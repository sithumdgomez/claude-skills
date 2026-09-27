"""Phase 1.2 - prove every statement was extracted correctly.

  python scripts/reconcile.py

Four tests per statement:
  1. opening balance + all rows = closing balance, to the cent
  2. row by row: previous balance + amount = the balance printed on that row
     (points at the exact bad row - usually a debit read as a credit)
  3. continuity: this statement's opening = the previous statement's closing
     (catches a missing statement)
  4. no transaction dated outside the statement period (catches day/month swaps
     and wrong years)
Writes: output/reconciliation.csv      one row per statement, status PASS/FAIL/UNVERIFIED/SIGNED_OFF
        review/reconcile_row_errors.csv  the exact rows that break the running balance
        output/coverage.csv            account x month grid from the parsed periods
Optional inputs you (not Claude) fill in:
        config/balance_anchors.csv  statement_id,opening_balance,closing_balance,source_note
            for CSV exports with no balance column (copy the figures from the PDF)
        config/signoffs.csv         statement_id,reason,signed_off_by,signed_off_on
            only for a genuine bank-side oddity you have checked yourself
Exit code 1 while anything is not PASS/SIGNED_OFF - later steps refuse to run on it.
"""
from __future__ import annotations

import datetime as dt
import sys
from decimal import Decimal

from common import (fy_bounds, fmt_money, load_accounts, load_project, money, month_keys, p,
                    read_csv, read_statement, write_csv)

REC_FIELDS = ["statement_id", "account_id", "source_file", "period_start", "period_end", "rows",
              "opening_balance", "total_in", "total_out", "computed_closing", "stated_closing",
              "difference", "row_errors", "dates_outside_period", "out_of_order_dates",
              "balance_source", "continuity", "status", "note"]
ERR_FIELDS = ["statement_id", "seq", "source_page", "source_line", "date", "description_raw",
              "amount", "expected_balance", "shown_balance", "difference"]


