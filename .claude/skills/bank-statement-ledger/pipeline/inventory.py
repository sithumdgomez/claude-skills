"""Phase 0.4 - inventory the raw statements.

Gives every statement a permanent ID (S001, S002, ...), copies it to
01_statements/ under a masked standard name, and finds missing periods early
so you can request them from the bank while the rest of the work goes on.

Run:     python scripts/inventory.py
Reads:   config/accounts.csv   (raw_folder maps a folder under 00_raw/ to an account)
         00_raw/**/*.pdf|*.csv  (never modified)
Writes:  config/inventory.csv          one row per statement (safe for Claude to read)
         01_statements/<file>          renamed copies (Claude is denied this folder)
         01_statements/_file_map.csv   statement ID -> original path (private)
         review/coverage_guess.csv     account x month, from periods found on page 1
Re-running is safe: known files keep their IDs (matched by content hash), and your
edits to the include / priority / notes columns are kept.
"""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
import sys

from common import (die, fy_bounds, load_accounts, load_project, mask, month_keys, p,
                    parse_date, read_csv, write_csv)

INV_FIELDS = ["statement_id", "account_id", "bank", "file_type", "statement_file",
              "original_name_masked", "sha256", "pages", "text_layer",
              "period_start_guess", "period_end_guess", "include", "priority", "notes"]

_DATE_TOKEN = r"(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\.?,?\s+\d{2,4})"
_PERIOD = re.compile(_DATE_TOKEN + r"\s*(?:to|-|–|—|until|through)\s*" + _DATE_TOKEN, re.I)


def detect_period(text: str):
    for m in _PERIOD.finditer(text or ""):
        try:
            a, b = parse_date(m[1]), parse_date(m[2])
        except ValueError:
            continue
        if a <= b and (b - a).days <= 400:
            return a, b
    return None, None


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_info(path):
    try:
        import pdfplumber
        from parsers._pdf_helpers import clean_page
    except ImportError:
        die("pdfplumber is not installed: pip install pdfplumber")
    try:
        with pdfplumber.open(path) as pdf:
            pages = len(pdf.pages)
            text = ""
            for pg in pdf.pages[:2]:
                text += (clean_page(pg).extract_text() or "") + "\n"
    except Exception as e:  # encrypted or damaged PDFs
        return 0, "?", None, None, f"cannot open ({type(e).__name__}) - password-protected or damaged?"
    has_text = "Y" if len(text.strip()) > 50 else "N"
    start, end = detect_period(text)
    note = "" if has_text == "Y" else "no text layer (scan?) - get an e-statement or CSV instead of OCR"
    return pages, has_text, start, end, note


def csv_info(path):
    dates = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        for row in csv.reader(f):
            for cell in row:
                try:
                    dates.append(parse_date(cell))
                except (ValueError, TypeError):
                    pass
    if not dates:
        return None, None, "no dates found in CSV"
    return min(dates), max(dates), ""


