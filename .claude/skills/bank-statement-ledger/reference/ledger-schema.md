# Ledger schema, types and config formats

## Master ledger columns (`03_data/classified.csv`, `output/master_ledger.csv`, Ledger tab)

| Column | Example | Meaning |
|---|---|---|
| txn_id | S037-0042 | Permanent ID: statement 37, row 42. Never reused |
| fy | FY2024 | Financial year by transaction date (FY2024 = 1 Jul 2023 – 30 Jun 2024) |
| date | 2023-11-03 | Transaction date as printed on the statement |
| account_id / account_name | BANKA-BUS-1234 / Business | Masked account |
| original_description | SQ *BEAN THERE MELB AU | Never edited (account numbers masked) |
| cleaned_description | Bean There Cafe | From `config/clean_names.csv`, the person's name, or title case |
| counterparty | Alex Nguyen / (own account) | Person for loans and gifts; own account for transfers |
| amount | -12.50 | Signed: + is money into this account. Exact decimal |
| money_in / money_out | – / 12.50 | The same amount in two columns, for convenience |
| type | Expense | One of the types below |
| category | Business meals and entertainment | From `config/categories.csv` |
| ato_label | All other expenses | From the category (business rows) |
| business_personal | Business / Personal / Mixed | Decided by what the transaction is, not by the account |
| business_pct | 60 | Only for Mixed; the owner's starting figure for the accountant |
| match_id | T0153 | Links the two sides of an internal transfer |
| classified_by | R0412 / D0031 / MATCH:T0153 / MATCH:T0153+D0040 / PERSON:Alex / NONE | What decided the row |
| confidence | high / medium / low | |
| review_status | Auto / Needs review / Reviewed / Ask accountant | |
| review_reasons | no rule for this payee; cash deposit – could be income | Why it's on the review list |
| notes | large business item … | Flags and decision notes |
| source_file, source_page, source_line | S037_BANKA-BUS-1234_2023-10-01_2023-12-31.pdf, 3, 14 | Trace back to the statement |
| statement_id, balance_shown, payee_key | | Supporting fields |

Add `gst_amount` and `bas_quarter` only if the owner is GST-registered, and agree the
treatment with the accountant first.

## Types (controlled list; `common.TYPES`)

| Type | Counted in income/expense totals? | Notes |
|---|---|---|
| Business income | Yes (Business P&L) | |
| Other income | Yes (Personal tab) | Interest, wages, government payments |
| Expense | Yes | Business, Personal or Mixed |
| Refund | Yes, reduces its category | Not income |
| Internal transfer | No | Between two of the owner's accounts, matched |
| Owner drawing | No | Business account → personal account |
| Owner contribution | No | Personal account → business account |
| Loan out / Loan in | No (Loans tab) | Money to / from a person. The net per person is who owes whom |
| Gift or shared bill | No | Personal money to or from people that isn't a loan |
| Tax | No | ATO payments and refunds |
| Outside account | No | To or from an account whose statements aren't in the set (card, PayPal) |
| Unknown | – | Always on the review list |

In a review decision, "Loan" is accepted and becomes Loan out or Loan in depending on the
direction of the money.

## Config files (all in `config/`)

**accounts.csv**, filled in by the owner
```
account_id,bank,account_name,last4,default_use,opened,closed,raw_folder,parser_prefix
BANKA-BUS-1234,Bank A,Business,1234,business,2021-03-01,,BankA/Business,banka
BANKA-EVE-5678,Bank A,Everyday,5678,personal,,,BankA/Everyday,banka
```
- `default_use`: business or personal.
- `raw_folder`: the folder under `00_raw/`.
- `parser_prefix`: selects `scripts/parsers/<prefix>_pdf.py` / `_csv.py`. It defaults to the
  bank name in lower case with letters and digits only. Give an account its own prefix if
  its layout differs.
- `opened` and `closed`: leave them blank if the account was open for the whole period.

**project.json** holds these settings:
- FY start month, first and last FY, currency
- `gst_registered`
- `own_names`: the owner's names as they appear on transfers
- `transfer_max_days` (default 4)
- `loan_flag_threshold`
- `large_business_item_threshold`
- `date_tolerance_days`
- the cash-deposit and transfer keyword lists

**inventory.csv** is written by `inventory.py`. The owner may edit only two columns:
- `include`: set to N to drop a superseded source.
- `priority`: 1 wins over 2 when two sources overlap. PDFs default to 1, CSVs to 2.

**rules.csv** is written by Claude. Columns are documented in
`pipeline/classify_rules.py`:
```
rule_id,match_type,pattern,direction,account_scope,type,category,business_personal,business_pct,confidence,reason
R0107,contains,WOOLWORTHS,out,any,Expense,Groceries,Personal,,high,Supermarket
R0104,contains,TELSTRA,out,any,Expense,Phone and internet,Mixed,60,high,Phone - 60% per DECISIONS.md
```
Exact rules win. Otherwise the first matching rule in the file wins.

**people.csv** is drafted by Claude and confirmed by the owner:
```
person,match_type,pattern,relationship,treatment,note
Alex Nguyen,contains,ALEX NGUYEN,friend,Loan,
```

**decisions.csv** is written by `apply_review.py`. Its columns are decision_id, scope
(txn / payee / person), key, type, category, business_personal, business_pct,
counterparty, ask_accountant, note, decided_on and source.

**manual_matches.csv** (out_txn_id,in_txn_id,note): pairs the owner links by hand.

**normalise.csv** (pattern,replacement,note): extra regex clean-up for payee keys, applied
before the built-in rules.

**clean_names.csv** (payee_key,clean_name): readable names.

**balance_anchors.csv** (statement_id,opening_balance,closing_balance,source_note): the owner
copies these from the PDF for CSV exports that have no balance column.

**signoffs.csv** (statement_id,reason,signed_off_by,signed_off_on): owner only, for a checked
bank-side anomaly.

**categories.csv** (category,applies_to,types,ato_label,possibly_deductible,description):
approved by the accountant in Phase 0.

## Workbook tabs (`output/FY20xx.xlsx`)

| Tab | Contents |
|---|---|
| README | Status (FINAL or DRAFT with the reasons), headline figures linked live to the tabs, what each tab is, type definitions, how to trace a number, control checks |
| Ledger | Every row in the FY, with a filter and frozen header |
| Business P&L | Income and expenses by ATO label, then category, as `SUMIFS` formulas. A Built value column and a Check (0) column sit beside each |
| Mixed use | Mixed rows with the business % and a formula for the business portion (not in the P&L totals) |
| Personal | Other income by category, interest by account, personal spending by category, possibly-deductible personal items, ATO payments |
| Internal transfers | Matched pairs touching the FY, totals of drawings and contributions |
| Loans | Per person: this FY's movements, the net owed at 30 June, flags. Detail with a running balance |
| Reconciliation | The statement balance checks for the FY, and account balances at the start and end of the FY |
| Open questions | Unreviewed rows, Ask accountant items, unmatched or crossing transfers, loan flags, large business items, unbalanced or missing statements |
