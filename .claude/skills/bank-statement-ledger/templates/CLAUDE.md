# Bookkeeping project: bank statements → accountant-ready ledgers

Goal: turn the bank statements in `00_raw/` into one reconciled ledger per financial year
that the accountant can use without redoing the work. The method is the
`bank-statement-ledger` skill; this file is the project's standing orders.

## Hard rules (never break these)

1. **Amounts only come from the source files, through scripts.** Never type, estimate,
   round or edit an amount, in a file or in a reply. Claude writes parsers, rules and
   decisions; scripts move the numbers.
2. **A statement is used only after it balances.** Opening balance + rows = closing
   balance, to the cent (`scripts/reconcile.py`). No exceptions without a line in
   `config/signoffs.csv` written by the owner.
3. **Every internal transfer is matched to its other side** (`scripts/match_transfers.py`)
   or listed in `review/transfers_unmatched.csv` for the owner.
4. **Anything not classified with high confidence goes to the owner's review list.**
   Never guess to make the list shorter.
5. **Every row keeps its original description, source file and page/line.** Fix
   classifications by changing rules or decisions, never by editing rows.
6. **Account numbers are masked to the last 4 digits** in everything Claude reads or writes.
   Never open `00_raw/` or `01_statements/` (blocked in `.claude/settings.json`). To see a
   statement's layout, run `python scripts/dump_sample.py <statement_id>`.
7. **Scripts print summaries and failures only.** Details go to files; read the file you
   need with a limit, not the whole thing.

## Folder map

| Folder | What | Who writes it |
|---|---|---|
| `00_raw/` | Original statements, read-only | Owner |
| `01_statements/` | Renamed copies, `S001_<account>_<start>_<end>.pdf` | `inventory.py` |
| `02_extracted/` | One CSV + meta.json per statement | `parse_all.py` |
| `03_data/` | transactions, payees, matches, classified ledger | scripts |
| `config/` | accounts, categories, rules, people, decisions, inventory | owner + Claude (rules) + scripts |
| `review/` | Lists for the owner: review queue, unmatched transfers, errors | scripts |
| `output/` | Reconciliation, coverage, FY workbooks, master ledger | scripts |
| `scripts/` | The pipeline. `scripts/parsers/<bank>_pdf.py` are written per bank | Claude |

## Pipeline

```
python scripts/import_statements.py "<folder>" --survey   # only if statements are elsewhere; then dry run, then --apply
python scripts/inventory.py          # IDs, masked copies, coverage guess
python scripts/dump_sample.py S001   # masked sample of one layout (for writing a parser)
python scripts/parse_all.py          # run the bank parsers
python scripts/run_all.py            # reconcile -> combine -> payees -> transfers -> people -> classify -> build
python scripts/apply_review.py       # after the owner fills review/review_queue.xlsx
```
Each script's docstring explains its inputs, outputs and checks. Read the docstring, not the code, unless you are changing the script.

## Who decides what

- **Scripts:** every number, every balance check, transfer matching, applying rules.
- **Claude:** parsers, payee rules (`config/rules.csv`), description clean-up, spotting
  patterns, the final accountant-style review.
- **Owner:** people and loans, business vs personal when unclear, business %, anything on the
  review list, sign-offs. Owner decisions (`config/decisions.csv`) always beat Claude's rules.
- **Accountant:** final business %, deductibility, depreciation, anything marked Ask accountant.

## Model per task

| Task | Model | Effort |
|---|---|---|
| Design, categories, hard debugging after 2 failed tries, final review | Opus | high |
| Parsers and scripts | Sonnet | medium |
| Payee rules | Sonnet | medium (low for obvious shops) |
| Clean names, grouping name variants | Haiku | low |

## Session ritual

- Start: read `PROGRESS.md`, do the next unchecked step, nothing else.
- One step per session. Clear the context when a step's check passes.
- End: update `PROGRESS.md` (status, numbers, next step) and `DECISIONS.md` (owner's calls).

## Project facts

Fill these in during Session 1 (from `notes_for_claude.md`):
- Financial years: FY2023 (1 Jul 2022 – 30 Jun 2023) to FY2026. AUD. Sole trader.
- GST registered: see `config/project.json`.
- Accounts: see `config/accounts.csv`.
