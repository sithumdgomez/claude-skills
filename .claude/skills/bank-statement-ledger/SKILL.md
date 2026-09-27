---
name: bank-statement-ledger
description: Turns years of messy multi-bank statements (PDF and CSV) into reconciled, accountant-ready ledgers, one per financial year. Scripts extract every amount and prove each statement balances to the cent. The skill then matches internal transfers between the owner's accounts, tracks informal loans with friends and family per person, splits business from personal, gives the owner a grouped review list, and builds an Excel pack with live formulas. Defaults are for an Australian sole trader (FY 1 Jul - 30 Jun, ATO labels) and can be adapted. Use when someone has a pile of bank statements to clean up for an accountant or tax return, or says "reconcile my statements", "categorise my transactions", "separate business and personal", "match transfers between my accounts", "sort out money I lent friends", "build a ledger for my accountant" or "catch up on bookkeeping". Also use when continuing a bookkeeping project that has a PROGRESS.md, or adding a new financial year to one.
argument-hint: [new project folder, "continue", or "demo"]
---

# Bank statements → accountant-ready ledger

This skill does the job a senior bookkeeper does with a shoebox of bank statements: turns
them into a ledger the accountant can use without redoing it, and proves every number.

**The method in one line:** scripts move numbers, Claude writes the scripts and the rules,
the owner makes the judgement calls, and the accountant decides the tax treatment.
There's a reason for each part:
- Numbers never pass through Claude, so none can be mistyped, estimated or invented.
- Claude classifies about 1,000 *payees* once instead of about 10,000 *rows*. That is
  cheaper and more consistent.
- Decisions that need the owner's knowledge (who "A NGUYEN" is, what a cash deposit was for)
  go to the owner, not to a guess.

All paths below are relative to `${CLAUDE_SKILL_DIR}`, except `scripts/...`, `config/...` and
the other project folders, which live in the user's project folder once it's set up.

## Where this fits

- **Not tax advice.** The skill records facts and the owner's starting positions:
  - business %
  - "possibly deductible" flags
  - large items that might be depreciating assets

  Deductibility, depreciation, the final business % and GST treatment are the
  **accountant's** calls. Put anything uncertain on the "Ask accountant" list rather than
  deciding it.
- `financial-advisor` / `personal-finance-coach`: wrong tool for bookkeeping. Don't load them
  for this.
- `data-analyst`: optional, only at the end, for a plain-language summary of each year.
- `xlsx`: only if the user wants the workbooks restyled. `build_outputs.py` already writes
  them, with formulas.
- `agent-creator`: to change the two bundled subagents (`templates/agents/`).
- **Where the work runs:** Claude Code on the owner's own computer, in a folder that is
  **not** inside a git repo with a remote. `init_project.py` refuses such folders. Never put
  statements in Claude Code on the web, a GitHub repo or a synced folder. The web version
  works from a repo clone, so the data would have to be pushed.

## Start here

| Situation | Do this |
|---|---|
| New project | `python ${CLAUDE_SKILL_DIR}/tools/init_project.py ~/bookkeeping`, then follow the **Session 1** prompt in `reference/prompts.md` |
| Statements already sitting in another folder | `python3 scripts/import_statements.py "<folder>" --survey` (drafts `config/accounts.csv`), then run it again without flags for a dry run, then with `--apply`. It copies each file into `00_raw/<bank>/<account>/`, working out the account from the statement header, the file name, or the folder names. `--show "<file>"` explains a file it can't place |
| Continuing | Read the project's `PROGRESS.md` and do the next unticked step. Nothing else. |
| New financial year added to a finished project | See **Adding a year** below |
| "Show me how it works" | `python ${CLAUDE_SKILL_DIR}/tools/make_demo.py /tmp/demo-books`, then `parse_all.py` and `run_all.py` inside it |
| Changed a pipeline script | `python ${CLAUDE_SKILL_DIR}/tools/selftest.py` must pass every check before it's used on real data |

Requires Python 3.9+ and `pip install pdfplumber openpyxl` (plus `reportlab` for the demo
and self-test only).

## Who does what (two layers, kept apart)

