"""Phase 0.1 - sort statements from an existing folder into 00_raw/<bank>/<account>/.

  python scripts/import_statements.py "<source folder>" --survey   # 1. what accounts are in there?
  python scripts/import_statements.py "<source folder>"            # 2. dry run: show where each file would go
  python scripts/import_statements.py "<source folder>" --apply    # 3. copy them

It works out each file's account from, in order of strength:
  - the account number's last 4 digits in the statement header (first 25 lines of page 1 / the CSV)
  - the last 4 digits in the file name ("Statement_12345678_2023.pdf")
  - the bank name and account name in the folder path ("CommBank/Business/...")
A file it can't place with confidence is left in the source and listed as UNSORTED -
drag those into the right 00_raw/ folder yourself.

--survey lists the account endings and banks it finds, and if config/accounts.csv has no
accounts yet, writes a draft there. Fill in default_use (business or personal) before
the dry run - the script will not guess that.

Copies only: the source folder is never changed. Files already imported (same content)
are skipped, so re-running is safe. Everything printed or written is masked to last 4 digits.
Writes review/import_report.csv. Next step after --apply: chmod -R a-w 00_raw, then inventory.py
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

from common import die, mask, p, read_csv, write_csv

KNOWN_BANKS = [
    ("CommBank", r"commonwealth bank|commbank|\bcba\b|netbank"),
    ("ANZ", r"\banz\b|australia and new zealand banking"),
    ("Westpac", r"westpac"),
    ("NAB", r"\bnab\b|national australia bank"),
    ("ING", r"\bing bank\b|\bing\b(?= (?:everyday|savings|orange|business))|ing\.com\.au"),
    ("Macquarie", r"macquarie"),
    ("St.George", r"st\.? ?george"),
    ("Bankwest", r"bankwest"),
    ("Bank of Melbourne", r"bank of melbourne"),
    ("BankSA", r"banksa|bank sa\b"),
    ("Suncorp", r"suncorp"),
    ("BOQ", r"bank of queensland|\bboq\b"),
    ("Bendigo", r"bendigo"),
    ("ubank", r"\bubank\b|\b86 ?400\b"),
    ("Up", r"\bup bank\b|up\.com\.au"),
    ("ME Bank", r"\bme bank\b|mebank"),
    ("HSBC", r"hsbc"),
    ("Citibank", r"citibank"),
    ("AMP", r"\bamp bank\b"),
    ("Heritage", r"heritage bank|people first bank"),
    ("Great Southern Bank", r"great southern bank"),
    ("Beyond Bank", r"beyond bank"),
    ("Bank Australia", r"bank australia"),
    ("Newcastle Permanent", r"newcastle permanent"),
    ("Greater Bank", r"greater bank"),
    ("Judo", r"judo bank"),
    ("Revolut", r"revolut"),
    ("Wise", r"\bwise\b(?= (?:account|payments|australia))"),
]
_BANK_RX = [(name, re.compile(rx, re.I)) for name, rx in KNOWN_BANKS]
_ACCT_LINE = re.compile(r"account|acct|a/c|\bacc\b|card|number|\bbsb\b", re.I)
# A transaction line: starts with a date and carries an amount. The header ends there.
_TXN_LINE = re.compile(r"^\s*(\d{1,2}[/.\-]\d{1,2}|\d{1,2}\s+[A-Za-z]{3})\b.*\d\.\d{2}")
_DIGIT_SEQ = re.compile(r"(?<![\d.,/])\d[\d \-]{3,}\d(?![\d.,/])")
_MASKED = re.compile(r"(?:[xX*•]{2,}|ending(?: in)?)\s?(\d{4})(?!\d)", re.I)
_BSB = re.compile(r"^\d{3}-?\d{3}$")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def looks_like_date(digits: str) -> bool:
    for fmt in ("%Y%m%d", "%d%m%Y", "%Y%m"):
        if len(digits) == len(dt.date(2000, 1, 1).strftime(fmt)):
            try:
                d = dt.datetime.strptime(digits, fmt)
                if 1990 <= d.year <= 2040:
                    return True
            except ValueError:
                pass
    return False


def endings(text: str) -> list[str]:
    """Candidate account endings (last 4 digits) in reading order."""
    out = []
    for m in _MASKED.finditer(text):
        out.append((m.start(), m.group(1)))
    for m in _DIGIT_SEQ.finditer(text):
        seq = m.group(0).strip()
        digits = re.sub(r"\D", "", seq)
        if len(digits) < 6 or _BSB.match(seq) or looks_like_date(digits) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", seq):
            continue
        out.append((m.start(), digits[-4:]))
    return [d for _, d in sorted(out)]


def name_endings(stem: str) -> list[str]:
    """Account endings in a file name: long digit runs (not dates) and masked forms like xx1234.
    Stricter than endings(): in file names, spaces and dashes separate fields, not digit groups."""
    out = [m.group(1) for m in _MASKED.finditer(stem)]
    for run in re.findall(r"(?<!\d)\d{6,}(?!\d)", stem):
        if not looks_like_date(run):
            out.append(run[-4:])
    return out


def banks_in(text: str) -> list[str]:
    return [name for name, rx in _BANK_RX if rx.search(text)]


def top_text(path: Path) -> tuple[str, str]:
    """The statement's header text (never its transactions), and a note if it could not be read.

    PDF: page-1 lines up to the first transaction line.
    CSV: the values of any column whose name mentions "account" (first 25 rows); CSV
    transaction descriptions are never read, because transfer lines name your other
    accounts ("TRANSFER FROM xx4321") and would send the file to the wrong folder."""
    if path.suffix.lower() == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                txt = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
        except Exception as e:
            return "", f"could not open PDF ({type(e).__name__})"
        head = []
        for line in txt.splitlines()[:40]:
            if _TXN_LINE.match(line):
                break
            head.append(line)
        return "\n".join(head), "" if txt.strip() else "no text layer (scan?)"
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            rows = [r for _, r in zip(range(26), csv.reader(f))]
    except Exception as e:
        return "", f"could not read CSV ({type(e).__name__})"
    if not rows:
        return "", "empty CSV"
    cols = [i for i, h in enumerate(rows[0]) if re.search(r"account|acct|bsb", h, re.I)]
    vals = {rows[0][i] + " " + r[i] for r in rows[1:] for i in cols if i < len(r) and r[i].strip()}
    return "\n".join(sorted(vals)), ""


def header_endings(text: str) -> list[str]:
    """Account endings on header lines that mention an account/card/number/BSB."""
    found = []
    for line in text.splitlines():
        if _ACCT_LINE.search(line):
            found += endings(line)
    return found


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gather(src: Path):
    files, ignored = [], []
    for f in sorted(src.rglob("*")):
        if not f.is_file() or f.name.startswith((".", "~$")):
            continue
        if f.suffix.lower() in {".pdf", ".csv"}:
            files.append(f)
        else:
            ignored.append(f)
    return files, ignored


def survey(src: Path, files: list[Path]) -> None:
    groups = defaultdict(lambda: {"files": 0, "banks": Counter(), "folders": Counter(), "types": Counter()})
    unknown = []
    for f in files:
        text, note = top_text(f)
        rel = f.relative_to(src)
        found = header_endings(text) or name_endings(f.stem)
        bank_hits = banks_in(text) or banks_in(str(rel))
        if not found:
            unknown.append((mask(rel.as_posix()), bank_hits[0] if bank_hits else "?", note))
            continue
        g = groups[found[0]]
        g["files"] += 1
        g["types"][f.suffix.lower().lstrip(".")] += 1
        for b in bank_hits[:1]:
            g["banks"][b] += 1
        if len(rel.parts) > 1:
            g["folders"][mask(rel.parent.as_posix())] += 1
    print(f"Survey of {len(files)} PDF/CSV files")
    print(f"{'ending':8} {'files':>5}  {'types':12} {'bank (guess)':18} folder")
    rows = []
    for l4, g in sorted(groups.items(), key=lambda kv: -kv[1]["files"]):
        bank = g["banks"].most_common(1)[0][0] if g["banks"] else "?"
        folder = g["folders"].most_common(1)[0][0] if g["folders"] else "-"
        types = " ".join(f"{k}:{v}" for k, v in g["types"].items())
        print(f"xx{l4:6} {g['files']:>5}  {types:12} {bank:18} {folder}")
        rows.append((l4, bank, folder))
    if unknown:
        print(f"No account number found in {len(unknown)} files (placed later by folder names, if possible):")
        for u in unknown[:15]:
            print(f"  {u[0]}  bank: {u[1]}  {u[2]}")
        if len(unknown) > 15:
            print(f"  ... {len(unknown) - 15} more")

    acc_path = p("config", "accounts.csv")
    existing = [r for r in read_csv(acc_path) if r.get("account_id")]
    if existing:
        print(f"config/accounts.csv already has {len(existing)} accounts - not overwritten.")
        return
    draft = []
    for l4, bank, folder in rows:
        last_dir = folder.split("/")[-1] if folder != "-" else ""
        name = re.sub(r"[^A-Za-z0-9 ]", "", last_dir).strip() or "Account"
        if bank != "?" and norm(bank) in norm(name):
            name = "Account"
        bank_label = bank if bank != "?" else "UnknownBank"
        draft.append({"account_id": f"{norm(bank_label)[:6].upper()}-{l4}", "bank": bank_label,
                      "account_name": name, "last4": l4, "default_use": "CHOOSE", "opened": "", "closed": "",
                      "raw_folder": f"{re.sub(r'[^A-Za-z0-9]', '', bank_label)}/{re.sub(r'[^A-Za-z0-9]', '', name)}_{l4}",
                      "parser_prefix": ""})
    write_csv(acc_path, draft, ["account_id", "bank", "account_name", "last4", "default_use", "opened",
                                "closed", "raw_folder", "parser_prefix"])
    print(f"\nWrote a draft config/accounts.csv with {len(draft)} accounts.")
    print("Before the next step: open it, replace every CHOOSE with business or personal, fix any bank")
    print("shown as UnknownBank, and delete rows that are not your accounts (e.g. a card number).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    src = Path(a.source).expanduser().resolve()
    if not src.is_dir():
        die(f"source folder not found: {a.source}")
    raw = p("00_raw")
    if raw in src.parents or src == raw:
        die("the source must be outside this project's 00_raw folder")
    files, ignored = gather(src)
    if not files:
        die("no PDF or CSV files found in the source folder")
    if a.survey:
        survey(src, files)
        return

    accounts = [r for r in read_csv(p("config", "accounts.csv"), required=True) if r.get("account_id")]
    bad = [r["account_id"] for r in accounts if r.get("default_use", "").lower() not in {"business", "personal"}]
    if bad:
        die(f"config/accounts.csv: set default_use to business or personal for {', '.join(bad)}")

    existing_hashes = {sha(f) for f in raw.rglob("*") if f.is_file()} if raw.exists() else set()
    report, seen = [], {}
    counts = Counter()
    for f in files:
        rel = f.relative_to(src)
        text, note = top_text(f)
        head = header_endings(text)
        name_end = name_endings(f.stem)
        path_n = norm(rel.as_posix())
        body_n = norm(text)
        found_banks = set(banks_in(text) + banks_in(rel.as_posix()))
        cands = []
        for acc in accounts:
            l4 = acc["last4"]
            ev = []
            pos = head.index(l4) if l4 in head else None
            if pos is not None:
                ev.append("statement header")
            yearish = re.fullmatch(r"(19|20)\d\d", l4) is not None
            if l4 in name_end or (not yearish and re.search(rf"(?<!\d){l4}(?!\d)", f.stem)):
                ev.append("file name")
            bank_hit = (norm(acc["bank"]) in path_n or norm(acc["bank"]) in body_n
                        or bool(set(banks_in(acc["bank"])) & found_banks))
            name_hit = norm(acc["account_name"]) and norm(acc["account_name"]) in path_n
            cands.append({"acc": acc, "ev": ev, "pos": pos if pos is not None else 99, "bank": bank_hit, "name": name_hit})
        strong = [c for c in cands if c["ev"]]
        choice, conf, why = None, "", ""
        if len(strong) == 1:
            choice, conf = strong[0], "high"
        elif len(strong) > 1:
            narrowed = [c for c in strong if c["bank"]] or strong
            narrowed.sort(key=lambda c: c["pos"])
            if len(narrowed) == 1 or narrowed[0]["pos"] < narrowed[1]["pos"]:
                choice, conf, why = narrowed[0], "medium", "several account numbers found; took the first in the header"
        else:
            weak = [c for c in cands if c["bank"] and c["name"]]
            if len(weak) == 1:
                choice, conf, why = weak[0], "medium", "from bank and account name in the folder/file names"
        entry = {"source": mask(rel.as_posix()), "type": f.suffix.lower().lstrip("."), "note": note}
        if not choice:
            entry.update(action="UNSORTED", account_id="", confidence="",
                         evidence="no account ending found" if not strong else "ambiguous: " + " / ".join(c["acc"]["account_id"] for c in strong))
            counts["UNSORTED"] += 1
            report.append(entry)
            continue
        acc = choice["acc"]
        dest_dir = raw / acc["raw_folder"]
        dest = dest_dir / f.name
        h = sha(f)
        if h in existing_hashes or h in seen:
            action = "skip (already imported)" if h in existing_hashes else f"skip (duplicate of {seen[h]})"
            counts["skipped"] += 1
        else:
            n = 2
            while dest.exists():
                dest = dest_dir / f"{f.stem}__{n}{f.suffix}"
                n += 1
            action = "copy" if a.apply else "would copy"
            counts[acc["account_id"]] += 1
            if a.apply:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
            seen[h] = mask(rel.as_posix())
        entry.update(action=action, account_id=acc["account_id"], confidence=conf,
                     evidence=", ".join(choice["ev"] or ["folder names"]) + (f" ({why})" if why else ""),
                     destination=mask(dest.relative_to(p()).as_posix()))
        report.append(entry)

    write_csv(p("review", "import_report.csv"), report,
              ["source", "type", "action", "account_id", "confidence", "evidence", "destination", "note"])
    print(f"{'Copied' if a.apply else 'DRY RUN - nothing copied yet'}: {len(files)} PDF/CSV files in the source")
    for acc in accounts:
        print(f"  {acc['account_id']:20} {counts.get(acc['account_id'], 0):>4} -> 00_raw/{acc['raw_folder']}")
    print(f"  {'already there/duplicate':20} {counts.get('skipped', 0):>4}")
    unsorted = [r for r in report if r["action"] == "UNSORTED"]
    medium = [r for r in report if r.get("confidence") == "medium"]
    print(f"  {'UNSORTED':20} {len(unsorted):>4}")
    for r in unsorted[:20]:
        print(f"     {r['source']}  ({r['evidence']})")
    if medium:
        print(f"Placed with medium confidence (check them): {len(medium)} - see review/import_report.csv")
    if ignored:
        kinds = Counter(f.suffix.lower() or "(none)" for f in ignored)
        print("Not PDF/CSV, ignored: " + ", ".join(f"{k} {v}" for k, v in kinds.items())
              + "  (xlsx/ofx/qif exports: download CSV instead)")
    if not a.apply:
        print('Looks right? Run again with --apply. UNSORTED files: drag them into the right 00_raw folder.')
    else:
        print("Next: drag any UNSORTED files into place, then: chmod -R a-w 00_raw && python3 scripts/inventory.py")


if __name__ == "__main__":
    main()
