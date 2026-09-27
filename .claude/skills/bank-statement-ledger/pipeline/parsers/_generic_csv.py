"""Generic parser for bank CSV exports, driven by a small MAPPING.

A bank-specific module (e.g. parsers/banka_csv.py) usually needs only:

    from parsers._generic_csv import parse_csv
    MAPPING = {
        "has_header": True,            # False if the first row is a transaction
        "date": "Date",                # column name, or 0-based index when has_header is False
        "description": ["Narrative"],  # one or more columns, joined with a space
        "amount": "Amount",            # signed amount column ...
        # "debit": "Debit", "credit": "Credit",   # ... or two columns instead of "amount"
        # "debit_is_positive": True,   # debit column shows 45.20 meaning money out
        # "amount_sign": "debit_positive",  # if a single amount column shows money OUT as positive
        "balance": "Balance",          # running balance column, or None
    }
    def parse(path, ctx):
        return parse_csv(path, ctx, MAPPING)

Look at the masked sample from dump_sample.py before writing a MAPPING; do not
assume a bank's format from memory - formats change over the years.
"""
from __future__ import annotations

import csv
from decimal import Decimal

from common import parse_date, parse_money


def parse_csv(path, ctx, mapping):
    with open(path, newline="", encoding=mapping.get("encoding", "utf-8-sig")) as f:
        raw = list(enumerate(csv.reader(f), 1))
    raw = raw[mapping.get("skip_rows", 0):]
    header = None
    if mapping.get("has_header", True):
        _, header = raw[0]
        header = [h.strip() for h in header]
        raw = raw[1:]

    def col(row, spec):
        if spec is None:
            return None
        if isinstance(spec, int):
            idx = spec
        else:
            if header is None:
                raise ValueError(f"column {spec!r} given by name but has_header is False")
            if spec not in header:
                raise ValueError(f"column {spec!r} not in CSV header {header}")
            idx = header.index(spec)
        return row[idx].strip() if idx < len(row) else ""

    desc_specs = mapping["description"]
    if not isinstance(desc_specs, list):
        desc_specs = [desc_specs]

    rows = []
    for line_no, r in raw:
        if not any(c.strip() for c in r):
            continue
        d = parse_date(col(r, mapping["date"]))
        desc = " ".join(x for x in (col(r, s) for s in desc_specs) if x)
        if "amount" in mapping:
            amt = parse_money(col(r, mapping["amount"]))
            if amt is None:
                raise ValueError(f"line {line_no}: empty amount")
            if mapping.get("amount_sign") == "debit_positive":
                amt = -amt
        else:
            debit = parse_money(col(r, mapping["debit"])) or Decimal("0.00")
            credit = parse_money(col(r, mapping["credit"])) or Decimal("0.00")
            if mapping.get("debit_is_positive", True):
                debit = -abs(debit)
            amt = credit + debit
        bal = parse_money(col(r, mapping.get("balance"))) if mapping.get("balance") is not None else None
        rows.append({"page": "", "line": line_no, "date": d, "description": desc,
                     "amount": amt, "balance": bal})
    if not rows:
        raise ValueError("no transactions found")
    # Many exports list newest first. Reverse the whole file (not a sort) so rows on
    # the same day keep their true order and the running balance still lines up.
    if rows[0]["date"] > rows[-1]["date"]:
        rows.reverse()
    dates = [r["date"] for r in rows]
    meta = {"period_start": min(dates), "period_end": max(dates)}
    if rows[0]["balance"] is not None and rows[-1]["balance"] is not None:
        meta.update(opening_balance=rows[0]["balance"] - rows[0]["amount"],
                    closing_balance=rows[-1]["balance"], balance_source="csv_running")
    else:
        meta.update(opening_balance=None, closing_balance=None, balance_source="none")
    return meta, rows
