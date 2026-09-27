"""Phase 1.1 - run the bank parsers over every included statement.

  python scripts/parse_all.py                  # everything with include=Y
  python scripts/parse_all.py --only S004 S009 # just these
  python scripts/parse_all.py --account BANKA-BUS-1234

Picks the parser by convention: scripts/parsers/<parser_prefix>_<pdf|csv>.py, where
parser_prefix comes from config/accounts.csv (default: the bank name, lower-case,
letters and digits only). Writes 02_extracted/<id>.csv + <id>.meta.json and
output/parse_log.csv. A statement whose parser fails has its old extract deleted,
so stale data can never flow into later steps.
Next step: python scripts/reconcile.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import sys
import traceback
from decimal import Decimal

from common import load_accounts, p, read_csv, slug, write_csv, write_statement, iso

LOG_FIELDS = ["statement_id", "account_id", "file_type", "parser", "status", "rows",
              "period_start", "period_end", "opening_balance", "closing_balance", "balance_source", "message"]


def _where(exc: BaseException) -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    frames = [f for f in tb if "parsers" in f.filename] or tb
    f = frames[-1]
    return f"{f.filename.split('/')[-1]}:{f.lineno}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--account")
    a = ap.parse_args()

    sys.path.insert(0, str(p("scripts")))
    accounts = load_accounts()
    inv = read_csv(p("config", "inventory.csv"), required=True)
    todo = [r for r in inv if r["include"].upper() == "Y"
            and (not a.only or r["statement_id"] in a.only)
            and (not a.account or r["account_id"] == a.account)]

    old_log = {r["statement_id"]: r for r in read_csv(p("output", "parse_log.csv"))}
    log = []
    for r in todo:
        sid, acct = r["statement_id"], accounts[r["account_id"]]
        prefix = acct.get("parser_prefix") or slug(acct["bank"])
        modname = f"{prefix}_{r['file_type']}"
        entry = {"statement_id": sid, "account_id": r["account_id"], "file_type": r["file_type"], "parser": modname}
        ctx = {
            "statement_id": sid, "account_id": r["account_id"], "source_file": r["statement_file"],
            "period_hint": (iso(r["period_start_guess"]) if r["period_start_guess"] else None,
                            iso(r["period_end_guess"]) if r["period_end_guess"] else None),
        }
        for stale in (p("02_extracted", f"{sid}.csv"), p("02_extracted", f"{sid}.meta.json")):
            stale.unlink(missing_ok=True)
        try:
            mod = importlib.import_module(f"parsers.{modname}")
        except ModuleNotFoundError as e:
            if e.name and e.name.endswith(modname):
                log.append({**entry, "status": "NO_PARSER", "message": f"write scripts/parsers/{modname}.py"})
                continue
            raise
        try:
            meta, rows = mod.parse(p("01_statements", r["statement_file"]), ctx)
            for k in ("period_start", "period_end"):
                if not isinstance(meta.get(k), dt.date):
                    raise ValueError(f"parser returned no {k}")
            for k in ("opening_balance", "closing_balance"):
                if meta.get(k) is not None and not isinstance(meta[k], Decimal):
                    raise TypeError(f"{k} must be Decimal")
            meta = {"statement_id": sid, "account_id": r["account_id"], "source_file": r["statement_file"],
                    "parser": modname, "balance_source": "statement", **meta}
            write_statement(meta, rows)
            log.append({**entry, "status": "OK", "rows": len(rows),
                        "period_start": meta["period_start"], "period_end": meta["period_end"],
                        "opening_balance": meta.get("opening_balance"),
                        "closing_balance": meta.get("closing_balance"),
                        "balance_source": meta["balance_source"]})
        except Exception as e:  # report every failure, keep going with the rest
            log.append({**entry, "status": "ERROR", "message": f"{type(e).__name__}: {e} ({_where(e)})"[:300]})

    done = {e["statement_id"] for e in log}
    merged = [e for sid, e in old_log.items() if sid not in done] + log
    merged.sort(key=lambda e: e["statement_id"])
    write_csv(p("output", "parse_log.csv"), merged, LOG_FIELDS)

    ok = sum(1 for e in log if e["status"] == "OK")
    print(f"Parsed {ok}/{len(log)} statements ({sum(int(e.get('rows') or 0) for e in log)} rows)")
    bad = [e for e in log if e["status"] != "OK"]
    for e in bad[:20]:
        print(f"  {e['statement_id']} {e['status']}: {e.get('message', '')}")
    if len(bad) > 20:
        print(f"  ... {len(bad) - 20} more in output/parse_log.csv")
    print("Next: python scripts/reconcile.py")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
