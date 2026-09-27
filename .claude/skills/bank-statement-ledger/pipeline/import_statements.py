"""Phase 0.1 - sort statements from an existing folder into 00_raw/<bank>/<account>/.

  python scripts/import_statements.py "<source folder>" --survey   # 1. what accounts are in there?
  python scripts/import_statements.py "<source folder>"            # 2. dry run: show where each file would go
  python scripts/import_statements.py "<source folder>" --apply    # 3. copy them
  python scripts/import_statements.py "<source folder>" --show "<file>"   # why wasn't a file's number found?

It works out each file's account from, in order of strength:
  - the account number's last 4 digits in the statement header (page 1 up to the first
    transaction line / the CSV's account column)
  - the last 4 digits in the file name ("Statement_12345678_2023.pdf")
  - the bank and account name in the folder and file names ("CommBank/Business/...",
    "CBA_Business-Saving_2023-02_to_2023-05.pdf")
A file it can't place with confidence is left in the source and listed as UNSORTED -
drag those into the right 00_raw/ folder yourself.

--survey lists the accounts it finds (by account ending, or by bank + account name when the
files show no number) and writes a draft config/accounts.csv if there are no accounts yet
(or only an untouched draft). Fill in default_use (business or personal) and any missing
last4 before the dry run - the script will not guess those.

--show prints page 1 of one file (masked) and marks where the script thinks the header ends,
to work out why an account number wasn't found. Safe to paste into Claude.

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
# Where the header ends (see header_end). The month must be a real month, so an address like
# "5 The Crescent" next to "Closing balance $1,234.56" does not end the header early.
_MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
          r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_DATE_START = re.compile(rf"^\s*(?:(\d{{1,2}})[/\-](\d{{1,2}})(?:[/\-]\d{{2,4}})?|(\d{{1,2}})\s+{_MONTH}(?:\s+\d{{4}})?)(?=\s|$)",
                         re.I)
_RANGE_REST = re.compile(r"^\s*(?:-|–|to)\s*\d", re.I)       # "1 Feb 2023 - 31 May 2023" is a period
_TABLE_HEAD = re.compile(r"^\s*(?:date|posted|value date|transaction date)\b.*"
                         r"\b(?:balance|debit|credit|amount|withdrawals?|deposits?)\b", re.I)
_OPENING = re.compile(r"opening balance|brought forward", re.I)
_AMOUNT = re.compile(r"\d\.\d{2}\b")
# Numbers in a header that are never account numbers: phone numbers ("13 10 12 for Business
# Accounts" on every NAB statement), ABNs, and numbers labelled customer/reference/licence etc.
_PHONE = re.compile(r"^(?:13 ?\d{2} ?\d{2}|1[38]00 ?\d{3} ?\d{3}|0[2-478] ?\d{4} ?\d{4}|04\d{2} ?\d{3} ?\d{3})$")
_ABN = re.compile(r"^\d{2} \d{3} \d{3} \d{3}$")
_NOT_ACCOUNT_LABEL = re.compile(r"(?:\babn|\bacn|\bafsl|licen[cs]e|\bcall|phone|\btel|\bfax|\bph|enquir\w*|\bbpay"
                                r"|biller(?: code)?|\bref(?:erence)?|customer(?: number| no)?|member(?: number| no)?"
                                r"|client(?: number| no)?|\bcrn)\W*$", re.I)
# A full BSB + account number anywhere in the header ("06 1234 00005678", "083-123 12345678").
_ACCT_SHAPE = re.compile(r"(?<![\d.,/])\d{2,3}[- ]?\d{3,4}[ ]{1,3}\d{4,10}(?![\d.,/])")
_DIGIT_SEQ = re.compile(r"(?<![\d.,/])\d[\d \-]{3,}\d(?![\d.,/])")
_MASKED = re.compile(r"(?:[xX*•]{2,}|ending(?: in)?)\s?(\d{4})(?!\d)", re.I)
_BSB = re.compile(r"^\d{3}-?\d{3}$")
# For --show only: digit runs that mask() misses, e.g. letter-spaced text "0 6 2 0 0 0 1 2 3 4".
_ANY_DIGITS = re.compile(r"(?<![\d.,])\d(?:[ \-]?\d){5,}(?![\d.,])")
# Words in file/folder names that say nothing about which account it is.
_NOISE = {"statement", "statements", "estatement", "estatements", "stmt", "export", "exports", "download",
          "downloads", "transactions", "history", "copy", "final", "new", "to", "from", "and", "of", "the",
          "for", "period", "page", "pdf", "csv", "bank", "banking", "account", "accounts", "acc", "acct",
          "unverified", "pending"}
_SHORT = {"CommBank": "CBA", "St.George": "STG", "Bank of Melbourne": "BOM", "Great Southern Bank": "GSB",
          "UnknownBank": "BANK"}


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


def not_an_account(seq: str, before: str) -> bool:
    """A phone number, ABN, or a number whose label says it is something else."""
    return bool(_PHONE.match(seq) or _ABN.match(seq) or _NOT_ACCOUNT_LABEL.search(before[-30:]))


def endings(text: str) -> list[str]:
    """Candidate account endings (last 4 digits) in reading order."""
    out = []
    for m in _MASKED.finditer(text):
        out.append((m.start(), m.group(1)))
    for m in _DIGIT_SEQ.finditer(text):
        seq = m.group(0).strip()
        digits = re.sub(r"\D", "", seq)
        if (len(digits) < 6 or _BSB.match(seq) or looks_like_date(digits) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", seq)
                or not_an_account(seq, text[:m.start()])):
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


def path_words(rel: Path) -> str:
    """A path as plain words: "FY2023/CBA_Business-Saving.pdf" -> "FY2023 CBA Business Saving pdf".
    (\\b in the bank patterns treats "_" as part of a word, so "CBA_" would not match.)"""
    return re.sub(r"[^A-Za-z0-9]+", " ", rel.as_posix()).strip()


def account_label(rel: Path) -> str:
    """What the folder and file names call the account, without bank, dates and filler:
    "FY2023/CBA_Business-Saving_2023-02_to_2023-05.pdf" -> "Business Saving". "" if nothing is left."""
    text = re.sub(r"[^A-Za-z0-9]+", " ", " ".join(rel.parent.parts + (rel.stem,)))
    for _, rx in _BANK_RX:
        text = rx.sub(" ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text).lower()   # BusinessSaving -> business saving
    words = []
    for w in text.split():
        if (len(w) < 2 or re.search(r"\d", w) or w in _NOISE or re.fullmatch(_MONTH, w)
                or re.fullmatch(r"[x*]+", w) or w in words):
            continue
        words.append(w)
    return " ".join(w.capitalize() for w in words)


def short_id(bank: str, label: str = "", l4: str = "") -> str:
    code = _SHORT.get(bank, norm(bank).upper()[:8] or "BANK")
    if l4:
        return f"{code}-{l4}"
    words = label.split() or ["Account"]
    tail = words[0][:6] if len(words) == 1 else "".join(w[:3] for w in words[:3])
    return f"{code}-{tail.upper()}"


def mask_all(text: str) -> str:
    """mask(), plus any other run of 6+ digits that is not a date (for --show output)."""
    def repl(m):
        digits = re.sub(r"\D", "", m.group(0))
        return m.group(0) if looks_like_date(digits) else "xx" + digits[-4:]
    return _ANY_DIGITS.sub(repl, mask(text))


def pdf_lines(path: Path) -> tuple[list[str], str]:
    """Page 1's text lines, and a note if there is no usable text."""
    try:
        import pdfplumber
        from parsers._pdf_helpers import clean_page
        with pdfplumber.open(path) as pdf:
            txt = ""
            if pdf.pages:
                txt = clean_page(pdf.pages[0]).extract_text() or ""
    except Exception as e:
        return [], f"could not open PDF ({type(e).__name__})"
    return txt.splitlines(), "" if txt.strip() else "no text layer (scan?)"