| Actor | Does | Never does |
|---|---|---|
| **Scripts** (`scripts/`) | Extract amounts, balance checks, de-duplication, transfer matching, applying rules, totals, workbooks | Guess |
| **Claude** | Writes bank parsers and payee rules, drafts categories, clean names, groups name variants, and does the final accountant's-eye review | Type, edit or estimate an amount; open raw statements; decide a tax treatment |
| **Owner** | Fills `accounts.csv`, `notes_for_claude.md` and `people.csv`; answers the review list; signs off genuine bank oddities | — |
| **Accountant** | Approves the category list up front; rules on everything marked Ask accountant | — |

## Hard rules, and why each exists

1. **Amounts come only from source files, through scripts.** If a number passes through a
   model's output even once, it can't be trusted.
2. **A statement is used only after `reconcile.py` shows PASS.** Opening balance + rows =
   closing balance, to the cent, plus row-by-row running-balance checks. A parser bug
   usually leaves the amount right and the sign wrong, and only the balance catches it.
   `combine.py` refuses to run on anything unbalanced unless `--allow-partial` is passed,
   which stamps every output as DRAFT.
3. **Every internal transfer is matched to its other side or listed.** Unmatched transfers
   inflate income and spending at the same time. That is the owner's original problem.
4. **Low confidence goes to the owner, never gets guessed.** A wrong rule is wrong on every
   row for that payee.
5. **Rows are never edited.** Change a rule (`config/rules.csv`) or a decision
   (`config/decisions.csv`), then re-run. Every row records what classified it
   (`classified_by`), so every result can be traced.
6. **Account numbers are masked to the last 4 digits** before anything reaches Claude or
   the accountant. `.claude/settings.json` denies reads of `00_raw/` and `01_statements/`.
   Look at a layout with `scripts/dump_sample.py`.
7. **Scripts print summaries only.** Claude reads everything a script prints, so detail
   goes to files.

## The pipeline

Details, inputs, outputs and checks for every step: `reference/phases.md`. Columns and
config file formats: `reference/ledger-schema.md`.

| Phase | Command (in the project) | Gate before moving on | Model · effort |
|---|---|---|---|
| 0 Set up | `import_statements.py` (if the statements are elsewhere), then `inventory.py` | No unmapped files. Missing months requested from the bank. Accountant has approved `config/categories.csv` | Opus · high for the categories and CLAUDE.md; Sonnet · medium for the rest |
| 1 Extract | Write `scripts/parsers/<bank>_pdf.py`, then run `parse_all.py` and `reconcile.py` | Every statement PASS or SIGNED_OFF, and no continuity BREAK/GAP | Sonnet · medium; Opus · high after 2 failed tries |
| 1 Combine | `combine.py` | Rows tie out, and there are no overlap conflicts | script |
| 2 Payees | `payees.py` | The top 200 keys look like real payees | script, plus Haiku · low for clean names |
| 3 Transfers | `match_transfers.py`, `people_candidates.py` | Pairs net to $0, and the owner has checked the unmatched list and confirmed `people.csv` | script, plus Haiku · low for name grouping |
| 4 Classify | Claude writes `config/rules.csv`, then run `classify.py` | Owner spot-checks 50 random rows with no more than 2 wrong | Sonnet · medium |
| 5 Review | Owner fills `review/review_queue.xlsx`, then run `apply_review.py` | Queue empty except Ask accountant | owner |
| 6 Pack | `build_outputs.py` (or `run_all.py`) | Checks A-C PASS, and README status is FINAL | script; Opus · high for the final review |

`run_all.py` runs reconcile → combine → payees → transfers → people → classify → build and
stops at the first failure.

## Phase 1: writing a bank parser (Claude's main job)

1. `python scripts/dump_sample.py S0xx --words`: dump one statement per layout, first and
   last page. Banks change layouts over the years, so dump one statement from each era.
2. Copy `scripts/parsers/_example_pdf.py` (it shows every trap below) to `<prefix>_pdf.py`,
   where `<prefix>` comes from `accounts.csv`. For CSVs, write a MAPPING for
   `_generic_csv.py` from the dumped header, as in `_example_csv.py`. Never write it from
   memory of what a bank's format "usually" is.
3. `parse_all.py --account <id>`, then `reconcile.py`. For each FAIL, read that statement's
   rows in `review/reconcile_row_errors.csv`, dump that page and fix the code. The error file
   names the exact row, so don't eyeball whole statements.
4. Two failed attempts on the same statement: escalate to Opus at high effort. If it's
   genuinely the bank's error, the owner (not Claude) adds it to `config/signoffs.csv`.