def main():
    cfg = load_project()
    accounts = load_accounts()
    raw = p("00_raw")
    if not raw.exists():
        die("00_raw/ not found - create it and copy the statements in")

    existing = {r["sha256"]: r for r in read_csv(p("config", "inventory.csv"))}
    used_ids = [int(r["statement_id"][1:]) for r in existing.values() if r["statement_id"][1:].isdigit()]
    next_id = max(used_ids, default=0) + 1

    folders = sorted(((a["raw_folder"].strip("/").lower(), aid) for aid, a in accounts.items()),
                     key=lambda t: -len(t[0]))
    rows, file_map, ignored, unmapped, dupes = [], [], [], [], []
    seen = {}
    out_dir = p("01_statements")
    out_dir.mkdir(exist_ok=True)

    for path in sorted(raw.rglob("*")):
        if not path.is_file() or path.name.startswith((".", "_")):
            continue
        ext = path.suffix.lower().lstrip(".")
        rel_parent = path.relative_to(raw).parent.as_posix().lower()
        if ext not in {"pdf", "csv"}:
            ignored.append(mask(path.name))
            continue
        acct_id = next((aid for rf, aid in folders if rf and (rel_parent == rf or rel_parent.startswith(rf + "/"))), None)
        if not acct_id:
            unmapped.append(mask(path.relative_to(raw).as_posix()))
            continue
        h = sha256(path)
        if h in seen:
            dupes.append((mask(path.name), seen[h]))
            continue
        prev = existing.get(h)
        if prev:
            sid = prev["statement_id"]
        else:
            sid = f"S{next_id:03d}"
            next_id += 1
        seen[h] = sid

        if ext == "pdf":
            pages, text_layer, start, end, note = pdf_info(path)
        else:
            pages, text_layer = "", "-"
            start, end, note = csv_info(path)

        if prev and prev.get("statement_file"):
            new_name = prev["statement_file"]
        else:
            span = f"_{start}_{end}" if start else ""
            new_name = f"{sid}_{acct_id}{span}.{ext}"
        dest = out_dir / new_name
        if not dest.exists() or dest.stat().st_size != path.stat().st_size:
            shutil.copy2(path, dest)

        rows.append({
            "statement_id": sid, "account_id": acct_id, "bank": accounts[acct_id]["bank"],
            "file_type": ext, "statement_file": new_name,
            "original_name_masked": mask(path.name), "sha256": h, "pages": pages,
            "text_layer": text_layer, "period_start_guess": start.isoformat() if start else "",
            "period_end_guess": end.isoformat() if end else "",
            "include": (prev or {}).get("include") or "Y",
            "priority": (prev or {}).get("priority") or ("1" if ext == "pdf" else "2"),
            "notes": (prev or {}).get("notes") or note,
        })
        file_map.append({"statement_id": sid, "original_path": path.relative_to(raw).as_posix()})

    rows.sort(key=lambda r: r["statement_id"])
    write_csv(p("config", "inventory.csv"), rows, INV_FIELDS)
    write_csv(out_dir / "_file_map.csv", file_map, ["statement_id", "original_path"])

    # Coverage guess: which months of the project window have a statement?
    start_all, _ = fy_bounds(cfg["first_fy"], cfg["fy_start_month"])
    _, end_all = fy_bounds(cfg["last_fy"], cfg["fy_start_month"])
    months = month_keys(start_all, end_all)
    grid, missing_total, unknown = [], 0, 0
    for aid, acct in accounts.items():
        opened = acct.get("opened") or ""
        closed = acct.get("closed") or ""
        line = {"account_id": aid}
        stmts = [r for r in rows if r["account_id"] == aid and r["include"].upper() == "Y"]
        unknown += sum(1 for r in stmts if not r["period_start_guess"])
        for mk in months:
            if (opened and mk < opened[:7]) or (closed and mk > closed[:7]):
                line[mk] = "-"
                continue
            ids = [r["statement_id"] for r in stmts
                   if r["period_start_guess"] and r["period_start_guess"][:7] <= mk <= r["period_end_guess"][:7]]
            line[mk] = " ".join(ids) if ids else "MISSING"
            missing_total += 0 if ids else 1
        grid.append(line)
    write_csv(p("review", "coverage_guess.csv"), grid, ["account_id"] + months)

    # ---- summary (short on purpose)
    n_pdf = sum(1 for r in rows if r["file_type"] == "pdf")
    print(f"Statements: {len(rows)} ({n_pdf} PDF, {len(rows) - n_pdf} CSV) across {len({r['account_id'] for r in rows})} accounts")
    for aid in accounts:
        n = sum(1 for r in rows if r["account_id"] == aid)
        print(f"  {aid}: {n}")
    scans = [r["statement_id"] for r in rows if r["text_layer"] == "N"]
    broken = [r["statement_id"] for r in rows if r["text_layer"] == "?"]
    if scans:
        print(f"No text layer (scans): {', '.join(scans)}")
    if broken:
        print(f"Could not open: {', '.join(broken)}")
    if dupes:
        print(f"Exact duplicate files skipped: {len(dupes)} (" + "; ".join(f"{n} = {s}" for n, s in dupes[:5]) + ")")
    if unmapped:
        print(f"Files not under any account's raw_folder: {len(unmapped)} - e.g. {unmapped[0]}")
    if ignored:
        print(f"Ignored non-PDF/CSV files: {len(ignored)}")
    print(f"Period not found on page 1: {unknown} statements (resolved after parsing)")
    print(f"Account-months with no statement found: {missing_total} -> review/coverage_guess.csv")
    if unmapped or broken:
        sys.exit(1)


if __name__ == "__main__":
    main()