def date_start(line: str):
    """The date a line starts with (a real day and month, then a space), or None."""
    m = _DATE_START.match(line)
    if not m:
        return None
    day, month = int(m.group(1) or m.group(3)), int(m.group(2) or 1)
    return m if 1 <= day <= 31 and 1 <= month <= 12 else None


def header_end(lines: list[str]) -> int:
    """Index of the line where the transactions start (the header is everything before), within
    the first 40 lines: the table heading ("Date ... Balance"), or a line that starts with a date
    and carries an amount, an opening balance, or a description whose amount comes on one of the
    next 3 lines (CommBank: "16 Dec MCDONALDS ..." / "Card xx1234" / "Value Date: ... 13.10")."""
    for i, line in enumerate(lines[:40]):
        if _TABLE_HEAD.search(line):
            return i
        m = date_start(line)
        rest = line[m.end():] if m else ""
        if not m or _RANGE_REST.match(rest):
            continue
        if _AMOUNT.search(rest) or _OPENING.search(rest):
            return i
        if len(re.findall(r"[A-Za-z]{2,}", rest)) >= 2:
            for nxt in lines[i + 1:i + 4]:
                if date_start(nxt):
                    break
                if _AMOUNT.search(nxt):
                    return i
    return min(len(lines), 40)


def top_text(path: Path) -> tuple[str, str]:
    """The statement's header text (never its transactions), and a note if it could not be read.

    PDF: page-1 lines up to the first transaction line.
    CSV: the values of any column whose name mentions "account" (first 25 rows); CSV
    transaction descriptions are never read, because transfer lines name your other
    accounts ("TRANSFER FROM xx4321") and would send the file to the wrong folder."""
    if path.suffix.lower() == ".pdf":
        lines, note = pdf_lines(path)
        return "\n".join(lines[:header_end(lines)]), note
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
    """Account endings on header lines that mention an account/card/number/BSB (or on the line
    just below such a label, when the number is printed a little lower). If none, a full
    BSB + account number anywhere in the header."""
    lines = text.splitlines()
    found = []
    for i, line in enumerate(lines):
        if _ACCT_LINE.search(line):
            got = endings(line)
            if not got and i + 1 < len(lines) and re.fullmatch(r"[\d \-]{6,}", lines[i + 1].strip()):
                got = endings(lines[i + 1])
            found += got
    if not found:
        for line in lines:
            found += [re.sub(r"\D", "", m.group(0))[-4:] for m in _ACCT_SHAPE.finditer(line)
                      if not not_an_account(m.group(0), line[:m.start()])]
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
    info = []
    for f in files:
        text, note = top_text(f)
        rel = f.relative_to(src)
        found = header_endings(text) or name_endings(f.stem)
        hits = banks_in(text) or banks_in(path_words(rel))
        info.append({"rel": rel, "ends": list(dict.fromkeys(found)), "bank": hits[0] if hits else "?",
                     "label": account_label(rel), "type": f.suffix.lower().lstrip("."), "note": note})

    # 1. accounts with a number; 2. files without one join an account with the same bank and
    #    name; 3. the rest are grouped by bank + name; 4. no name either: listed for the owner.
    # A file whose header shows several numbers (e.g. a linked savings account above its own) takes
    # the first number that isn't already the only number on another account's statements.
    sole = defaultdict(set)
    for i in info:
        if len(i["ends"]) == 1 and i["label"]:
            sole[i["ends"][0]].add(i["label"])
    for i in info:
        ends = i["ends"]
        free = [e for e in ends if not (i["label"] and sole.get(e) and i["label"] not in sole[e])]
        i["l4"] = (free or ends or [""])[0]

    groups = []
    for l4 in dict.fromkeys(i["l4"] for i in info if i["l4"]):
        items = [i for i in info if i["l4"] == l4]
        banks = Counter(i["bank"] for i in items if i["bank"] != "?")
        labels = Counter(i["label"] for i in items if i["label"])
        groups.append({"l4": l4, "bank": banks.most_common(1)[0][0] if banks else "?",
                       "label": labels.most_common(1)[0][0] if labels else "", "items": items, "by_name": 0})
    unknown = []
    for i in (i for i in info if not i["l4"]):
        same = [g for g in groups if i["label"] and g["label"] == i["label"] and g["bank"] == i["bank"]]
        if len(same) == 1:
            same[0]["items"].append(i)
            same[0]["by_name"] += 1
        elif i["label"]:
            g = next((g for g in groups if not g["l4"] and g["label"] == i["label"] and g["bank"] == i["bank"]), None)
            if g is None:
                g = {"l4": "", "bank": i["bank"], "label": i["label"], "items": [], "by_name": 0}
                groups.append(g)
            g["items"].append(i)
            g["by_name"] += 1
        else:
            unknown.append(i)

    print(f"Survey of {len(files)} PDF/CSV files")
    print(f"{'ending':8} {'files':>5}  {'types':12} {'bank (guess)':14} account name (from file/folder names)")
    for g in sorted(groups, key=lambda g: (g["bank"], g["label"], g["l4"])):
        types = " ".join(f"{k}:{v}" for k, v in Counter(i["type"] for i in g["items"]).items())
        extra = f"   ({g['by_name']} placed by name only)" if g["l4"] and g["by_name"] else ""
        print(f"{'xx' + g['l4'] if g['l4'] else '????':8} {len(g['items']):>5}  {types:12} {g['bank']:14} "
              f"{g['label'] or '-'}{extra}")
    if any(not g["l4"] for g in groups):
        print("???? = no account number found in these files, so they are grouped by bank and name.\n"
              "       Add each one's last 4 digits to config/accounts.csv yourself (from a statement).")
    if unknown:
        print(f"\nNo account number or account name found in {len(unknown)} files (you'll place these by hand):")
        for u in unknown[:15]:
            print(f"  {mask(u['rel'].as_posix())}  bank: {u['bank']}  {u['note']}")
        if len(unknown) > 15:
            print(f"  ... {len(unknown) - 15} more")
    notes = Counter(i["note"] for i in info if i["note"])
    for note, n in notes.items():
        print(f"{n} files: {note}")
    if any(not g["l4"] for g in groups):
        example = next(g for g in groups if not g["l4"])["items"][0]["rel"].as_posix()
        print(f'\nTo see why a file shows no number:  --show "{mask(example)}"')

    acc_path = p("config", "accounts.csv")
    existing = [r for r in read_csv(acc_path) if r.get("account_id")]
    if existing and any(r.get("default_use", "").strip().upper() != "CHOOSE" for r in existing):
        print(f"\nconfig/accounts.csv already has {len(existing)} accounts you've edited - not overwritten.")
        return
    draft, ids = [], set()
    for g in sorted(groups, key=lambda g: (g["bank"], g["label"], g["l4"])):
        bank = g["bank"] if g["bank"] != "?" else "UnknownBank"
        name = g["label"] or "Account"
        acc_id = short_id(bank, name, g["l4"])
        n = 2
        while acc_id in ids:
            acc_id = f"{short_id(bank, name, g['l4'])}-{n}"
            n += 1
        ids.add(acc_id)
        folder = re.sub(r"[^A-Za-z0-9]", "", name) + (f"_{g['l4']}" if g["l4"] else "")
        draft.append({"account_id": acc_id, "bank": bank, "account_name": name, "last4": g["l4"],
                      "default_use": "CHOOSE", "opened": "", "closed": "",
                      "raw_folder": f"{re.sub(r'[^A-Za-z0-9]', '', bank)}/{folder}", "parser_prefix": ""})
    write_csv(acc_path, draft, ["account_id", "bank", "account_name", "last4", "default_use", "opened",
                                "closed", "raw_folder", "parser_prefix"])
    print(f"\n{'Replaced the untouched draft' if existing else 'Wrote a draft'} config/accounts.csv "
          f"with {len(draft)} accounts.")
    print("Before the next step: open it, replace every CHOOSE with business or personal, fill in any empty\n"
          "last4, fix any bank shown as UnknownBank, and delete rows that are not your accounts.")


