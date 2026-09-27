# Paste-ready prompts

Each prompt is one session. Start the session from the project folder with the model and
effort shown. After the first session, every session starts the same way:
**"Read PROGRESS.md and do the next step."** The prompts below are for when you want to be
explicit.

---

## Before Session 1 (owner, about 30 minutes, no Claude)
1. `pip install pdfplumber openpyxl`
2. `python <skill>/tools/init_project.py ~/bookkeeping`. Use a local folder, not inside any
   repo or synced folder.
3. Copy the statements into `00_raw/<bank>/<account>/`, then run `chmod -R a-w 00_raw`.
4. Fill in `config/accounts.csv`, `own_names` in `config/project.json`, and
   `notes_for_claude.md`.
5. Optional: download CSV exports from each bank as far back as they allow.

## Session 1: design and inventory (`claude --model opus --effort high`)
```
Use the bank-statement-ledger skill. This project turns my bank statements into
accountant-ready ledgers. Read CLAUDE.md, config/accounts.csv, config/project.json
and notes_for_claude.md. Do not open anything in 00_raw/ or 01_statements/.

This session only:
1. Fill in the "Project facts" section of CLAUDE.md from my notes.
2. Tailor config/categories.csv to my business (add what it needs, remove what it
   clearly doesn't; keep the ATO labels exact). Show me the list as a table.
3. Tell me anything missing from my notes that would change the plan.
Then update PROGRESS.md and stop.
```
Before the next session: approve the category list, and email it with the ledger columns
(`reference/ledger-schema.md`) to the accountant.

## Session 2: inventory (`claude --model sonnet --effort medium`)
```
Read PROGRESS.md. Run python scripts/inventory.py and show me only the summary:
unmapped files, scans, duplicates and missing months. List the statements I need to
request from each bank. Update PROGRESS.md.
```

## Sessions 3–4: parsers (`claude --model sonnet --effort medium`)
```
Read PROGRESS.md. Write the parsers for every bank in config/accounts.csv. Use one
bank-parser subagent per bank, in parallel. Each works from dump_sample.py output only
and stops when every statement for its bank passes reconcile.py or it has failed
twice on one statement. Then run parse_all.py and reconcile.py and give me the
PASS/FAIL table. List anything that needs a balance anchor or my sign-off. Update
PROGRESS.md.
```
If a statement still fails after two attempts, run a new session with `--model opus --effort high`:
```
Read PROGRESS.md. Statement S0xx fails reconcile.py. Read its rows in
review/reconcile_row_errors.csv, dump the failing page with --words, and fix the
parser. Do not edit any amounts or extracted files by hand.
```

## Session 5: combine, payees, transfers, people (`claude --model sonnet --effort medium`)
```
Read PROGRESS.md. Run combine.py, payees.py, match_transfers.py and
people_candidates.py. Report each summary. Then:
- propose config/normalise.csv rows if the top payee keys still carry noise, and re-run payees.py
- draft config/people.csv from review/people_candidates.csv (group name variants;
  leave treatment "Ask me" where you can't tell) and show it to me for confirmation
- list review/transfers_unmatched.csv grouped by likely cause
Update PROGRESS.md.
```
Clean names can be done with `--model haiku --effort low`: "Write config/clean_names.csv
for the top 300 payees in 03_data/payees.csv."

## Session 6: payee rules (`claude --model sonnet --effort medium`)
```
Read PROGRESS.md. Write rules in config/rules.csv for payees.csv rows with status
"new", biggest abs_total first, 150 at a time (read with offset/limit). Use only
config/categories.csv categories; decide business vs personal by what the payee is,
using notes_for_claude.md and DECISIONS.md. confidence high only when any bookkeeper
would agree from the name. After each batch run classify.py and report its summary
and review/rule_conflicts.csv. Update PROGRESS.md with how far you got.
```

## Owner review (no Claude)
Open `review/review_queue.xlsx` and fill in the yellow columns. Save, then run
`python scripts/apply_review.py` and `python scripts/run_all.py`. Repeat until the queue
holds only Ask accountant items.

## Session 7: pack and final review (`claude --model opus --effort high`)
```
Read PROGRESS.md. Run run_all.py and report the checks and each workbook's README
status. Then review the pack as my accountant would, reading only the README,
Business P&L, Personal, Loans, Internal transfers and Open questions tabs (not the
Ledger tab). Look for year-on-year jumps, large one-offs, loans that look like
income, business income in personal accounts, and expected items that are missing.
Write review/qa_findings.md. For each finding, propose a rule or decision change or
an Ask-accountant note. Update PROGRESS.md.
```

## Adding a year later (`claude --model sonnet --effort medium`)
```
Use the bank-statement-ledger skill. I've added FY20xx statements to 00_raw/ and set
last_fy in config/project.json. Follow "Adding a year": inventory, parse the new
statements only, reconcile, run_all, and write rules only for payees with status
"new". Update PROGRESS.md.
```
