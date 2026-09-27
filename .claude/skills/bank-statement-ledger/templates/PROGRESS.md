# Progress

**Next step:** 0.2 - fill in `config/accounts.csv` and `notes_for_claude.md`
**Last updated:** (date) by (session)

## Current numbers
- Statements: ? in inventory / ? parsed / ? balance (PASS or SIGNED_OFF)
- Rows: ? · Payees: ? (? without a rule) · Transfer pairs: ? · Review groups open: ?

## Checklist (tick only when the step's check has passed)

### Phase 0 - Set up
- [ ] 0.1 Statements copied into `00_raw/<bank>/<account>/`, folder made read-only
- [ ] 0.2 `config/accounts.csv`, `config/project.json` (own_names!), `notes_for_claude.md` filled in by owner
- [ ] 0.3 Categories reviewed by owner and sent to the accountant for a yes
- [ ] 0.4 `inventory.py` run - no unmapped files, missing statements requested from banks

### Phase 1 - Extract and balance
- [ ] 1.1 A parser for every bank + file type (`parse_all.py` shows no NO_PARSER / ERROR)
- [ ] 1.2 `reconcile.py`: every statement PASS or SIGNED_OFF, no continuity BREAK/GAP
- [ ] 1.3 `combine.py`: rows tie out, duplicates listed, no overlap conflicts

### Phase 2 - Clean and group
- [ ] 2.1 `payees.py`: top 200 payee keys look like real payees; owner spot-checked 30 rows
- [ ] 2.2 `config/clean_names.csv` for the payees that matter

### Phase 3 - Transfers and loans
- [ ] 3.1 `match_transfers.py`: pairs net to zero; owner checked `review/transfers_unmatched.csv`
- [ ] 3.2 `config/people.csv` confirmed by owner

### Phase 4 - Classify
- [ ] 4.1 Rules written for every payee (biggest $ first)
- [ ] 4.2 `classify.py`: owner spot-checked 50 random rows (≤ 2 wrong)
- [ ] 4.3 (optional) receipts found for vague business-looking items

### Phase 5 - Owner review
- [ ] 5.1 Review queue empty except "Ask accountant"

### Phase 6 - Accountant pack
- [ ] 6.1 `build_outputs.py`: checks A-C PASS, every workbook status FINAL
- [ ] 6.2 Accountant-style review done, findings fixed or listed
- [ ] 6.3 Sent to accountant

## Known issues / notes for the next session
-