5. For several banks, run one `bank-parser` subagent per bank in parallel (bundled in
   `.claude/agents/`). The banks are independent, and each agent's balance check verifies it.

## Phase 4: writing payee rules

- Work only from `03_data/payees.csv` rows with status `new`, biggest `abs_total` first, in
  batches of about 150. Transfers (`own-transfer`) and people (`person`) are handled
  elsewhere.
- Use only categories in `config/categories.csv`, which the accountant approved in
  Phase 0. Need a new one? Ask the owner, don't invent it.
- Use `exact` on the payee_key. Use `contains` or `startswith` on the `stem` column when one
  merchant appears with many suffixes.
- Decide business or personal by **what the payee is**. The account is only the tie-breaker
  (`business_personal = account`). A business expense paid from a personal card is still a
  business expense.
- `confidence = high` only when any bookkeeper would agree from the name alone. Anything
  else is medium and gets reviewed.
- Keep payee classification in **one** session, in batches, rather than parallel agents:
  consistency matters more than speed. Only past about 2,000 payees, use
  `payee-classifier` subagents, then check `review/rule_conflicts.csv`.

## Working efficiently

Full strategy: `reference/model-and-tokens.md`. The short version:
- Run one step per session. End every session by updating `PROGRESS.md` and
  `DECISIONS.md`, then clear the context. Don't use `/compact` for this work: summaries drop
  details like which statement has a reversed row. The next session starts with "Read
  PROGRESS.md and do the next step".
- `CLAUDE.md` (from the template) loads automatically, so never re-explain the project.
- The biggest wastes of tokens:
  - Claude reading PDFs
  - classifying row by row
  - Claude writing ledger rows in replies
  - scripts printing whole tables
  - one marathon session

## Gotchas (field-tested traps; add every new failure here and a test to `tools/selftest.py`)

- **Sign errors** are the most common extraction bug: the right amount lands in the wrong
  column. Decide the sign by column x-position, never by guessing. The row-level balance
  check pinpoints them.
- **Missing years:** many statements print "03 Jan". Take the year from the statement
  period. A Dec–Jan statement spans two years.
- **Month-first date parsing** (a pandas/Excel default) silently swaps 03/04 and 04/03. All
  parsing here is day-first, and `reconcile.py` flags dates outside the statement period.
- **CSV exports are often newest-first.** Reverse the whole file, don't sort by date, or
  rows on the same day scramble and the running balance breaks.
- **Brought-forward, carried-forward, opening and closing lines** look like transactions.
  Skip them explicitly.
- **Descriptions that wrap onto a second line** must be joined to the row above. A line with
  an amount but no date should raise an error, not be dropped.
- **The same period from two sources** (a PDF plus a CSV export): `combine.py` removes
  duplicates one-to-one and stops on rows found in only one of them. Never pick one
  silently.
- **CSVs with no balance column** can't be proved. Add the PDF's opening and closing to
  `config/balance_anchors.csv`, or the statement stays UNVERIFIED.
- **Two identical transfers the same week:** the matcher flags them "ambiguous". The owner
  confirms them on the review list, or pairs them by hand in `config/manual_matches.csv`.
- **Transfers leaving on 30 June and arriving 1 July** belong to different years. They are
  listed, not netted.
- **Masked reference numbers or phone numbers ending in an own account's last 4 digits**
  can look like a transfer. The unmatched list is for the owner to check, not proof.
- **"TRANSFER FROM <friend>" is not an internal transfer.** It needs a person entry in
  `people.csv`. Someone who only ever pays the owner is flagged as possible income, not a
  loan.
- **Cash deposits** always go to review, because they could be income.
- **Bank interest earned is taxable income.** It's listed per account on the Personal tab.
- **ATO refunds are not income; ATO payments are not expenses** (type Tax). If the owner is
  GST-registered, BAS payments need their own treatment: ask the accountant.
- **Payments to a credit card, PayPal or Wise** are transfers to an account missing
  from the set. The real spending is on that account's statements (Wise and PayPal let you
  download them). Add them, or use type Outside account.
- **Afterpay and other buy-now-pay-later services** give no statements, only an order history
  (often just screenshots). The instalments on the bank statement are the amounts; never
  take amounts from the order history. It only matters for business purchases: the owner keeps
  a screenshot per business order in `evidence/afterpay/` as the receipt, and marks the
  matching instalments as business in the review list, naming the order in the note.
  Everything else paid through Afterpay is personal.
