# Phases in detail

Each step lists who does it, what goes in and comes out, the tool and model, and **the check
that must pass before moving on**. Tick the step in the project's `PROGRESS.md` only when its
check passes.

Effort is set in Claude Code with `claude --model sonnet --effort medium` (levels: low,
medium, high, xhigh, max) or with `/model` inside a session. In the Claude.ai app, the nearest
equivalent is turning extended thinking on or off. xhigh and max are not needed anywhere
in this job.

---

## Phase 0: Set up (1 session)

### 0.1 Collect the files (owner)
- **Do:** create the project with `tools/init_project.py`. Copy every statement into
  `00_raw/<bank>/<account>/` and make the folder read-only (`chmod -R a-w 00_raw`).
  Optional: where a bank's CSV export reaches back far enough, download CSVs too. They
  extract more cleanly, and `combine.py` removes the overlap with the PDFs.
- **Out:** `00_raw/`
- **Check:** the file count matches what the owner expects.

### 0.2 Accounts and facts (owner, about 15 minutes)
- **Do:**
  - Fill in `config/accounts.csv`, one row per account (format in `ledger-schema.md`).
  - Put the owner's names as they appear on transfers into `own_names` in
    `config/project.json`, e.g. `["J CITIZEN", "JANE CITIZEN"]`.
  - Answer `notes_for_claude.md`.
- **Why it matters:** Claude can't guess these, and transfer matching depends on them.
- **Check:** every folder in `00_raw/` is some account's `raw_folder`.

### 0.3 Rules and categories (Claude · Opus · high)
- **Do:**
  - Adapt the project `CLAUDE.md` with the owner's facts.
  - Tailor `config/categories.csv` to the business described in `notes_for_claude.md`: add
    categories the business needs and remove ones it clearly doesn't. Never rename the ATO
    labels.
  - Put a GST note in `config/project.json` if it applies.
- **Out:** `CLAUDE.md`, `config/categories.csv`, `PROGRESS.md` updated.
- **Check:** the owner approves the category list, then **emails it to the accountant with
  the ledger column list** (`ledger-schema.md`) and gets a yes. This five-minute email
  prevents the most expensive rework there is: re-categorising everything later.

### 0.4 Inventory (script: `inventory.py`)
- **Out:**
  - `config/inventory.csv` (statement IDs, masked names, pages, text layer, a guess at the
    period, include/priority)
  - `01_statements/` (renamed copies)
  - `review/coverage_guess.csv`
- **Check:**
  - No unmapped files.
  - Scans (text_layer N) have been replaced with e-statements or CSVs.
  - Missing months have been **requested from the bank now**; they take days to arrive.

---

## Phase 1: Extract and balance (2–3 sessions)

### 1.1 One parser per bank and file type (Claude · Sonnet · medium)
- **Do:** see "Phase 1: writing a bank parser" in SKILL.md. For more than one bank, run one
  `bank-parser` subagent per bank in parallel.
- **In:** the masked samples from `dump_sample.py`, and the worked examples in
  `scripts/parsers/`.
- **Out:** `scripts/parsers/<prefix>_pdf.py` / `_csv.py`, and `02_extracted/S0xx.csv` plus
  `.meta.json`.
- **Check:** `parse_all.py` shows no NO_PARSER and no ERROR.

### 1.2 Balance every statement (script: `reconcile.py`)
- **Tests:**
  1. Opening + rows = closing.
  2. Running balance row by row.
  3. Continuity with the previous statement.
  4. No dates outside the period.
- **Out:** `output/reconciliation.csv`, `review/reconcile_row_errors.csv`, `output/coverage.csv`.
- **Fixing failures:** Claude fixes the parser (Sonnet, then Opus · high after 2 failed
  tries).
  - A CSV with no balances needs `config/balance_anchors.csv` (the owner copies the figures
    from the PDF).
  - A genuine bank error needs the owner's line in `config/signoffs.csv`.