def show(src: Path, target: str) -> None:
    f = Path(target).expanduser()
    if not f.is_absolute():
        f = src / target
    if not f.is_file():
        die(f"file not found: {target} (give the path as the survey prints it, relative to the source folder)")
    rel = f.relative_to(src) if src in f.parents else Path(f.name)
    print(f"File: {mask(rel.as_posix())}   (page 1 only, account numbers masked)")
    if f.suffix.lower() == ".pdf":
        lines, note = pdf_lines(f)
        cut = header_end(lines)
        for i, line in enumerate(lines[:45]):
            if i == cut:
                print("----- header ends here: the next line looks like the first transaction -----")
            print(f"  {mask_all(line)}")
        if cut >= len(lines[:45]):
            print("----- no transaction line found; all lines above count as header -----")
        if note:
            print(f"Note: {note}")
    else:
        with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
            for _, line in zip(range(6), fh):
                print(f"  {mask_all(line.rstrip())}")
    text, _ = top_text(f)
    ends = header_endings(text)
    print(f"Account endings found in the header: {', '.join('xx' + e for e in ends) or 'none'}")
    print(f"Bank: {', '.join(banks_in(text)) or 'none'} (text), "
          f"{', '.join(banks_in(path_words(rel))) or 'none'} (file/folder names)")
    print(f"Account name from file/folder names: {account_label(rel) or 'none'}")
    print("Before pasting this anywhere, delete your name and address lines if you prefer.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", metavar="FILE", help="print page 1 of one file (masked) to see why no number was found")
    a = ap.parse_args()
    src = Path(a.source).expanduser().resolve()
    if not src.is_dir():
        die(f"source folder not found: {a.source}")
    raw = p("00_raw")
    if raw in src.parents or src == raw:
        die("the source must be outside this project's 00_raw folder")
    if a.show:
        show(src, a.show)
        return
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
    no_l4 = [r["account_id"] for r in accounts if not re.fullmatch(r"\d{4}", r.get("last4", "").strip())]

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
        found_banks = set(banks_in(text) + banks_in(path_words(rel)))
        label_n = norm(account_label(rel))
        cands = []
        for acc in accounts:
            l4 = acc.get("last4", "").strip()
            ev = []
            pos = head.index(l4) if l4 and l4 in head else None
            if pos is not None:
                ev.append("statement header")
            yearish = re.fullmatch(r"(19|20)\d\d", l4) is not None
            if l4 and (l4 in name_end or (not yearish and re.search(rf"(?<!\d){l4}(?!\d)", f.stem))):
                ev.append("file name")
            bank_hit = (norm(acc["bank"]) in path_n or norm(acc["bank"]) in body_n
                        or bool(set(banks_in(acc["bank"])) & found_banks))
            acc_n = norm(acc["account_name"])
            name_hit = bool(acc_n) and (acc_n in path_n or acc_n == label_n)
            cands.append({"acc": acc, "ev": ev, "pos": pos if pos is not None else 99, "bank": bank_hit, "name": name_hit})
        strong = [c for c in cands if c["ev"]]
        choice, conf, why = None, "", ""
        if len(strong) == 1:
            choice, conf = strong[0], "high"
        elif len(strong) > 1:
            narrowed = [c for c in strong if c["bank"]] or strong
            named = [c for c in narrowed if c["name"]]
            narrowed.sort(key=lambda c: c["pos"])
            if len(named) == 1:
                choice, conf, why = named[0], "medium", "several account numbers found; took the one named in the file name"
            elif len(narrowed) == 1 or narrowed[0]["pos"] < narrowed[1]["pos"]:
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
    if no_l4:
        print(f"last4 is empty for {', '.join(no_l4)}: fill it in from a statement before inventory.py "
              "(transfer matching needs it).")
    if not a.apply:
        print('Looks right? Run again with --apply. UNSORTED files: drag them into the right 00_raw folder.')
    else:
        print("Next: drag any UNSORTED files into place, then: chmod -R a-w 00_raw && python3 scripts/inventory.py")


if __name__ == "__main__":
    main()