def main():
    cfg = load_project()
    tol = dt.timedelta(days=int(cfg["date_tolerance_days"]))
    accounts = load_accounts()
    inv = [r for r in read_csv(p("config", "inventory.csv"), required=True) if r["include"].upper() == "Y"]
    anchors = {r["statement_id"]: r for r in read_csv(p("config", "balance_anchors.csv"))}
    signoffs = {r["statement_id"]: r for r in read_csv(p("config", "signoffs.csv"))}

    results, row_errors, parsed = [], [], {}
    for inv_row in inv:
        sid = inv_row["statement_id"]
        res = {"statement_id": sid, "account_id": inv_row["account_id"], "source_file": inv_row["statement_file"]}
        try:
            meta, rows = read_statement(sid)
        except FileNotFoundError:
            res.update(status="FAIL", note="not parsed - run parse_all.py / write the parser")
            results.append(res)
            continue
        opening, closing = meta.get("opening_balance"), meta.get("closing_balance")
        source = meta.get("balance_source", "statement")
        if sid in anchors:
            opening = money(anchors[sid]["opening_balance"])
            closing = money(anchors[sid]["closing_balance"])
            source = "anchor: " + anchors[sid].get("source_note", "")
        total_in = sum((r["amount"] for r in rows if r["amount"] > 0), Decimal("0.00"))
        total_out = sum((r["amount"] for r in rows if r["amount"] < 0), Decimal("0.00"))
        ps, pe = meta["period_start"], meta["period_end"]
        outside = [r for r in rows if r["date"] < ps - tol or r["date"] > pe + tol]
        out_of_order = sum(1 for a, b in zip(rows, rows[1:]) if b["date"] < a["date"])

        n_err = 0
        if opening is not None:
            running = opening
            for r in rows:
                running += r["amount"]
                shown = r["balance_shown"]
                if shown is not None and shown != running:
                    n_err += 1
                    row_errors.append({**r, "expected_balance": running, "shown_balance": shown,
                                       "difference": shown - running})
                    running = shown  # re-sync so one bad row is reported once, not on every later row
        computed = opening + total_in + total_out if opening is not None else None
        diff = (closing - computed) if (closing is not None and computed is not None) else None

        if opening is None or closing is None:
            status, note = "UNVERIFIED", "no opening/closing balance - add it to config/balance_anchors.csv from the PDF"
        elif diff != 0 or n_err or outside:
            status = "FAIL"
            bits = []
            if diff != 0:
                bits.append(f"out by {fmt_money(diff)}")
            if n_err:
                bits.append(f"{n_err} running-balance errors (review/reconcile_row_errors.csv)")
            if outside:
                bits.append(f"{len(outside)} dates outside period (day/month swap or wrong year?)")
            note = "; ".join(bits)
        else:
            status, note = "PASS", ""
        if status != "PASS" and sid in signoffs:
            note = f"SIGNED OFF ({signoffs[sid].get('reason', '')}) - was: {status} {note}"
            status = "SIGNED_OFF"
        if not rows:
            note = (note + "; " if note else "") + "no transactions in this statement"
        res.update(period_start=ps, period_end=pe, rows=len(rows), opening_balance=opening,
                   total_in=total_in, total_out=total_out, computed_closing=computed,
                   stated_closing=closing, difference=diff, row_errors=n_err,
                   dates_outside_period=len(outside), out_of_order_dates=out_of_order,
                   balance_source=source, status=status, note=note)
        results.append(res)
        parsed[sid] = (inv_row, res)

    # ---- continuity along each account's chain of statements
    breaks = 0
    by_acct: dict[str, list] = {}
    for sid, (inv_row, res) in parsed.items():
        by_acct.setdefault(res["account_id"], []).append((res["period_start"], int(inv_row.get("priority") or 9), sid, res))
    for acct, items in by_acct.items():
        items.sort(key=lambda t: (t[0], t[1]))
        prev = None
        for _, _, sid, res in items:
            if prev is None:
                res["continuity"] = "FIRST"
                prev = res
                continue
            if res["period_end"] <= prev["period_end"] and res["period_start"] >= prev["period_start"]:
                res["continuity"] = f"OVERLAP (inside {prev['statement_id']} - duplicate source?)"
                continue
            po, pc = res.get("opening_balance"), prev.get("stated_closing")
            if po is not None and pc is not None:
                if po == pc:
                    res["continuity"] = "OK"
                else:
                    res["continuity"] = f"BREAK: opening {fmt_money(po)} vs previous closing {fmt_money(pc)} ({prev['statement_id']})"
                    breaks += 1
            else:
                gap = (res["period_start"] - prev["period_end"]).days - 1
                res["continuity"] = f"GAP {gap} days after {prev['statement_id']}" if gap > int(cfg["date_tolerance_days"]) else "OK (dates)"
                breaks += 1 if gap > int(cfg["date_tolerance_days"]) else 0
            prev = res

    results.sort(key=lambda r: r["statement_id"])
    write_csv(p("output", "reconciliation.csv"), results, REC_FIELDS)
    write_csv(p("review", "reconcile_row_errors.csv"), row_errors, ERR_FIELDS)

    # ---- coverage grid from the real (parsed) periods
    start_all, _ = fy_bounds(cfg["first_fy"], cfg["fy_start_month"])
    _, end_all = fy_bounds(cfg["last_fy"], cfg["fy_start_month"])
    months = month_keys(start_all, end_all)
    grid, missing = [], 0
    for aid, acct in accounts.items():
        line = {"account_id": aid}
        for mk in months:
            if (acct.get("opened") and mk < acct["opened"][:7]) or (acct.get("closed") and mk > acct["closed"][:7]):
                line[mk] = "-"
                continue
            ids = [r["statement_id"] for r in results if r["account_id"] == aid and r.get("period_start")
                   and r["period_start"].isoformat()[:7] <= mk <= r["period_end"].isoformat()[:7]]
            line[mk] = " ".join(ids) if ids else "MISSING"
            missing += 0 if ids else 1
        grid.append(line)
    write_csv(p("output", "coverage.csv"), grid, ["account_id"] + months)

    # ---- summary
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("Statements: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" (of {len(results)})")
    for r in results:
        if r["status"] not in {"PASS", "SIGNED_OFF"}:
            print(f"  {r['statement_id']} {r['status']}: {r.get('note', '')}")
    for r in results:
        c = str(r.get("continuity", ""))
        if c.startswith(("BREAK", "GAP")):
            print(f"  {r['statement_id']} continuity {c}")
    print(f"Account-months with no statement: {missing} (output/coverage.csv)")
    ok = all(r["status"] in {"PASS", "SIGNED_OFF"} for r in results) and breaks == 0
    print("ALL STATEMENTS BALANCE" if ok else "NOT READY: fix the items above before combine.py")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
