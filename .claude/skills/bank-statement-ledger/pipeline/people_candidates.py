"""Phase 3.2 - list person-to-person payments so you can say who is who.

  python scripts/people_candidates.py

Finds payments that look like they went to or came from a person (transfer keywords,
PayID/Osko, no match to one of your own accounts) and groups them by payee_key.
Claude (Haiku is enough) proposes which keys are the same person; you confirm
config/people.csv and give each person a treatment:
  Loan                 money out = Loan out, money in = Loan in (net = who owes whom)
  Gift or shared bill  personal, not income or spending for tax
  Business customer    money in is business income
  Business supplier    money out is a business expense (category still needed)
  Ask me               stays on your review list
Writes: review/people_candidates.csv (only payee keys not already covered by people.csv or a rule)
"""
from __future__ import annotations

from decimal import Decimal

from classify_rules import PeopleBook, RuleBook
from common import load_accounts, load_project, money, p, read_csv, write_csv


def main():
    cfg = load_project()
    accounts = load_accounts()
    keywords = [k.upper() for k in cfg["transfer_keywords"]] + ["DIRECT CREDIT", "PAYMENT FROM", "PAYMENT TO"]
    own = [n.upper() for n in cfg.get("own_names", []) if n]
    last4s = [a["last4"] for a in accounts.values() if a.get("last4")]
    tx = read_csv(p("03_data", "transactions_keyed.csv"), required=True)
    matched = {x for m in read_csv(p("03_data", "transfer_matches.csv")) for x in (m["out_txn_id"], m["in_txn_id"])}
    people, rules = PeopleBook.load(), RuleBook.load()

    groups: dict[str, list] = {}
    for r in tx:
        if r["txn_id"] in matched:
            continue
        k = r["payee_key"]
        if not any(w in k for w in keywords) or any(l4 in k for l4 in last4s) or any(n in k for n in own):
            continue
        if people.match(k) or rules.match(k, money(r["amount"]), r["account_id"]):
            continue
        groups.setdefault(k, []).append(r)
    out = []
    for k, rows in groups.items():
        amts = [money(r["amount"]) for r in rows]
        out.append({"payee_key": k, "rows": len(rows),
                    "total_in": sum((a for a in amts if a > 0), Decimal("0.00")),
                    "total_out": sum((a for a in amts if a < 0), Decimal("0.00")),
                    "first_date": min(r["date"] for r in rows), "last_date": max(r["date"] for r in rows),
                    "samples": " | ".join(list(dict.fromkeys(r["description_raw"] for r in rows))[:3])})
    out.sort(key=lambda r: -(r["total_in"] - r["total_out"]))
    write_csv(p("review", "people_candidates.csv"), out,
              ["payee_key", "rows", "total_in", "total_out", "first_date", "last_date", "samples"])
    print(f"Possible person-to-person payee keys not yet mapped: {len(out)} -> review/people_candidates.csv")
    print(f"People already in config/people.csv: {len({r['person'] for r in people.rows})}")
    if people.errors:
        for e in people.errors:
            print("  " + e)


if __name__ == "__main__":
    main()
