"""Phase 4.2 - classify every row and build your review list.

  python scripts/classify.py

First source that applies wins, and every row records which one it was (classified_by):
  1. a matched internal transfer             03_data/transfer_matches.csv       -> MATCH:T0031
     (a txn decision with another type removes the row from matching, so it lands in 2)
  2. your decision for this transaction      config/decisions.csv  scope=txn      -> D0012
  3. your decision for this payee            config/decisions.csv  scope=payee    -> D0007
  4. your decision for this person, or the   config/decisions.csv  scope=person / -> D0003 / PERSON:Alex
     person's treatment in people.csv        config/people.csv
  5. a payee rule                            config/rules.csv                     -> R0412
  6. nothing: type Unknown, goes to review                                         -> NONE
A matched transfer the owner confirmed (decision with a transfer type) keeps its pair.
Your decisions always beat Claude's rules. Claude never edits rows - it edits rules.

Writes: 03_data/classified.csv   the full ledger (all years)
        review/review_queue.xlsx  grouped by payee/person, biggest money first, with dropdowns
        review/rule_conflicts.csv near-identical payees that the rules put in different categories
Refuses to overwrite review_queue.xlsx if it holds decisions not yet applied
(run apply_review.py first).
"""
from __future__ import annotations

import difflib
import re
import sys
from decimal import Decimal

from classify_rules import PeopleBook, RuleBook
from common import (BP_VALUES, LOAN_TYPES, PNL_TYPES, TRANSFER_TYPES, TYPES, load_accounts, load_project,
                    money, p, read_csv, write_csv)

LEDGER_FIELDS = ["txn_id", "fy", "date", "account_id", "account_name", "original_description",
                 "cleaned_description", "counterparty", "amount", "money_in", "money_out", "type", "category",
                 "ato_label", "business_personal", "business_pct", "match_id", "classified_by", "confidence",
                 "review_status", "review_reasons", "notes", "source_file", "source_page", "source_line",
                 "statement_id", "balance_shown", "payee_key"]
DECIDE_COLS = ["decide_type", "decide_category", "decide_business_personal", "decide_business_pct",
               "decide_person", "decide_ask_accountant", "decide_note"]
QUEUE = p("review", "review_queue.xlsx")


def queue_has_pending_decisions() -> bool:
    if not QUEUE.exists():
        return False
    from openpyxl import load_workbook
    wb = load_workbook(QUEUE, read_only=True, data_only=True)
    for name in ("Groups", "Transactions"):
        if name not in wb.sheetnames:
            continue
        rows = wb[name].iter_rows(values_only=True)
        header = list(next(rows, []) or [])
        idx = [i for i, h in enumerate(header) if h in DECIDE_COLS]
        for r in rows:
            if any(r[i] not in (None, "") for i in idx if i < len(r)):
                return True
    return False


def resolve_type(t: str, amount: Decimal) -> str:
    """'Loan' in a decision means Loan out or Loan in depending on the direction of the money."""
    if t == "Loan":
        return "Loan out" if amount < 0 else "Loan in"
    return t


def treatment_result(treatment: str, amount: Decimal) -> dict:
    if treatment == "Loan":
        return {"type": resolve_type("Loan", amount), "bp": "Personal", "conf": "high"}
    if treatment == "Gift or shared bill":
        return {"type": "Gift or shared bill", "bp": "Personal", "conf": "high"}
    if treatment == "Business customer":
        if amount > 0:
            return {"type": "Business income", "bp": "Business", "conf": "high", "category": "Sales and fees"}
        return {"type": "Unknown", "bp": "", "conf": "low", "why": "money paid OUT to a business customer (refund?)"}
    if treatment == "Business supplier":
        if amount < 0:
            return {"type": "Expense", "bp": "Business", "conf": "medium", "why": "supplier - category needed"}
        return {"type": "Refund", "bp": "Business", "conf": "medium", "why": "money IN from a supplier - refund?"}
    return {"type": "Unknown", "bp": "", "conf": "low", "why": "people.csv says: ask me"}


def title(key: str) -> str:
    return " ".join(w if re.fullmatch(r"XX\d{4}", w) else w.capitalize() for w in key.split())


