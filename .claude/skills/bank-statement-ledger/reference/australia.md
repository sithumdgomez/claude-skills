# Australian defaults and where they come from

Checked in September 2026. Re-check against the ATO before relying on a detail. Tax
treatment is always the accountant's decision; this file only explains why the defaults are
what they are.

## Financial year
- Runs 1 July to 30 June, and is labelled by the year it ends: FY2024 = 1 Jul 2023 – 30 Jun
  2024.
- `config/project.json`: `"fy_start_month": 7`.

## Business expense labels (`ato_label` in `categories.csv`)
The category list maps business categories to the expense labels at item P8 (business income
and expenses) of the ATO's Business and professional items schedule:
- Cost of sales, shown as Opening stock, Purchases and other costs, and Closing stock
- Foreign resident withholding expenses
- Contractor, sub-contractor and commission expenses
- Superannuation expenses
- Bad debts
- Lease expenses
- Rent expenses
- Interest expenses within Australia
- Interest expenses overseas
- Depreciation expenses
- Motor vehicle expenses
- Repairs and maintenance
- All other expenses

The income labels include "Other business income" and "Assessable government industry
payments".

A bank ledger only sees *purchases*. Opening and closing stock, depreciation and
reconciliation items are the accountant's work. "Equipment purchases" is mapped to
Depreciation expenses as a pointer, and the accountant decides between depreciation and an
immediate write-off.

Sources:
- [ATO – Business and professional items schedule instructions 2025](https://www.ato.gov.au/forms-and-instructions/business-and-professional-items-schedule-2025-instructions)
- [ATO – P8 Business income and expenses (2022)](https://www.ato.gov.au/forms-and-instructions/business-and-professional-items-schedule-2022-and-instructions/instructions-to-complete-the-bpi-schedule/p8-business-income-and-expenses)
- [MYOB practice support – Item P8 labels 2024](https://practice-support.myob.com/taxau2024/item-p8-business-income-and-expenses)

## Sole-trader treatments built into the defaults
- **Business or personal is decided by what the transaction is.** A sole trader and the
  business are the same taxpayer. A business expense paid from a personal card is still a
  business expense. Money moved from the business account to a personal one is a *drawing*,
  not an expense, and a private expense isn't deductible.
  ([ATO – using business money and assets for private purposes](https://www.ato.gov.au/businesses-and-organisations/starting-registering-or-closing-a-business/running-your-own-business/using-your-business-money-and-assets-for-private-purposes))
- **Bank interest is assessable income**, so it's listed per account.
  ([ATO – investing in bank accounts](https://www.ato.gov.au/individuals-and-families/investments-and-assets/investing-in-bank-accounts-and-income-bonds))
- **Possibly-deductible personal items** are flagged for the accountant, not claimed:
  - tax agent fees ([ATO – cost of managing tax affairs](https://www.ato.gov.au/individuals-and-families/income-deductions-offsets-and-records/deductions-you-can-claim/cost-of-managing-tax-affairs))
  - donations to deductible gift recipients ([ATO – gifts and donations](https://www.ato.gov.au/individuals-and-families/income-deductions-offsets-and-records/deductions-you-can-claim/gifts-and-donations))
  - income protection insurance
  - personal super contributions
- **Your own super is not "Superannuation expenses"** (that label is for employees). It's a
  personal item for the accountant.
- **ATO payments and refunds** are type Tax, not an expense or income.

## GST
- Registration is required once GST turnover reaches $75,000
  ([ATO – registering for GST](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/registering-for-gst)).
- If the owner is registered:
  - set `"gst_registered": true`
  - add `gst_amount` and `bas_quarter` columns, as agreed with the accountant
  - treat BAS payments to the ATO separately from income tax
- The default pipeline assumes no GST registration.

## Adapting to another country
- Change `fy_start_month` and `currency`.
- Replace the `ato_label` values with the local return's labels. Research them with the
  `researcher` skill; don't use memory.
- Remove or replace the AU-specific categories (D9, D10, super).
- The scripts contain nothing country-specific apart from the default keyword lists in
  `project.json`: the transfer words (OSKO, PayID, BPAY are Australian) and the state codes
  stripped from payee keys in `payees.py`.