- **Payment processors** (Stripe, Square, PayPal) pay out net of fees. The accountant needs
  gross income, so flag it and get the processor reports.
- **Transaction lines name the owner's other accounts** ("TRANSFER FROM xx4321"). Never work
  out which account a statement belongs to from its transactions; only from its header, file
  name or folder. `import_statements.py` reads PDF headers up to the first transaction and
  only the "account" column of CSVs, for this reason.
- **CommBank PDFs:** bold labels can be "fake bold" (each letter printed twice, read as
  `AAccccoouunntt`), and a transaction runs over 2–3 lines with the amount on the last
  ("16 Dec MCDONALDS ..." / "Card xx1234" / "Value Date: 13/12/2022  13.10  $104.14 CR").
  Sideways mail-sorting codes up the left margin ("2.1.12345.67890") look like a date and an amount. `parsers/_pdf_helpers.clean_page()` removes both the doubled letters and sideways text (`page_lines` uses it); a CBA parser must join
  each date line with the lines below it up to the one with the amount. Pages after the first
  repeat a small header (statement number, account number) above the table.
  `import_statements.py` ends the header at the "Date ... Balance" table heading, so a
  debit-card number on a transaction line ("Card xx9999") is never taken for the account.
- **Headers carry numbers that are not account numbers.** Every NAB statement starts with
  "call 13 22 65 for Personal Accounts or 13 10 12 for Business Accounts", and footers carry the
  bank's ABN; both once passed for an account ending. `import_statements.py` skips phone
  numbers, ABNs and numbers labelled customer/reference/licence/BPAY. A header can also show a
  linked account's number: the survey never gives a second account a number that is already the
  only one on another account's statements, and the import picks the account named in the file
  name. Always have the owner confirm each account's last 4 digits (their banking app shows
  them) and check the medium-confidence rows in `review/import_report.csv` before `--apply`.
- **Some statements show no account number in their header** (seen with CommBank
  downloads). `import_statements.py --survey` then groups them by bank and account name from
  the file and folder names ("CBA_Business-Saving_2023-02_to_2023-05.pdf" → CommBank,
  Business Saving) and leaves `last4` empty for the owner to fill in. Run `--show "<file>"` to
  see the masked page-1 text and where the script thinks the header ends. In file names, "_"
  counts as part of a word for `\b`, so match bank names against `path_words()`, never the raw
  path.
- **pdfplumber needs a text layer.** A scanned statement (text_layer N in the inventory)
  needs an e-statement or CSV from the bank. OCR misreads digits.

## Adding a year (e.g. FY2027)

1. Put the new statements in `00_raw/`, set `last_fy` in `config/project.json`, and run
   `inventory.py`. Existing statements keep their IDs.
2. `parse_all.py --only <new ids>`, then `reconcile.py`. The continuity check links the new
   statements to the old ones.
3. `run_all.py`. Existing rules and decisions carry over. `payees.py` marks only genuinely
   new payees as `new`, so only those go to Claude.
4. Review, then build. Earlier years' workbooks are rebuilt identically unless a rule changed.
   If one did, tell the accountant.

## Adapting outside Australia

Change `fy_start_month` (1 for calendar years), `currency` and the `ato_label` column of
`config/categories.csv`. Research the local tax form's labels with the `researcher` skill;
don't recall them from memory. Everything else is country-neutral. See `reference/australia.md`
for what is AU-specific and where each fact comes from.

## Files in this skill

- `pipeline/`: the scripts copied into each project (`scripts/`), plus `parsers/` helpers
  and worked examples
- `templates/`: CLAUDE.md, PROGRESS.md, DECISIONS.md, notes_for_claude.md, config
  CSVs (including the category list mapped to ATO labels), settings.json and two subagents
- `tools/init_project.py`, `tools/make_demo.py`, `tools/selftest.py`
- `reference/phases.md`: every step with who, inputs and outputs, the tool and model, and
  its check
- `reference/ledger-schema.md`: ledger columns, types, config formats and workbook tabs
- `reference/model-and-tokens.md`: model choice, sessions, parallel agents and token wasters
- `reference/australia.md`: FY, ATO labels, sole-trader treatments and sources
- `reference/prompts.md`: paste-ready prompts for each session
