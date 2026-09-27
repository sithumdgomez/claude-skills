"""WORKED EXAMPLE - parser for the made-up "Demo Bank" PDF layout used by tools/make_demo.py.

Copy this file to <yourbank>_pdf.py and adapt it; do not use it for a real bank as-is.
It shows the traps real statements have and how to handle each one:
  - dates printed without a year ("03 Jul")      -> parse_date(..., period_start, period_end)
  - debit and credit in separate columns          -> sign decided by the column a number sits in
  - balances with CR/DR suffixes as separate words -> money_words() folds them in
  - descriptions wrapping onto a second line       -> continuation lines appended to the last row
  - opening / brought forward / carried forward / closing lines -> skipped, never treated as rows
  - page numbers and headers on every page         -> ignored
  - a line with an amount but no date              -> raise, so it can't be silently dropped
"""
from __future__ import annotations

import re

from common import mask, parse_date, parse_money
from parsers._pdf_helpers import money_words, nearest_column, page_lines, text_between

MONTHS = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"}
SKIP = ("BROUGHT FORWARD", "CARRIED FORWARD", "OPENING BALANCE", "CLOSING BALANCE")


def parse(path, ctx):
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        head = pdf.pages[0].extract_text() or ""
        m = re.search(r"Statement period\s+(.+?)\s+to\s+(.+?)\s*$", head, re.M | re.I)
        if not m:
            raise ValueError("statement period not found on page 1")
        start, end = parse_date(m[1]), parse_date(m[2])
        m_open = re.search(r"Opening balance\s+\$?([\d,]+\.\d{2}(?:\s*(?:CR|DR))?)", head, re.I)
        m_close = re.search(r"Closing balance\s+\$?([\d,]+\.\d{2}(?:\s*(?:CR|DR))?)", head, re.I)
        opening = parse_money(m_open[1]) if m_open else None
        closing = parse_money(m_close[1]) if m_close else None

        rows, cur = [], None
        for pno, page in enumerate(pdf.pages, 1):
            cols, desc_x, amount_left = None, None, None
            for lno, ln in enumerate(page_lines(page), 1):
                words, text = ln["words"], ln["text"]
                if cols is None:
                    # Everything above the table header is page furniture.
                    if words and words[0]["text"] == "Date" and "Balance" in text:
                        cols = {w["text"].lower(): w["x1"] for w in words if w["text"] in ("Debit", "Credit", "Balance")}
                        desc_x = next(w["x0"] for w in words if w["text"] == "Transaction")
                        amount_left = min(cols.values()) - 60
                    continue
                if re.match(r"^Page \d+ of \d+", text):
                    continue
                if any(s in text.upper() for s in SKIP):
                    cur = None
                    continue
                nums = money_words(ln)
                is_new = (len(words) >= 2 and re.fullmatch(r"\d{1,2}", words[0]["text"])
                          and words[1]["text"][:3].upper() in MONTHS and words[0]["x0"] < desc_x - 5)
                if is_new:
                    date = parse_date(f"{words[0]['text']} {words[1]['text']}", start, end)
                    amount = balance = None
                    for n in nums:
                        col = nearest_column(n["x1"], cols)
                        if col == "debit":
                            amount = -parse_money(n["text"])
                        elif col == "credit":
                            amount = parse_money(n["text"])
                        elif col == "balance":
                            balance = parse_money(n["text"])
                    if amount is None:
                        raise ValueError(f"page {pno} line {lno}: no debit or credit amount: {mask(text)}")
                    cur = {"page": pno, "line": lno, "date": date,
                           "description": text_between(ln, desc_x - 2, amount_left),
                           "amount": amount, "balance": balance}
                    rows.append(cur)
                elif nums:
                    raise ValueError(f"page {pno} line {lno}: amount on a line with no date: {mask(text)}")
                elif cur is not None:
                    cur["description"] += " " + text_between(ln, desc_x - 2, amount_left)

    return {"period_start": start, "period_end": end, "opening_balance": opening,
            "closing_balance": closing, "balance_source": "statement"}, rows
