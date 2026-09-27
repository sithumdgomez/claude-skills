"""Loading and matching rules (config/rules.csv) and people (config/people.csv).

Shared by payees.py (to mark payees that already have a rule) and classify.py.

rules.csv columns
  rule_id            R0001 ... (never reuse an id - ledger rows point at it)
  match_type         exact | contains | startswith | regex   (tested against payee_key)
  pattern            e.g. WOOLWORTHS
  direction          in | out | any   (money in / money out)
  account_scope      any | business | personal | <account_id>
  type               one of the types in common.TYPES
  category           from config/categories.csv (required for income/expense/refund types)
  business_personal  Business | Personal | Mixed | account  ("account" = the account's default use)
  business_pct       0-100, required when Mixed (a starting figure; the accountant confirms)
  confidence         high | medium | low   (anything but high goes to the review list)
  reason             one line: why this rule is right
Order: exact rules win; then the others in file order, first match wins.

people.csv columns
  person, match_type, pattern, relationship (friend|family|customer|supplier|other),
  treatment (Loan | Gift or shared bill | Business customer | Business supplier | Ask me), note
"""
from __future__ import annotations

import re
from pathlib import Path

from common import BP_VALUES, TYPES, load_accounts, p, read_csv

RULE_FIELDS = ["rule_id", "match_type", "pattern", "direction", "account_scope", "type", "category",
               "business_personal", "business_pct", "confidence", "reason"]
PEOPLE_FIELDS = ["person", "match_type", "pattern", "relationship", "treatment", "note"]
TREATMENTS = {"Loan", "Gift or shared bill", "Business customer", "Business supplier", "Ask me"}


def _tester(match_type: str, pattern: str):
    pat = pattern.upper()
    if match_type == "exact":
        return lambda k: k == pat
    if match_type == "contains":
        return lambda k: pat in k
    if match_type == "startswith":
        return lambda k: k.startswith(pat)
    if match_type == "regex":
        rx = re.compile(pattern, re.I)
        return lambda k: bool(rx.search(k))
    raise ValueError(f"unknown match_type {match_type!r}")


class RuleBook:
    def __init__(self, rules: list[dict], accounts: dict):
        self.accounts = accounts
        self.exact: dict[str, list[dict]] = {}
        self.others: list[dict] = []
        self.errors: list[str] = []
        seen = set()
        for r in rules:
            rid = r.get("rule_id", "")
            if not rid or not r.get("pattern"):
                continue
            if rid in seen:
                self.errors.append(f"{rid}: duplicate rule_id")
            seen.add(rid)
            mt = (r.get("match_type") or "contains").lower()
            r["match_type"] = mt
            r["direction"] = (r.get("direction") or "any").lower()
            r["account_scope"] = r.get("account_scope") or "any"
            r["confidence"] = (r.get("confidence") or "low").lower()
            if r.get("type") not in TYPES:
                self.errors.append(f"{rid}: type {r.get('type')!r} is not one of the allowed types")
            if r["direction"] not in {"in", "out", "any"}:
                self.errors.append(f"{rid}: direction must be in/out/any")
            if r["confidence"] not in {"high", "medium", "low"}:
                self.errors.append(f"{rid}: confidence must be high/medium/low")
            bp = r.get("business_personal", "")
            if bp and bp not in BP_VALUES + ["account"]:
                self.errors.append(f"{rid}: business_personal must be Business/Personal/Mixed/account")
            if bp == "Mixed" and not (r.get("business_pct") or "").replace(".", "", 1).isdigit():
                self.errors.append(f"{rid}: Mixed needs a business_pct")
            try:
                r["_test"] = _tester(mt, r["pattern"])
            except (ValueError, re.error) as e:
                self.errors.append(f"{rid}: {e}")
                continue
            if mt == "exact":
                self.exact.setdefault(r["pattern"].upper(), []).append(r)
            else:
                self.others.append(r)

    @classmethod
    def load(cls, path: Path | None = None) -> "RuleBook":
        return cls(read_csv(path or p("config", "rules.csv")), load_accounts())

    def _scope_ok(self, r: dict, amount, account_id: str) -> bool:
        d = r["direction"]
        if (d == "in" and amount <= 0) or (d == "out" and amount >= 0):
            return False
        sc = r["account_scope"]
        if sc in {"", "any"}:
            return True
        if sc in {"business", "personal"}:
            return self.accounts.get(account_id, {}).get("default_use") == sc
        return sc == account_id

    def match(self, key: str, amount, account_id: str) -> dict | None:
        for r in self.exact.get(key, []):
            if self._scope_ok(r, amount, account_id):
                return r
        for r in self.others:
            if r["_test"](key) and self._scope_ok(r, amount, account_id):
                return r
        return None


class PeopleBook:
    def __init__(self, rows: list[dict]):
        self.rows, self.errors = [], []
        for r in rows:
            if not r.get("person") or not r.get("pattern"):
                continue
            r["match_type"] = (r.get("match_type") or "contains").lower()
            if r.get("treatment") not in TREATMENTS:
                self.errors.append(f"people.csv {r['person']}: treatment must be one of {sorted(TREATMENTS)}")
            try:
                r["_test"] = _tester(r["match_type"], r["pattern"])
            except (ValueError, re.error) as e:
                self.errors.append(f"people.csv {r['person']}: {e}")
                continue
            self.rows.append(r)

    @classmethod
    def load(cls) -> "PeopleBook":
        return cls(read_csv(p("config", "people.csv")))

    def match(self, key: str) -> dict | None:
        for r in self.rows:
            if r["_test"](key):
                return r
        return None
