"""Phase 3.1 - match internal transfers between your own accounts.

  python scripts/match_transfers.py

A pair is money out of one of your accounts and the same amount into another of
your accounts, -1 to transfer_max_days days later (config/project.json, default 4).
Same amount and date alone is not enough - a $50 grocery bill and a $50 refund can
coincide - so at least one side must carry a transfer signal: the other account's
last 4 digits, one of your own names (own_names in project.json), or a transfer
keyword (TRANSFER, TFR, OSKO, PAYID ...).

Scoring: last-4 hint +40, own name +25, keyword +15, same bank +5, and +20/+15/+10/+5
for 0/1/2/<=4 days apart. Best pairs are taken first; each transaction is used once.
If a transaction had two equally good partners (two $100 transfers in one week)
the pair is kept but flagged "ambiguous" and given medium confidence.

Business -> personal account = Owner drawing; personal -> business = Owner contribution;
anything else between your accounts = Internal transfer.

Manual pairs: config/manual_matches.csv (out_txn_id,in_txn_id,note) - applied first.
A txn-level decision in config/decisions.csv with a non-transfer type keeps that
transaction out of automatic matching (use it for a coincidence the script got wrong).

Writes: 03_data/transfer_matches.csv
        review/transfers_unmatched.csv  rows that look like transfers but found no partner
"""
from __future__ import annotations

import re
import sys
from decimal import Decimal

from common import TRANSFER_TYPES, iso, load_accounts, load_project, money, p, read_csv, write_csv

MATCH_FIELDS = ["match_id", "type", "out_txn_id", "in_txn_id", "out_account", "in_account", "out_date",
                "in_date", "amount", "days_apart", "score", "signals", "confidence", "crosses_fy", "note"]


def pair_type(out_acct: dict, in_acct: dict) -> str:
    if out_acct["default_use"] == "business" and in_acct["default_use"] == "personal":
        return "Owner drawing"
    if out_acct["default_use"] == "personal" and in_acct["default_use"] == "business":
        return "Owner contribution"
    return "Internal transfer"


