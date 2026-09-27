"""Bank parsers. One module per bank and file type: <parser_prefix>_pdf.py / <parser_prefix>_csv.py.

Each module exposes:  parse(path, ctx) -> (meta, rows)
  ctx  = {"statement_id", "account_id", "source_file", "period_hint": (start, end) or (None, None)}
  meta = {"period_start": date, "period_end": date,
          "opening_balance": Decimal | None, "closing_balance": Decimal | None,
          "balance_source": "statement" | "csv_running" | "none"}
  rows = [{"page", "line", "date": date, "description": str,
           "amount": Decimal (+ = money in), "balance": Decimal | None}, ...]
Files starting with "_" are helpers and worked examples, not parsers for a real bank.
"""