- **Check:** every included statement PASS or SIGNED_OFF, no BREAK or GAP, and MISSING months
  explained (the account opened later, or it's closed).

### 1.3 Combine (script: `combine.py`)
- **Out:**
  - `03_data/transactions.csv` (permanent `txn_id`, `fy`)
  - `03_data/control_totals.csv`
  - `review/duplicates_removed.csv`
  - `review/overlap_conflicts.csv`
- **Check:** rows in = rows extracted − duplicates (the script asserts it), and there are no
  overlap conflicts.

---

## Phase 2: Clean and group (1 session)

### 2.1 Payee keys (script: `payees.py`)
- **Out:**
  - `03_data/transactions_keyed.csv`
  - `03_data/payees.csv`: one row per payee_key, biggest dollar value first, with a `stem`
    and a `status` (ruled / own-transfer / person / new)
- **Tuning:** if the keys still carry noise (store numbers, references), Claude adds regex
  rows to `config/normalise.csv` (Sonnet · low) and re-runs. The script itself isn't edited.
- **Check:** the top 200 keys by value read like real payees, and the owner spot-checks 30
  random rows (raw description → key).

### 2.2 Clean names (Claude · Haiku · low, batches)
- **Out:** `config/clean_names.csv` (payee_key → readable name) for the payees that matter.
  Long-tail payees can keep the automatic title-case.
- **Check:** every key appears at most once, and the owner skims 50.

---

## Phase 3: Transfers and loans (1–2 sessions)

### 3.1 Match internal transfers (script: `match_transfers.py`)
- **Out:** `03_data/transfer_matches.csv` and `review/transfers_unmatched.csv`.
- **The owner reviews the unmatched list.** Usually it's one of:
  - an account missing from the set: add its statements, or type Outside account
  - a coincidence: a txn decision with the right type
  - a pair the script missed: `config/manual_matches.csv`
- **Check:**
  - Every pair nets to $0.00 and no transaction is used twice (both asserted by the script).
  - Crossing-FY pairs are listed.
  - The owner has seen the unmatched list.

### 3.2 People (script: `people_candidates.py`, then Claude · Haiku · low, then owner)
- **Out:** `review/people_candidates.csv`. Claude drafts `config/people.csv` by grouping name
  variants, and the owner confirms each person's relationship and treatment.
- **Treatments:**
  - **Loan:** money out is Loan out and money in is Loan in. The running net shows who owes
    whom, so nobody has to decide on every $20 whether it was a new loan or a repayment.
  - **Gift or shared bill**
  - **Business customer**
  - **Business supplier**
  - **Ask me**
- **Check:** every candidate with money above the owner's threshold is either mapped or
  consciously left for review.

---

## Phase 4: Classify (1–2 sessions)

### 4.1 Payee rules (Claude · Sonnet · medium; low for obvious shops)
- **In:** `payees.csv` rows with status `new` (read with offset/limit, about 150 at a time),
  `categories.csv`, `DECISIONS.md`, `notes_for_claude.md`.
- **Out:** rows appended to `config/rules.csv` (format in `ledger-schema.md`).
- **Check:** `classify.py` reports no rule errors, and `review/rule_conflicts.csv` has been
  looked at.

### 4.2 Apply (script: `classify.py`)
- **Out:** `03_data/classified.csv` and `review/review_queue.xlsx`.
- **Check:** the owner spot-checks 50 random rows. If more than 2 are wrong, fix the **rules**
  (not the rows) and re-run.

### 4.3 Optional: evidence for vague business-looking items (Claude · Sonnet · medium)
- **Do:** for Unknown or medium items over about $50 where business use is possible, search
  the owner's email (if a mail connector is available) for a receipt or invoice: the same
  amount, within 3 days of the date. If invoices go out through an accounting tool, match
  incoming payments to invoices; it's the strongest proof of business income.
- **Out:** the evidence goes in the review decision's note. The amount never changes.

---

## Phase 5: Owner review (no Claude needed)

### 5.1 `review/review_queue.xlsx`
- **How it's laid out:**
  - **Groups sheet:** one line per payee or person, biggest money first, with dropdowns.
    Pick a type, category and business/personal. Use `decide_person` to name a friend, and
    `decide_ask_accountant` = Y when unsure.
  - **Transactions sheet:** single-row exceptions, which win over the group.
- **Then:** run `apply_review.py`, which writes `config/decisions.csv` and archives the
  sheet, then `run_all.py`. Repeat until the queue is empty except Ask accountant items.
- **Check:** `classify.py` shows 0 Needs review.

---

## Phase 6: Accountant pack (1–2 sessions)

### 6.1 Build (script: `build_outputs.py`)
- **Out:** `output/master_ledger.csv` and `output/FY20xx.xlsx`, with these tabs:
  - README
  - Ledger
  - Business P&L
  - Mixed use
  - Personal
  - Internal transfers
  - Loans
  - Reconciliation
  - Open questions
- **Checks:**
  - **A:** the ledger ties to the balanced statements per account per FY.
  - **B:** every row has one allowed type, and there are no duplicate IDs.
  - **C:** transfer pairs net to zero within each FY.
  - **D:** every "Check (0)" cell is 0 (formula total = script total).
  - README status is FINAL.

### 6.2 Accountant's-eye review (Claude · Opus · high)
- **Read only:** the summary tabs and the flagged lists, not the Ledger tab.
- **Look for:**
  - jumps from one year to the next
  - large one-offs
  - loans that look like income
  - business income landing in personal accounts
  - expected items that are missing (a phone bill that stops, no interest on a savings
    account)
- **Out:** `review/qa_findings.md`. Each finding is fixed through rules or decisions, or added
  as an Ask accountant decision.

### 6.3 Handover (owner)
- **Do:** send the FY workbooks and `master_ledger.csv`. Keep the project folder: any number
  the accountant queries traces from the Ledger row to its `txn_id`, then to the statement
  file and page or line.
