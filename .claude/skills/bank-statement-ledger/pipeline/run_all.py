"""Run the pipeline from the balance check to the accountant pack, stopping at the first failure.

  python scripts/run_all.py                 # reconcile -> combine -> payees -> transfers -> people -> classify -> build
  python scripts/run_all.py --allow-partial # build a DRAFT from the statements that balance so far
  python scripts/run_all.py --until classify

If review/review_queue.xlsx holds decisions you have filled in, they are applied first.
Parsing (parse_all.py) is not included: run it when a parser or statement changes.
Every stage prints only a short summary.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from common import p

STAGES = ["reconcile", "combine", "payees", "match_transfers", "people_candidates", "classify", "build_outputs"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--until", choices=STAGES)
    a = ap.parse_args()
    sys.path.insert(0, str(p("scripts")))
    from classify import queue_has_pending_decisions

    stages = list(STAGES)
    if queue_has_pending_decisions():
        stages.insert(0, "apply_review")
    for st in stages:
        args = [sys.executable, str(p("scripts", f"{st}.py"))]
        if st == "combine" and a.allow_partial:
            args.append("--allow-partial")
        print(f"== {st}")
        sys.stdout.flush()
        code = subprocess.call(args, cwd=p())
        if code != 0 and not (st == "reconcile" and a.allow_partial):
            print(f"Stopped at {st} (exit {code}).")
            sys.exit(code)
        if st == a.until:
            break
    print("== done")


if __name__ == "__main__":
    main()
