"""Phase 1.3 - combine balanced statements into one transaction file.

  python scripts/combine.py                 # refuses if any included statement is not PASS/SIGNED_OFF
  python scripts/combine.py --allow-partial # use only the balanced ones; outputs are marked DRAFT

Only statements that balance are used (the accuracy rule). When two statements for
the same account cover the same days (e.g. a CSV export and the PDF statement), the
lower-priority one's rows in the shared window are matched one-to-one against the
higher-priority one (same amount, date within 3 days) and removed as duplicates.
Every removal is listed; a row that exists in only one of the two sources stops the
run, because one of them is incomplete and silently picking one would lose money.

Writes: 03_data/transactions.csv    txn_id (S037-0042 = statement 37, row 42), fy, ...
        03_data/control_totals.csv  rows and net per account per FY (build_outputs ties back to this)
        03_data/combine_log.json    statements used / excluded
        review/duplicates_removed.csv, review/overlap_conflicts.csv
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from decimal import Decimal

from common import fy_of, load_project, p, read_csv, read_statement, write_csv

TXN_FIELDS = ["txn_id", "fy", "date", "account_id", "statement_id", "seq", "source_file",
              "source_page", "source_line", "description_raw", "amount", "balance_shown"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-partial", action="store_true")
    a = ap.parse_args()
    cfg = load_project()
    fsm = int(cfg["fy_start_month"])

    inv = {r["statement_id"]: r for r in read_csv(p("config", "inventory.csv"), required=True)
           if r["include"].upper() == "Y"}
    rec = {r["statement_id"]: r for r in read_csv(p("output", "reconciliation.csv"), required=True)}
    good = [sid for sid in inv if rec.get(sid, {}).get("status") in {"PASS", "SIGNED_OFF"}]
    bad = sorted(set(inv) - set(good))
    if bad and not a.allow_partial:
        print(f"FAIL: {len(bad)} included statements do not balance yet: {', '.join(bad[:15])}")
        print("Fix them (reconcile.py), set include=N in config/inventory.csv, or run with --allow-partial for a DRAFT.")
        sys.exit(1)

    stmts = {}
    for sid in good:
        meta, rows = read_statement(sid)
        stmts[sid] = (meta, rows, int(inv[sid].get("priority") or 9))

    # ---- duplicate sources for the same account and days
    removed, conflicts, drop = [], [], set()
    by_acct: dict[str, list] = {}
    for sid, (meta, _, prio) in stmts.items():
        by_acct.setdefault(meta["account_id"], []).append(sid)
    for acct, sids in by_acct.items():
        sids.sort(key=lambda s: (stmts[s][2], stmts[s][0]["period_start"], s))
        for i, low in enumerate(sids):
            for high in sids[:i]:
                lm, lrows, _ = stmts[low]
                hm, hrows, _ = stmts[high]
                w0 = max(lm["period_start"], hm["period_start"])
                w1 = min(lm["period_end"], hm["period_end"])
                if w0 > w1:
                    continue
                slack = dt.timedelta(days=3)
                lwin = [r for r in lrows if w0 <= r["date"] <= w1 and (low, r["seq"]) not in drop]
                hwin = [r for r in hrows if w0 - slack <= r["date"] <= w1 + slack]
                used = set()
                for r in lwin:
                    best = None
                    for h in hwin:
                        if h["seq"] in used or h["amount"] != r["amount"]:
                            continue
                        gap = abs((h["date"] - r["date"]).days)
                        if gap <= 3 and (best is None or gap < best[0]):
                            best = (gap, h)
                    if best:
                        used.add(best[1]["seq"])
                        drop.add((low, r["seq"]))
                        removed.append({"removed_txn": f"{low}-{r['seq']:04d}", "kept_txn": f"{high}-{best[1]['seq']:04d}",
                                        "account_id": acct, "date": r["date"], "amount": r["amount"],
                                        "removed_description": r["description_raw"],
                                        "kept_description": best[1]["description_raw"]})
                    else:
                        conflicts.append({"statement_id": low, "seq": r["seq"], "other_statement": high,
                                          "date": r["date"], "amount": r["amount"],
                                          "description_raw": r["description_raw"],
                                          "problem": f"in {low} but not in higher-priority {high}"})
                for h in hwin:
                    if w0 <= h["date"] <= w1 and h["seq"] not in used:
                        conflicts.append({"statement_id": high, "seq": h["seq"], "other_statement": low,
                                          "date": h["date"], "amount": h["amount"],
                                          "description_raw": h["description_raw"],
                                          "problem": f"in {high} but not in overlapping {low}"})
    write_csv(p("review", "duplicates_removed.csv"), removed,
              ["removed_txn", "kept_txn", "account_id", "date", "amount", "removed_description", "kept_description"])
    write_csv(p("review", "overlap_conflicts.csv"), conflicts,
              ["statement_id", "seq", "other_statement", "date", "amount", "description_raw", "problem"])
    if conflicts:
        print(f"FAIL: {len(conflicts)} rows appear in only one of two overlapping statements (review/overlap_conflicts.csv).")
        print("Usually one source is a partial export: set include=N for it in config/inventory.csv, or fix its parser.")
        sys.exit(1)

    # ---- combine
    out, totals = [], {}
    rows_in = 0
    for sid, (meta, rows, _) in sorted(stmts.items()):
        rows_in += len(rows)
        for r in rows:
            if (sid, r["seq"]) in drop:
                continue
            fy = fy_of(r["date"], fsm)
            out.append({**r, "txn_id": f"{sid}-{r['seq']:04d}", "fy": fy})
            key = (r["account_id"], fy)
            t = totals.setdefault(key, {"account_id": key[0], "fy": fy, "rows": 0, "net": Decimal("0.00")})
            t["rows"] += 1
            t["net"] += r["amount"]
    out.sort(key=lambda r: (r["account_id"], r["date"], r["statement_id"], r["seq"]))
    write_csv(p("03_data", "transactions.csv"), out, TXN_FIELDS)
    write_csv(p("03_data", "control_totals.csv"), sorted(totals.values(), key=lambda t: (t["account_id"], t["fy"])),
              ["account_id", "fy", "rows", "net"])
    p("03_data", "combine_log.json").write_text(json.dumps(
        {"used": sorted(stmts), "excluded_not_balanced": bad, "partial": bool(bad)}, indent=2), encoding="utf-8")

    assert len(out) == rows_in - len(removed), "row count does not tie out"
    print(f"Rows: {rows_in} extracted - {len(removed)} duplicates = {len(out)} in 03_data/transactions.csv")
    fys = sorted({r["fy"] for r in out})
    print(f"Accounts: {len({r['account_id'] for r in out})}, financial years: {', '.join(fys)}")
    if bad:
        print(f"DRAFT: {len(bad)} unbalanced statements excluded: {', '.join(bad[:10])}")
    print("Next: python scripts/payees.py")


if __name__ == "__main__":
    main()