def main():
    if queue_has_pending_decisions():
        print("FAIL: review/review_queue.xlsx has decisions that were not applied yet.")
        print("Run: python scripts/apply_review.py   (then re-run classify.py)")
        sys.exit(1)

    cfg = load_project()
    accounts = load_accounts()
    cats = {c["category"]: c for c in read_csv(p("config", "categories.csv"), required=True) if c.get("category")}
    clean = {r["payee_key"]: r["clean_name"] for r in read_csv(p("config", "clean_names.csv")) if r.get("clean_name")}
    rules, people = RuleBook.load(), PeopleBook.load()
    if rules.errors or people.errors:
        print("FAIL: fix these in config/ first:")
        for e in (rules.errors + people.errors)[:30]:
            print("  " + e)
        sys.exit(1)
    decisions = read_csv(p("config", "decisions.csv"))
    dec = {(d["scope"], d["key"]): d for d in decisions if d.get("scope") and d.get("key")}
    matches = read_csv(p("03_data", "transfer_matches.csv"))
    match_of = {}
    for m in matches:
        match_of[m["out_txn_id"]] = m
        match_of[m["in_txn_id"]] = m
    cash_kw = [k.upper() for k in cfg["cash_deposit_keywords"]]
    big = Decimal(str(cfg["large_business_item_threshold"]))

    tx = read_csv(p("03_data", "transactions_keyed.csv"), required=True)
    ledger = []
    for r in tx:
        amt = money(r["amount"])
        key = r["payee_key"]
        acct = accounts[r["account_id"]]
        why, notes = [], []
        res = {"type": "Unknown", "category": "", "bp": "", "pct": "", "counterparty": "", "by": "NONE",
               "conf": "low", "match_id": "", "user": False, "ask": False}

        def from_decision(d):
            res.update(type=resolve_type(d.get("type") or "Unknown", amt), category=d.get("category", ""),
                       bp=d.get("business_personal", ""), pct=d.get("business_pct", ""),
                       counterparty=d.get("counterparty", "") or res["counterparty"], by=d["decision_id"],
                       conf="high", user=True, ask=(d.get("ask_accountant", "").upper() == "Y"))
            if d.get("note"):
                notes.append(d["note"])

        person = people.match(key)
        if person:
            res["counterparty"] = person["person"]

        txn_dec, payee_dec = dec.get(("txn", r["txn_id"])), dec.get(("payee", key))
        if r["txn_id"] in match_of:
            # A txn decision with a non-transfer type never gets here: match_transfers.py skips it.
            m = match_of[r["txn_id"]]
            res.update(type=m["type"], category="Transfer", by=f"MATCH:{m['match_id']}", conf=m["confidence"],
                       match_id=m["match_id"], counterparty="(own account)")
            confirm = next((d for d in (txn_dec, payee_dec) if d and d.get("type") in TRANSFER_TYPES), None)
            if confirm:  # the owner confirmed this pairing on the review list
                res.update(by=f"MATCH:{m['match_id']}+{confirm['decision_id']}", conf="high", user=True)
                if confirm.get("note"):
                    notes.append(confirm["note"])
            elif m["note"]:
                why.append("transfer match: " + m["note"])
            if m["crosses_fy"]:
                notes.append("transfer pair crosses 30 June")
        elif txn_dec:
            from_decision(txn_dec)
        elif ("payee", key) in dec:
            from_decision(dec[("payee", key)])
        elif person and ("person", person["person"]) in dec:
            from_decision(dec[("person", person["person"])])
        elif person:
            t = treatment_result(person["treatment"], amt)
            res.update(type=t["type"], bp=t["bp"], conf=t["conf"], by=f"PERSON:{person['person']}",
                       category=t.get("category", "Loan" if t["type"] in LOAN_TYPES else ""))
            if t.get("why"):
                why.append(t["why"])
        else:
            rule = rules.match(key, amt, r["account_id"])
            if rule:
                res.update(type=rule["type"], category=rule.get("category", ""), bp=rule.get("business_personal", ""),
                           pct=rule.get("business_pct", ""), by=rule["rule_id"], conf=rule["confidence"])
            else:
                why.append("no rule for this payee")

        if res["bp"] == "account":
            res["bp"] = acct["default_use"].capitalize()
        t = res["type"]
        if t not in TYPES:
            why.append(f"type {t!r} is not allowed")
            res["type"] = t = "Unknown"
        if not res["user"] and res["conf"] != "high" and res["by"] != "NONE":
            why.append(f"{res['conf']} confidence")
        if t in PNL_TYPES:
            if not res["category"]:
                why.append("category needed")
            elif res["category"] not in cats:
                why.append(f"category {res['category']!r} not in categories.csv")
            if res["bp"] not in BP_VALUES:
                why.append("business or personal?")
        if res["bp"] == "Mixed" and not res["pct"]:
            why.append("business % needed")
        if amt > 0 and any(k in key or k in r["description_raw"].upper() for k in cash_kw) and not res["user"]:
            why.append("cash deposit - could be income")
        if t == "Unknown" and "no rule for this payee" not in why and not res["ask"]:
            why.append("type unknown")
        if t == "Expense" and res["bp"] == "Business" and -amt >= big:
            notes.append(f"large business item (>= ${big:,.0f}) - accountant to check if it is a depreciating asset")

        cat = cats.get(res["category"], {})
        status = ("Ask accountant" if res["ask"] else "Reviewed") if res["user"] else ("Needs review" if why else "Auto")
        if res["user"] and why and not res["ask"]:
            status = "Needs review"  # your decision left something open (e.g. no category)
        ledger.append({
            "txn_id": r["txn_id"], "fy": r["fy"], "date": r["date"], "account_id": r["account_id"],
            "account_name": acct["account_name"], "original_description": r["description_raw"],
            "cleaned_description": clean.get(key) or (res["counterparty"] if res["counterparty"] not in ("", "(own account)")
                                                      else title(key)),
            "counterparty": res["counterparty"], "amount": amt,
            "money_in": amt if amt > 0 else "", "money_out": -amt if amt < 0 else "",
            "type": t, "category": res["category"], "ato_label": cat.get("ato_label", ""),
            "business_personal": res["bp"], "business_pct": res["pct"], "match_id": res["match_id"],
            "classified_by": res["by"], "confidence": res["conf"], "review_status": status,
            "review_reasons": "; ".join(dict.fromkeys(why)), "notes": "; ".join(dict.fromkeys(notes)),
            "source_file": r["source_file"], "source_page": r["source_page"], "source_line": r["source_line"],
            "statement_id": r["statement_id"], "balance_shown": r["balance_shown"], "payee_key": key,
        })

    assert len(ledger) == len(tx)
    write_csv(p("03_data", "classified.csv"), ledger, LEDGER_FIELDS)
    groups = build_queue(ledger, cats)
    conflicts = rule_conflicts(ledger)

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for x in ledger:
        by_status[x["review_status"]] = by_status.get(x["review_status"], 0) + 1
        by_type[x["type"]] = by_type.get(x["type"], 0) + 1
    print(f"Classified {len(ledger)} rows: " + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())))
    print("By type: " + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])))
    print(f"Review list: {groups} groups -> review/review_queue.xlsx")
    if conflicts:
        print(f"Possible rule inconsistencies: {conflicts} -> review/rule_conflicts.csv")
    print("Next: fill in review_queue.xlsx, then python scripts/apply_review.py; or build: python scripts/build_outputs.py")


