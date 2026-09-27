"""Print a masked text sample of one statement, so Claude can write or fix a parser
without ever opening the PDF (Phase 1.1).

  python scripts/dump_sample.py S001              # first and last page, plain text
  python scripts/dump_sample.py S001 --pages 2 3  # chosen pages
  python scripts/dump_sample.py S001 --words      # every word with its x-position (for columns)
  python scripts/dump_sample.py S001 --max-lines 60

Output is also saved to review/samples/<id>_p<page>.txt. Account numbers are masked.
One sample per statement layout is enough - do not dump every statement.
"""
from __future__ import annotations

import argparse
import csv
import re

from common import die, mask, p, read_csv

_YEAR = re.compile(r"^(19|20)\d{2}$")


def mask_word(text: str) -> str:
    # In --words mode numbers are split into separate words, so the line-level
    # mask cannot see "1234 5678" as one account number. Mask every bare digit
    # group of 3+ digits except a plausible year.
    digits = text.replace("-", "")
    if digits.isdigit() and len(digits) >= 3 and not _YEAR.match(digits):
        return "xx" + digits[-4:] if len(digits) >= 5 else "x" * len(digits)
    return mask(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("statement_id")
    ap.add_argument("--pages", nargs="*", type=int)
    ap.add_argument("--words", action="store_true")
    ap.add_argument("--max-lines", type=int, default=80)
    a = ap.parse_args()

    inv = {r["statement_id"]: r for r in read_csv(p("config", "inventory.csv"), required=True)}
    row = inv.get(a.statement_id)
    if not row:
        die(f"{a.statement_id} not in config/inventory.csv")
    path = p("01_statements", row["statement_file"])
    out_dir = p("review", "samples")
    out_dir.mkdir(parents=True, exist_ok=True)

    if row["file_type"] == "csv":
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            lines = [",".join(r) for r in csv.reader(f)]
        pick = lines[:15] + (["..."] + lines[-5:] if len(lines) > 20 else lines[15:])
        text = "\n".join(mask(x) for x in pick)
        out = out_dir / f"{a.statement_id}_csv.txt"
        out.write_text(text, encoding="utf-8")
        print(f"# {a.statement_id} ({row['account_id']}, CSV, {len(lines)} lines) -> {out.relative_to(p())}")
        print(text)
        return

    import pdfplumber
    from parsers._pdf_helpers import page_lines

    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        pages = a.pages or sorted({1, n})
        for pg in pages:
            if not 1 <= pg <= n:
                print(f"(page {pg} does not exist; {n} pages)")
                continue
            lines = page_lines(pdf.pages[pg - 1])
            if a.words:
                body = [f"y={ln['top']:6.1f} | " + "  ".join(
                    f"{mask_word(w['text'])}@{w['x0']:.0f}-{w['x1']:.0f}" for w in ln["words"])
                    for ln in lines]
            else:
                body = [mask(ln["text"]) for ln in lines]
            text = "\n".join(body)
            out = out_dir / f"{a.statement_id}_p{pg}{'_words' if a.words else ''}.txt"
            out.write_text(text, encoding="utf-8")
            print(f"# {a.statement_id} ({row['account_id']}) page {pg} of {n} -> {out.relative_to(p())}")
            print("\n".join(body[:a.max_lines]))
            if len(body) > a.max_lines:
                print(f"... ({len(body) - a.max_lines} more lines in the file)")


if __name__ == "__main__":
    main()
