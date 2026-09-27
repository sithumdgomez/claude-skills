# Notes for Claude (filled in by the owner - Claude reads this, never guesses these)

## The basics
- Registered for GST? (yes/no, and from when)
- What does the business do?
- How do clients pay you? (bank transfer to which account, cash, card terminal, platform)
  Clients paying into a personal account is fine to say: every account's money in is reviewed
- Cash you were paid and never put in a bank: it is in no statement. List it in
  `income_not_in_bank.csv` (date, who, what for, amount, how you know), from invoices,
  messages or a diary. Leave the amount blank if you don't know it; Claude never fills it in
- Any income that is not from the business? (job, Centrelink, rent, interest)
- Work paid in instalments or part-payments? Invoice numbering (e.g. "INV-", "JC-") so
  payments can be recognised
- Work done free, or swapped for goods/services instead of money? List swaps in
  `income_not_in_bank.csv` with kind Swap (who, when, what you did, what you got, your rough
  value) - they are not in the bank statements
- Did the business change structure (e.g. sole trader -> company)? From what date, and which
  accounts moved to the new entity?

## Accounts
- Every account with its bank, name, last 4 digits, business or personal, opened/closed dates
  (also goes in config/accounts.csv)
- How your own name appears on transfers (e.g. "J CITIZEN", "JANE C") - goes in config/project.json own_names
- Credit cards, PayPal, Afterpay, Wise, loans, or accounts NOT in these statements? List them,
  and say whether any were used for the business

## People
- Friends / family you lend to or borrow from (names as they appear on transfers)
- People who are also clients

## Mixed use
- Things used partly for business (phone, internet, car, home office) and a rough business %

## Anything else
- Big one-off purchases, windfalls, or events in these years the accountant should know about
