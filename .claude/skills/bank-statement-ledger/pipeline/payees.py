"""Phase 2.1 - turn raw descriptions into payee keys and group them.

  python scripts/payees.py

Claude classifies payees, not rows: ~10,000 rows usually collapse to ~1,000 payees,
and one rule then covers every row for that payee. The original description is never
changed - payee_key is an extra column.

Normalising: upper-case; drop dates, times, card numbers, reference numbers,
purchase prefixes (VISA PURCHASE, EFTPOS ...), payment-processor prefixes (SQ *, PAYPAL *),
foreign-currency notes and trailing location codes (AU, NSW ...). Project-specific
fixes go in config/normalise.csv (pattern,replacement,note - regex, applied first),
so the rules can be tuned without editing this script.

Writes: 03_data/transactions_keyed.csv  transactions + payee_key
        03_data/payees.csv              one row per payee_key, biggest dollar value first,
                                        status: ruled / own-transfer / person / new - only "new" goes to Claude
"""
from __future__ import annotations

import re
import statistics
from decimal import Decimal

from classify_rules import PeopleBook, RuleBook
from common import load_accounts, load_project, money, p, read_csv, write_csv

_MONTH = (r"(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?"
          r"|SEP(?:T(?:EMBER)?)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)(?![A-Z])")
BUILTIN = [
    (r"\bVALUE DATE:?\s*\S+", " "),
    (r"\b\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?\b", " "),          # dates 03/07/2022, 03/07
    (rf"\b\d{{1,2}}\s?{_MONTH}(?:\s?\d{{2,4}})?\b", " "),          # 03 JUL 2022, 03JUL
    (r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " "),                           # times
    (r"\bCARD\s*(?:NO\.?|NUMBER)?\s*(?:XX|X+)?\d{4}\b", " "),        # CARD xx1234
    (r"\b(?:REF|REFERENCE|RECEIPT|RCPT|TRACE|AUTH)\b\s*(?:NO\.?)?\s*[:#]?\s*[A-Z0-9\-]*\d[A-Z0-9\-]*", " "),
    (r"\b[A-Z]{3}\s?\d+\.\d{2}\b", " "),                               # USD 12.00
    (r"\b(?:INCL\.?|INCLUDING)?\s*(?:FOREIGN|INTL|INTERNATIONAL)\s*(?:TRANSACTION|TXN|CURRENCY)?\s*FEE\b", " "),
    (r"^(?:(?:VISA|MASTERCARD|EFTPOS|DEBIT CARD|CARD|POS|PURCHASE|RECURRING|TAP|CONTACTLESS|AUTHORISATION ONLY)\b\s*)+", ""),
    (r"^(?:SQ|SQU|SP|ZLR|LS|TST|PAYPAL|PP|IZ|SMP)\s?\*\s?", ""),      # payment processors
    (r"[^A-Z0-9&'*/\- ]", " "),
    (r"\s+", " "),
]
_TRAIL = {"AU", "AUS", "AUSTRALIA", "NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT", "CARD", "X", "XX"}


class Normaliser:
    def __init__(self):
        custom = [(r["pattern"], r.get("replacement", "")) for r in read_csv(p("config", "normalise.csv")) if r.get("pattern")]
        self.steps = [(re.compile(a, re.I), b) for a, b in custom + BUILTIN]

    def key(self, desc: str) -> str:
        s = (desc or "").upper()
        for rx, rep in self.steps:
            s = rx.sub(rep, s)
        toks = s.strip(" -*/").split()
        while toks and (toks[-1] in _TRAIL or toks[-1].isdigit() or re.fullmatch(r"X+\d{0,4}", toks[-1])
                        and not re.fullmatch(r"XX\d{4}", toks[-1])):
            toks.pop()
        return " ".join(toks) or "(NO DESCRIPTION)"


_GENERIC = {"THE", "MR", "MRS", "MS", "DR", "DIRECT", "CREDIT", "DEBIT", "TRANSFER", "TFR", "FROM", "TO",
            "PAYMENT", "PAYMENTS", "OSKO", "PAYID", "INTERNET", "ONLINE", "BPAY", "FAST", "NPP", "PAY", "ANYONE"}


def stem(key: str) -> str:
    """Generic leading words plus the first meaningful word: 'DIRECT CREDIT ACME PTY' -> 'DIRECT CREDIT ACME'.
    Helps Claude write one 'contains' rule for a merchant that appears with many suffixes."""
    out = []
    for t in key.split():
        out.append(t)
        if t not in _GENERIC and len(t) >= 3:
            break
    return " ".join(out) or key


def main():
    tx = read_csv(p("03_data", "transactions.csv"), required=True)
    norm = Normaliser()
    book, people = RuleBook.load(), PeopleBook.load()
    cfg, accounts = load_project(), load_accounts()
    own_rx = [re.compile(rf"(?<!\d){a['last4']}(?!\d)") for a in accounts.values() if a.get("last4")]
    own_names = [n.upper() for n in cfg.get("own_names", []) if n]
    for r in tx:
        r["payee_key"] = norm.key(r["description_raw"])
    write_csv(p("03_data", "transactions_keyed.csv"), tx, list(tx[0].keys()) if tx else ["txn_id"])

    groups: dict[str, list] = {}
    for r in tx:
        groups.setdefault(r["payee_key"], []).append(r)
    out = []
    for key, rows in groups.items():
        amts = [money(r["amount"]) for r in rows]
        tin = sum((a for a in amts if a > 0), Decimal("0.00"))
        tout = sum((a for a in amts if a < 0), Decimal("0.00"))
        months = sorted({r["date"][:7] for r in rows})
        samples = []
        for r in rows:
            if r["description_raw"] not in samples:
                samples.append(r["description_raw"])
            if len(samples) == 3:
                break
        if any(book.match(key, a, r["account_id"]) for a, r in zip(amts, rows)):
            status = "ruled"
        elif any(rx.search(key) for rx in own_rx) or any(n in key for n in own_names):
            status = "own-transfer"   # handled by match_transfers.py, not by a rule
        elif people.match(key):
            status = "person"         # handled by config/people.csv
        else:
            status = "new"
        out.append({
            "payee_key": key, "stem": stem(key), "rows": len(rows), "total_in": tin, "total_out": tout,
            "abs_total": tin - tout, "accounts": " ".join(sorted({r["account_id"] for r in rows})),
            "first_date": min(r["date"] for r in rows), "last_date": max(r["date"] for r in rows),
            "typical_amount": statistics.median(abs(a) for a in amts),
            "months_active": len(months), "status": status,
            "samples": " | ".join(samples),
        })
    out.sort(key=lambda r: (-r["abs_total"], r["payee_key"]))
    write_csv(p("03_data", "payees.csv"), out,
              ["payee_key", "stem", "rows", "total_in", "total_out", "abs_total", "accounts", "first_date",
               "last_date", "typical_amount", "months_active", "status", "samples"])

    new = [r for r in out if r["status"] == "new"]
    print(f"{len(tx)} rows -> {len(out)} payee keys ({len({r['stem'] for r in out})} stems)")
    counts = {st: sum(1 for r in out if r["status"] == st) for st in ("ruled", "own-transfer", "person", "new")}
    print("Status: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"Payees needing a rule (status new): {len(new)} (worth ${sum((r['abs_total'] for r in new), Decimal('0')):,.2f})")
    print("Top 5 by value: " + "; ".join(r["payee_key"] for r in out[:5]))
    print("Next: python scripts/match_transfers.py")


if __name__ == "__main__":
    main()
