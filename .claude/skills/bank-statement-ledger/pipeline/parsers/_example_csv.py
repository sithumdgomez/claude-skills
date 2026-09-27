"""WORKED EXAMPLE - CSV export in the made-up format used by tools/make_demo.py
(header row "Date,Description,Amount,Balance", signed amounts, newest transaction first).

A real bank's CSV parser is usually just this: a MAPPING read off the masked header
from dump_sample.py, handed to the generic parser.
"""
from parsers._generic_csv import parse_csv

MAPPING = {
    "has_header": True,
    "date": "Date",
    "description": ["Description"],
    "amount": "Amount",
    "balance": "Balance",
}


def parse(path, ctx):
    return parse_csv(path, ctx, MAPPING)