def main():
    cfg = load_project()
    accounts = load_accounts()
    max_days = int(cfg["transfer_max_days"])
    own_names = [n.upper() for n in cfg.get("own_names", []) if n]
    keywords = [k.upper() for k in cfg["transfer_keywords"]]

    tx = read_csv(p("03_data", "transactions_keyed.csv"), required=True)
    by_id = {r["txn_id"]: r for r in tx}
    for r in tx:
        r["_amt"] = money(r["amount"])
        r["_date"] = iso(r["date"])
        r["_desc"] = (r["description_raw"] + " " + r["payee_key"]).upper()

    decisions = read_csv(p("config", "decisions.csv"))
    blocked = {d["key"] for d in decisions if d.get("scope") == "txn" and d.get("type")
               and d["type"] not in TRANSFER_TYPES}

    l4_rx = {aid: re.compile(rf"(?<!\d){re.escape(a['last4'])}(?!\d)") for aid, a in accounts.items() if a.get("last4")}

    def signals(r, other_acct_id):
        s = []
        if other_acct_id in l4_rx and l4_rx[other_acct_id].search(r["_desc"]):
            s.append("last4")
        if any(n in r["_desc"] for n in own_names):
            s.append("own name")
        if any(k in r["_desc"] for k in keywords):
            s.append("keyword")
        return s

    matches, used = [], set()

    # ---- manual pairs first
    for m in read_csv(p("config", "manual_matches.csv")):
        o, i = by_id.get(m.get("out_txn_id")), by_id.get(m.get("in_txn_id"))
        if not o or not i:
            print(f"FAIL: manual match {m} refers to an unknown txn_id")
            sys.exit(1)
        if o["_amt"] + i["_amt"] != 0 or o["account_id"] == i["account_id"]:
            print(f"FAIL: manual match {o['txn_id']} / {i['txn_id']} does not net to zero between two accounts")
            sys.exit(1)
        if o["_amt"] > 0:
            o, i = i, o
        used.update({o["txn_id"], i["txn_id"]})
        matches.append((o, i, 999, ["manual"], "high", m.get("note", "manual")))

    # ---- candidates
    outs = [r for r in tx if r["_amt"] < 0 and r["txn_id"] not in used and r["txn_id"] not in blocked]
    ins_by_amt: dict[Decimal, list] = {}
    for r in tx:
        if r["_amt"] > 0 and r["txn_id"] not in used and r["txn_id"] not in blocked:
            ins_by_amt.setdefault(r["_amt"], []).append(r)
    cands = []
    for o in outs:
        for i in ins_by_amt.get(-o["_amt"], []):
            if i["account_id"] == o["account_id"]:
                continue
            days = (i["_date"] - o["_date"]).days
            if not -1 <= days <= max_days:
                continue
            sig = sorted(set(signals(o, i["account_id"]) + signals(i, o["account_id"])))
            if not sig:
                continue
            score = (40 if "last4" in sig else 0) + (25 if "own name" in sig else 0) + (15 if "keyword" in sig else 0)
            score += 5 if accounts[o["account_id"]]["bank"] == accounts[i["account_id"]]["bank"] else 0
            score += {0: 20, 1: 15, 2: 10}.get(days, 5 if days >= 0 else 0)
            cands.append((score, abs(days), o["txn_id"], i["txn_id"], sig))
    best_for: dict[str, int] = {}
    count_best: dict[str, int] = {}
    for score, _, oid, iid, _ in cands:
        for t in (oid, iid):
            if score > best_for.get(t, -1):
                best_for[t], count_best[t] = score, 1
            elif score == best_for[t]:
                count_best[t] += 1
    cands.sort(key=lambda c: (-c[0], c[1], c[2], c[3]))
    for score, days, oid, iid, sig in cands:
        if oid in used or iid in used:
            continue
        used.update({oid, iid})
        o, i = by_id[oid], by_id[iid]
        ambiguous = count_best.get(oid, 1) > 1 or count_best.get(iid, 1) > 1
        strong = ("last4" in sig or "own name" in sig) and 0 <= days <= 2
        conf = "high" if strong and not ambiguous else "medium"
        note = "ambiguous: another transaction was an equally good partner - check dates" if ambiguous else ""
        matches.append((o, i, score, sig, conf, note))

    rows = []
    for n, (o, i, score, sig, conf, note) in enumerate(sorted(matches, key=lambda m: (m[0]["date"], m[0]["txn_id"])), 1):
        rows.append({
            "match_id": f"T{n:04d}", "type": pair_type(accounts[o["account_id"]], accounts[i["account_id"]]),
            "out_txn_id": o["txn_id"], "in_txn_id": i["txn_id"], "out_account": o["account_id"],
            "in_account": i["account_id"], "out_date": o["date"], "in_date": i["date"], "amount": -o["_amt"],
            "days_apart": (i["_date"] - o["_date"]).days, "score": score, "signals": " ".join(sig),
            "confidence": conf, "crosses_fy": "Y" if o["fy"] != i["fy"] else "", "note": note,
        })
    write_csv(p("03_data", "transfer_matches.csv"), rows, MATCH_FIELDS)

    # ---- transfer-looking rows left over
    unmatched = []
    for r in tx:
        if r["txn_id"] in used or r["txn_id"] in blocked:
            continue
        hits = [f"names your account {aid}" for aid, rx in l4_rx.items() if aid != r["account_id"] and rx.search(r["_desc"])]
        if any(n in r["_desc"] for n in own_names):
            hits.append("contains your name")
        if hits:
            unmatched.append({"txn_id": r["txn_id"], "date": r["date"], "account_id": r["account_id"],
                              "description_raw": r["description_raw"], "amount": r["_amt"], "why_flagged": "; ".join(hits)})
    write_csv(p("review", "transfers_unmatched.csv"), unmatched,
              ["txn_id", "date", "account_id", "description_raw", "amount", "why_flagged"])

    # ---- checks
    ids = [x for r in rows for x in (r["out_txn_id"], r["in_txn_id"])]
    assert len(ids) == len(set(ids)), "a transaction was used in two pairs"
    for r in rows:
        assert money(by_id[r["out_txn_id"]]["amount"]) + money(by_id[r["in_txn_id"]]["amount"]) == 0
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    print(f"Matched pairs: {len(rows)} (" + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items())) + ")")
    print(f"  medium confidence: {sum(1 for r in rows if r['confidence'] != 'high')}, "
          f"ambiguous: {sum(1 for r in rows if r['note'].startswith('ambiguous'))}, "
          f"crossing 30 June: {sum(1 for r in rows if r['crosses_fy'])}")
    print(f"Transfer-looking rows with no partner: {len(unmatched)} -> review/transfers_unmatched.csv")
    print("Every pair nets to $0.00 and no transaction is used twice: OK")
    print("Next: python scripts/people_candidates.py, then python scripts/classify.py")


if __name__ == "__main__":
    main()
