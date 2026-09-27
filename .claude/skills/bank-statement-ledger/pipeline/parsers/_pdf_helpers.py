"""Helpers for PDF statement parsers (pdfplumber).

Bank statements are tables drawn as positioned text. Reading them by word
x-position is far more reliable than splitting extract_text() on spaces,
because it tells you which column (debit / credit / balance) a number sits in.
Getting that column wrong is the most common extraction bug: the amount is
right but the sign is wrong, and only the balance check catches it.
"""
from __future__ import annotations

import re

MONEY_WORD = re.compile(r"^\(?-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})\)?-?$|^\(?-?\$?\d+\.\d{2}\)?-?$")


def dedupe(page):
    """Drop letters printed twice on top of each other. Some banks fake bold text that way
    (CommBank headings), which pdfplumber otherwise reads as "AAccccoouunntt"."""
    try:
        return page.dedupe_chars()
    except AttributeError:  # pdfplumber older than 0.10
        return page


def page_lines(page, y_tolerance: float = 3.0) -> list[dict]:
    """Group the words on a page into lines: [{"top", "words": [{text,x0,x1,top}], "text"}]."""
    words = dedupe(page).extract_words(x_tolerance=1.5, y_tolerance=2, keep_blank_chars=False,
                               use_text_flow=False)
    words.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[dict] = []
    for w in words:
        if lines and abs(lines[-1]["top"] - w["top"]) <= y_tolerance:
            lines[-1]["words"].append(w)
        else:
            lines.append({"top": w["top"], "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
        ln["text"] = " ".join(w["text"] for w in ln["words"])
    return lines


def words_between(line: dict, x_min: float, x_max: float) -> list[dict]:
    """Words whose horizontal centre lies in [x_min, x_max)."""
    return [w for w in line["words"] if x_min <= (w["x0"] + w["x1"]) / 2 < x_max]


def text_between(line: dict, x_min: float, x_max: float) -> str:
    return " ".join(w["text"] for w in words_between(line, x_min, x_max))


def money_words(line: dict) -> list[dict]:
    """Money-looking words, with a following CR/DR word folded into the amount text."""
    out, ws = [], line["words"]
    for i, w in enumerate(ws):
        if MONEY_WORD.match(w["text"]):
            item = dict(w)
            if i + 1 < len(ws) and ws[i + 1]["text"].upper() in {"CR", "DR"}:
                item["text"] = w["text"] + " " + ws[i + 1]["text"]
                item["x1"] = ws[i + 1]["x1"]
            out.append(item)
    return out


def nearest_column(x_right: float, columns: dict[str, float], max_gap: float = 25.0) -> str | None:
    """Which column's right edge is closest to this (right-aligned) number? None if none is close."""
    name, dist = None, max_gap
    for col, edge in columns.items():
        d = abs(edge - x_right)
        if d <= dist:
            name, dist = col, d
    return name