def build_queue(ledger: list[dict], cats: dict) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    todo = [x for x in ledger if x["review_status"] == "Needs review"]
    groups: dict[tuple, list] = {}
    for x in todo:
        if x["classified_by"].startswith("PERSON:"):
            g = ("person", x["counterparty"])
        else:
            g = ("payee", x["payee_key"])
        groups.setdefault(g, []).append(x)
    ordered = sorted(groups.items(), key=lambda kv: -sum(abs(x["amount"]) for x in kv[1]))

    wb = Workbook()
    ws = wb.active
    ws.title = "How to use"
    for line in [
        "Your review list. One line per payee or person on 'Groups' - one decision covers all its rows.",
        "Fill only the yellow columns. Leave a row blank to skip it for now.",
        "decide_type: pick from the list. 'Loan' becomes Loan out / Loan in by direction automatically.",
        "decide_category + decide_business_personal: needed for income, expenses and refunds.",
        "decide_business_pct: only for Mixed (e.g. phone 60). Your accountant confirms the final %.",
        "decide_person: name the person for transfers to/from friends or family (builds the loans list).",
        "decide_ask_accountant: Y if you don't know - it goes on the accountant's open-questions list.",
        "Exceptions to a group: decide those single rows on the 'Transactions' sheet (they win over the group).",
        "Save, close, then run: python scripts/apply_review.py  and re-run the pipeline.",
    ]:
        ws.append([line])
    ws.column_dimensions["A"].width = 110

    yellow = PatternFill("solid", fgColor="FFF2CC")
    bold = Font(bold=True)
    lists = wb.create_sheet("Lists")
    type_opts = TYPES + ["Loan"]
    cat_opts = sorted(cats)
    for i, v in enumerate(type_opts, 2):
        lists.cell(i, 1, v)
    for i, v in enumerate(cat_opts, 2):
        lists.cell(i, 2, v)
    for i, v in enumerate(BP_VALUES, 2):
        lists.cell(i, 3, v)
    lists.cell(2, 4, "Y")
    for c, h in enumerate(["types", "categories", "business_personal", "yes"], 1):
        lists.cell(1, c, h).font = bold

    def sheet(name, header, rows):
        s = wb.create_sheet(name, 1 if name == "Groups" else 2)
        s.append(header)
        for c in s[1]:
            c.font = bold
        for row in rows:
            s.append(row)
        n = max(len(rows) + 1, 2)
        first = len(header) - len(DECIDE_COLS) + 1
        for j, h in enumerate(DECIDE_COLS):
            col = first + j
            letter = s.cell(1, col).column_letter
            s.cell(1, col).fill = yellow
            for i in range(2, n + 1):
                s.cell(i, col).fill = yellow
            src = {"decide_type": f"=Lists!$A$2:$A${len(type_opts) + 1}",
                   "decide_category": f"=Lists!$B$2:$B${len(cat_opts) + 1}",
                   "decide_business_personal": "=Lists!$C$2:$C$4",
                   "decide_ask_accountant": "=Lists!$D$2:$D$2"}.get(h)
            if src:
                dv = DataValidation(type="list", formula1=src, allow_blank=True)
                s.add_data_validation(dv)
                dv.add(f"{letter}2:{letter}{n}")
        s.freeze_panes = "B2"
        for col in s.columns:
            width = min(max(len(str(c.value or "")) for c in col) + 2, 60)
            s.column_dimensions[col[0].column_letter].width = max(width, 12)

    g_rows, t_rows = [], []
    for n, ((scope, key), rows) in enumerate(ordered, 1):
        gid = f"G{n:04d}"
        tin = sum((x["amount"] for x in rows if x["amount"] > 0), Decimal("0.00"))
        tout = sum((x["amount"] for x in rows if x["amount"] < 0), Decimal("0.00"))
        reasons = "; ".join(dict.fromkeys(r for x in rows for r in x["review_reasons"].split("; ") if r))
        g_rows.append([gid, scope, key, len(rows), tin, tout,
                       " ".join(sorted({x["account_id"] for x in rows})), min(x["date"] for x in rows),
                       max(x["date"] for x in rows),
                       " | ".join(list(dict.fromkeys(x["original_description"] for x in rows))[:3]),
                       rows[0]["type"], rows[0]["category"], rows[0]["business_personal"], reasons]
                      + [None] * len(DECIDE_COLS))
        for x in rows:
            t_rows.append([x["txn_id"], gid, x["date"], x["account_id"], x["original_description"],
                           x["amount"], x["type"], x["category"], x["review_reasons"]] + [None] * len(DECIDE_COLS))
    # Amounts here are for display; apply_review.py reads back decisions only, never amounts.
    sheet("Groups", ["group_id", "scope", "key", "rows", "total_in", "total_out", "accounts", "first_date",
                     "last_date", "samples", "current_type", "current_category", "current_bp", "why"] + DECIDE_COLS, g_rows)
    sheet("Transactions", ["txn_id", "group_id", "date", "account_id", "description", "amount", "current_type",
                           "current_category", "why"] + DECIDE_COLS, t_rows)
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    wb.save(QUEUE)
    return len(ordered)


def rule_conflicts(ledger: list[dict]) -> int:
    """Near-identical payee keys that rules put in different categories (e.g. BUNNINGS 123 vs BUNNINGS)."""
    seen: dict[str, tuple] = {}
    for x in ledger:
        if x["classified_by"].startswith("R"):
            seen.setdefault(x["payee_key"], (x["type"], x["category"], x["business_personal"], x["classified_by"]))
    by_stem: dict[str, list] = {}
    for k in seen:
        by_stem.setdefault(k.split()[0] if k.split() else k, []).append(k)
    out = []
    for keys in by_stem.values():
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if seen[a][:3] != seen[b][:3] and difflib.SequenceMatcher(None, a, b).ratio() >= 0.85:
                    out.append({"payee_a": a, "rule_a": seen[a][3], "class_a": " / ".join(seen[a][:3]),
                                "payee_b": b, "rule_b": seen[b][3], "class_b": " / ".join(seen[b][:3])})
    write_csv(p("review", "rule_conflicts.csv"), out, ["payee_a", "rule_a", "class_a", "payee_b", "rule_b", "class_b"])
    return len(out)


if __name__ == "__main__":
    main()
