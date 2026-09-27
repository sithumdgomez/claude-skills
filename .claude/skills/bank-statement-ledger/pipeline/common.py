"""Shared helpers for the bank-statement-ledger pipeline.

The rules that every script must follow live here, in one place:
- Money is decimal.Decimal, never float. Floats turn 0.1 + 0.2 into
  0.30000000000000004, and a ledger that is out by a cent fails its balance check.
- Dates are read day-first (Australian format) and stored as ISO yyyy-mm-dd.
- Account and card numbers are masked to the last 4 digits before anything is
  written where Claude or the accountant can see it.
- Scripts print short summaries; detail goes to files (Claude reads every line
  a script prints, so a printed table costs tokens on every run).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

# scripts/ sits directly inside the project folder.
ROOT = Path(__file__).resolve().parent.parent
CENT = Decimal("0.01")


def p(*parts: str) -> Path:
    """Path inside the project folder."""
    return ROOT.joinpath(*parts)


def rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def die(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}")
    sys.exit(code)


# --------------------------------------------------------------------------- config

DEFAULT_PROJECT = {
    "country": "AU",
    "currency": "AUD",
    "fy_start_month": 7,
    "first_fy": "FY2023",
    "last_fy": "FY2026",
    "gst_registered": False,
    "own_names": [],
    "transfer_max_days": 4,
    "loan_flag_threshold": "500",
    "large_business_item_threshold": "1000",
    "date_tolerance_days": 7,
    "cash_deposit_keywords": ["CASH DEP", "CASH DEPOSIT", "ATM DEPOSIT", "BRANCH DEPOSIT"],
    "transfer_keywords": [
        "TRANSFER", "TFR", "XFER", "OSKO", "PAYID", "PAY ID", "NPP", "PAY ANYONE",
        "FAST TRANSFER", "INTERNET TRANSFER", "ONLINE TRANSFER", "BEEM",
    ],
}


def load_project() -> dict:
    cfg = dict(DEFAULT_PROJECT)
    f = p("config", "project.json")
    if f.exists():
        cfg.update(json.loads(f.read_text(encoding="utf-8")))
    return cfg


def load_accounts() -> dict[str, dict]:
    rows = read_csv(p("config", "accounts.csv"), required=True)
    need = {"account_id", "bank", "account_name", "last4", "default_use", "raw_folder"}
    missing = need - set(rows[0].keys()) if rows else need
    if missing:
        die(f"config/accounts.csv is missing columns: {', '.join(sorted(missing))}")
    out = {}
    for r in rows:
        if not r["account_id"]:
            continue
        use = r["default_use"].strip().lower()
        if use not in {"business", "personal"}:
            die(f"accounts.csv: {r['account_id']} default_use must be business or personal")
        r["default_use"] = use
        out[r["account_id"]] = r
    return out


# --------------------------------------------------------------------------- vocab

TYPES = [
    "Business income", "Other income", "Expense", "Refund",
    "Internal transfer", "Owner drawing", "Owner contribution",
    "Loan out", "Loan in", "Gift or shared bill", "Tax", "Outside account", "Unknown",
]
PNL_TYPES = {"Business income", "Other income", "Expense", "Refund"}
TRANSFER_TYPES = {"Internal transfer", "Owner drawing", "Owner contribution"}
LOAN_TYPES = {"Loan out", "Loan in"}
BP_VALUES = ["Business", "Personal", "Mixed"]


# --------------------------------------------------------------------------- csv

def read_csv(path: Path, required: bool = False) -> list[dict]:
    path = Path(path)
    if not path.exists():
        if required:
            die(f"missing file: {rel(path)}")
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    clean = []
    for r in rows:
        clean.append({(k or "").strip(): (v or "").strip()
                      for k, v in r.items() if k is not None and not isinstance(v, list)})
    return clean


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, float):
        raise TypeError("a float reached a CSV writer; money must be Decimal")
    if isinstance(v, Decimal):
        return fmt_money(v)
    if isinstance(v, dt.date):
        return v.isoformat()
    return v


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r.get(k)) for k in fields})


# --------------------------------------------------------------------------- money

_MONEY_BODY = re.compile(r"(?:\d+(?:\.\d{1,2})?|\.\d{1,2})")


def parse_money(text) -> Decimal | None:
    """Parse an amount as printed on a statement.

    Handles $, commas, spaces, AUD, leading/trailing minus, (brackets),
    and CR/DR suffixes (CR = positive, DR = negative/overdrawn).
    Returns None for an empty cell. Raises ValueError for anything else,
    so a misread column fails loudly instead of becoming a wrong number.
    For a debit/credit *column* the parser decides the sign, not this function.
    """
    if text is None:
        return None
    if isinstance(text, Decimal):
        return text
    if isinstance(text, float):
        raise TypeError("float passed to parse_money; read the cell as text")
    s = str(text).strip()
    if not s or s in {"-", "–", "—"}:
        return None
    s = (s.replace("−", "-").replace("$", "").replace(",", "")
          .replace(" ", "").replace(" ", ""))
    up = s.upper()
    if up.startswith("AUD"):
        s = s[3:]
        up = up[3:]
    if up == "NIL":
        return Decimal("0.00")
    neg = False
    if up.endswith("CR"):
        s = s[:-2]
    elif up.endswith("DR"):
        s = s[:-2]
        neg = True
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
        neg = not neg
    if s.endswith("-"):
        s = s[:-1]
        neg = not neg
    if s.startswith("+"):
        s = s[1:]
    elif s.startswith("-"):
        s = s[1:]
        neg = not neg
    if not _MONEY_BODY.fullmatch(s):
        raise ValueError(f"not a money amount: {text!r}")
    v = Decimal(s).quantize(CENT)
    return -v if neg else v


def money(s: str) -> Decimal | None:
    """Read a money value written by this pipeline ('' -> None)."""
    if s is None or s == "":
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"bad money value in pipeline file: {s!r}")


def fmt_money(d: Decimal) -> str:
    d = d.quantize(CENT)
    if d == 0:
        d = Decimal("0.00")
    return f"{d:f}"


# --------------------------------------------------------------------------- dates

_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_DMY = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2}|\d{4})$")
_D_MON_Y = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)?[\s\-]*([A-Za-z]{3,9})\.?,?[\s\-]*(\d{2}|\d{4})?$")
_MON_D_Y = re.compile(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$")


def _month(name: str) -> int:
    key = name[:3].upper()
    if key not in _MONTHS:
        raise ValueError(f"unknown month: {name!r}")
    return _MONTHS[key]


def _year(y: str) -> int:
    n = int(y)
    return 2000 + n if n < 100 else n


def _infer_year(d: int, mo: int, start: dt.date | None, end: dt.date | None, text: str) -> dt.date:
    # Many Australian statements print "03 Jan" with no year. The year comes from
    # the statement period; a statement spanning Dec-Jan needs both years.
    if not start or not end:
        raise ValueError(f"date {text!r} has no year and no statement period was given")
    lo, hi = start - dt.timedelta(days=31), end + dt.timedelta(days=31)
    found = []
    for y in sorted({start.year, end.year}):
        try:
            cand = dt.date(y, mo, d)
        except ValueError:
            continue
        if lo <= cand <= hi:
            found.append(cand)
    inside = [c for c in found if start <= c <= end]
    if len(inside) == 1:
        return inside[0]
    if len(found) == 1:
        return found[0]
    raise ValueError(f"cannot work out the year for {text!r} in period {start}..{end}")


def parse_date(text, period_start: dt.date | None = None, period_end: dt.date | None = None) -> dt.date:
    """Parse a statement date, always day-first. Never guesses month-first."""
    if isinstance(text, dt.date):
        return text
    s = " ".join(str(text).split())
    m = _ISO.match(s)
    if m:
        return dt.date(int(m[1]), int(m[2]), int(m[3]))
    m = _DMY.match(s)
    if m:
        return dt.date(_year(m[3]), int(m[2]), int(m[1]))
    m = _D_MON_Y.match(s)
    if m:
        d, mo = int(m[1]), _month(m[2])
        if m[3]:
            return dt.date(_year(m[3]), mo, d)
        return _infer_year(d, mo, period_start, period_end, s)
    m = _MON_D_Y.match(s)
    if m:
        return dt.date(int(m[3]), _month(m[1]), int(m[2]))
    raise ValueError(f"unrecognised date: {text!r}")


def iso(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def fy_of(d: dt.date, start_month: int = 7) -> str:
    """FY label by the year the financial year ends: 1 Jul 2022 - 30 Jun 2023 = FY2023."""
    if start_month == 1:
        return f"FY{d.year}"
    return f"FY{d.year + 1 if d.month >= start_month else d.year}"


def fy_bounds(label: str, start_month: int = 7) -> tuple[dt.date, dt.date]:
    end_year = int(label[2:])
    if start_month == 1:
        return dt.date(end_year, 1, 1), dt.date(end_year, 12, 31)
    start = dt.date(end_year - 1, start_month, 1)
    end = dt.date(end_year, start_month, 1) - dt.timedelta(days=1)
    return start, end


def fy_labels(first: str, last: str) -> list[str]:
    return [f"FY{y}" for y in range(int(first[2:]), int(last[2:]) + 1)]


def month_keys(start: dt.date, end: dt.date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


# --------------------------------------------------------------------------- masking

# Order matters: card groups, then BSB + account, then spaced account numbers,
# then any long run of digits. Amounts ("123456.78", "1,234.56") and dates
# ("01/07/2022", "2022-07-01") are deliberately left alone.
_CARD = re.compile(r"(?<![\d.])\d{4}(?:[ -]\d{4}){2,3}(?![\d.])")
_BSB_ACCT = re.compile(r"(?<![\d.])\d{3}[- ]?\d{3}[ ]{1,3}\d{4,10}(?![\d.])")
_ACCT_SPACED = re.compile(r"(?<![\d.])\d{4} \d{4,6}(?![\d.])")
_LONG = re.compile(r"(?<![\d.])\d{6,}(?![\d.])")


def _keep_last4(m: re.Match) -> str:
    digits = re.sub(r"\D", "", m.group(0))
    return "xx" + digits[-4:]


def mask(text: str) -> str:
    """Mask account/card numbers to the last 4 digits: '062-000 12345678' -> 'xx5678'."""
    if not text:
        return text
    s = _CARD.sub(_keep_last4, text)
    s = _BSB_ACCT.sub(_keep_last4, s)
    s = _ACCT_SPACED.sub(_keep_last4, s)
    s = _LONG.sub(_keep_last4, s)
    return s


# --------------------------------------------------------------------------- statements

EXTRACT_FIELDS = ["statement_id", "seq", "account_id", "source_file", "source_page", "source_line",
                  "date", "description_raw", "amount", "balance_shown"]


def write_statement(meta: dict, rows: list[dict]) -> Path:
    """Write one parsed statement to 02_extracted/<id>.csv and <id>.meta.json.

    rows: dicts with page, line, date (date), description (str),
          amount (Decimal, + = money in), balance (Decimal or None).
    """
    sid = meta["statement_id"]
    out_rows = []
    for i, r in enumerate(rows, 1):
        if not isinstance(r.get("date"), dt.date):
            raise TypeError(f"{sid} row {i}: date must be a datetime.date")
        if not isinstance(r.get("amount"), Decimal):
            raise TypeError(f"{sid} row {i}: amount must be Decimal, got {type(r.get('amount')).__name__}")
        bal = r.get("balance")
        if bal is not None and not isinstance(bal, Decimal):
            raise TypeError(f"{sid} row {i}: balance must be Decimal or None")
        out_rows.append({
            "statement_id": sid,
            "seq": i,
            "account_id": meta["account_id"],
            "source_file": meta["source_file"],
            "source_page": r.get("page", ""),
            "source_line": r.get("line", ""),
            "date": r["date"],
            "description_raw": mask(" ".join(str(r.get("description", "")).split())),
            "amount": r["amount"],
            "balance_shown": bal,
        })
    meta_out = {}
    for k, v in meta.items():
        if isinstance(v, Decimal):
            v = fmt_money(v)
        elif isinstance(v, dt.date):
            v = v.isoformat()
        meta_out[k] = v
    meta_out["rows"] = len(out_rows)
    write_csv(p("02_extracted", f"{sid}.csv"), out_rows, EXTRACT_FIELDS)
    f = p("02_extracted", f"{sid}.meta.json")
    f.write_text(json.dumps(meta_out, indent=2), encoding="utf-8")
    return f


def read_statement(sid: str) -> tuple[dict, list[dict]]:
    mf = p("02_extracted", f"{sid}.meta.json")
    if not mf.exists():
        raise FileNotFoundError(sid)
    meta = json.loads(mf.read_text(encoding="utf-8"))
    for k in ("period_start", "period_end"):
        meta[k] = iso(meta[k]) if meta.get(k) else None
    for k in ("opening_balance", "closing_balance"):
        meta[k] = money(meta.get(k) or "")
    rows = read_csv(p("02_extracted", f"{sid}.csv"), required=True)
    for r in rows:
        r["date"] = iso(r["date"])
        r["amount"] = money(r["amount"])
        r["balance_shown"] = money(r["balance_shown"])
        r["seq"] = int(r["seq"])
    return meta, rows


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())
