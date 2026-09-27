"""Regression test for the pipeline: builds the demo in a temp folder, runs everything,
compares the ledger to the generator's ground truth, then tries to break it on purpose.

  pip install pdfplumber openpyxl reportlab
  python <skill>/tools/selftest.py            # prints PASS/FAIL per test, exit 1 on any FAIL

Run it after changing any pipeline script. When a real project hits a new failure,
add a test here that reproduces it (and a line to the skill's Gotchas).
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  - ' + detail if detail and not ok else ''}")


def run(root, script, *args):
    r = subprocess.run([sys.executable, str(root / "scripts" / script), *args], cwd=root,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(path, data):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)


def unit_tests(root):
    sys.path.insert(0, str(root / "scripts"))
    import common as c
    D = Decimal
    money_cases = {"1,234.56": D("1234.56"), "$1,234.56 CR": D("1234.56"), "12.00 DR": D("-12.00"),
                   "(45.20)": D("-45.20"), "45.20-": D("-45.20"), "-0.50": D("-0.50"), "": None, "Nil": D("0.00")}
    ok = all(c.parse_money(k) == v for k, v in money_cases.items())
    try:
        c.parse_money("12,34O.00")
        ok = False
    except ValueError:
        pass
    check("parse_money handles CR/DR, brackets, trailing minus; rejects junk", ok)
    p0, p1 = dt.date(2022, 12, 1), dt.date(2023, 1, 31)
    ok = (c.parse_date("03 Jan", p0, p1) == dt.date(2023, 1, 3) and c.parse_date("28 Dec", p0, p1) == dt.date(2022, 12, 28)
          and c.parse_date("03/04/2023") == dt.date(2023, 4, 3) and c.parse_date("3/4/23") == dt.date(2023, 4, 3)
          and c.parse_date("2023-04-03") == dt.date(2023, 4, 3))
    try:
        c.parse_date("03 Jan")
        ok = False
    except ValueError:
        pass
    check("parse_date is day-first, infers missing years from the period, refuses to guess", ok)
    m = {"BSB 062-000 12345678": "BSB xx5678", "CARD 4564 1234 5678 9012": "CARD xx9012",
         "Account number 1234 5678": "Account number xx5678", "REF 987654321": "REF xx4321",
         "01/07/2022 1,234.56 123456.78": "01/07/2022 1,234.56 123456.78", "2022-07-01": "2022-07-01"}
    bad = {k: c.mask(k) for k, v in m.items() if c.mask(k) != v}
    check("mask keeps last 4 of account/card numbers and leaves dates and amounts alone", not bad, str(bad))
    import inventory
    periods = {"Statement starts 18 January 2025\nStatement ends 10 March 2025": (dt.date(2025, 1, 18), dt.date(2025, 3, 10)),
               "Period 1 Feb 2023 - 31 May 2023": (dt.date(2023, 2, 1), dt.date(2023, 5, 31)),
               "Statement Period 01/07/2023 to 31/12/2023": (dt.date(2023, 7, 1), dt.date(2023, 12, 31))}
    bad = {t: inventory.detect_period(t) for t, v in periods.items() if inventory.detect_period(t) != v}
    check("statement periods are found in the usual layouts, including NAB's starts/ends lines", not bad, str(bad))
    import classify
    ps_out, ps_in = classify.treatment_result("Personal spending", D("-50.00")), classify.treatment_result("Personal spending", D("50.00"))
    check("people marked Personal spending: money out is a personal expense, never a loan",
          (ps_out["type"], ps_out["bp"], ps_out.get("category")) == ("Expense", "Personal", "Other personal expense")
          and ps_in["type"] == "Unknown", f"{ps_out} {ps_in}")
    import import_statements as imp
    not_accounts = ["Accounts or 13 10 12 for Business Accounts.", "Enquiries 13 1998", "Phone 1300 123 456",
                    "ABN 11 222 333 444 AFSL", "Customer number 98-765-2468", "Mobile 0412 345 678"]
    accounts = {"Account number 77-888-1357": ["1357"], "Account Number 06 1234 00005678": ["5678"],
                "Account number 123 456 789": ["6789"]}
    bad = [t for t in not_accounts if imp.endings(t)] + [t for t, v in accounts.items() if imp.endings(t) != v]
    check("phone numbers, ABNs and customer numbers are never taken for account numbers", not bad, str(bad))
    real_order = ["MR J CITIZEN", "13 SAMPLE BEND", "SUBURB VIC 3000", "12.00.34V", "O.123D.456S.7R.LS", "1234",
                  "7R123ZZ", "2.1.12345.67890", "*#*", "Your Statement", "Statement 1 (Page 1 of 2)",
                  "Account Number 06 1234 00005678", "032", "Statement", "Period 1 Feb 2023 - 31 May 2023",
                  "Closing Balance $250.00CR", "Enquiries 13 1998", "Date Transaction Debit Credit Balance",
                  "01 Feb 2023 OPENING BALANCE Nil", "22 MayTransfer from xx5555 CommBank app", "Bill $20.00 $20.00CR"]
    cut = imp.header_end(real_order)
    check("header reading skips margin codes that look like a date + amount (CommBank line order)",
          cut == 17 and imp.header_endings("\n".join(real_order[:cut])) == ["5678"], f"cut at {real_order[cut]!r}")
    check("fy_of: 30 Jun 2023 = FY2023, 1 Jul 2023 = FY2024",
          c.fy_of(dt.date(2023, 6, 30)) == "FY2023" and c.fy_of(dt.date(2023, 7, 1)) == "FY2024")


def make_pdf(path, lines):
    from reportlab.pdfgen import canvas
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    for i, line in enumerate(lines):
        c.drawString(40, 800 - 16 * i, line)
    c.save()


def make_cba_like_pdf(path, fake_bold=False, number_drop=0.0, bare=False, margin_codes=False):
    """Page 1 laid out like a CommBank statement (made-up numbers): two header columns, bold labels
    (optionally "fake bold": printed twice), transactions over 3 lines with the amount on the last,
    and a debit card number in a transaction that must never be taken for the account.
    bare=True leaves out the table heading and the opening balance line; margin_codes=True adds
    sideways mail-sorting codes up the left margin that look like a date and an amount."""
    from reportlab.pdfgen import canvas
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(595, 842))

    def txt(x, y, s, bold=False, size=9, right=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        draw = c.drawRightString if right else c.drawString
        draw(x, 842 - y, s)
        if bold and fake_bold:
            draw(x + 0.3, 842 - y, s)
    if margin_codes:
        for y, code in [(300, "12.00.34V"), (380, "2.1.12345.67890"), (460, "7R123ZZ")]:
            c.saveState(), c.translate(15, 842 - y), c.rotate(-90)
            c.setFont("Helvetica", 6), c.drawString(0, 0, code), c.restoreState()
    txt(345, 60, "Your Statement", bold=True, size=20)
    txt(345, 88, "Statement 1", bold=True), txt(535, 88, "(Page 1 of 2)", right=True)
    txt(345, 115, "Account Number", bold=True), txt(535, 115 + number_drop, "06 1234 00005678", right=True)
    txt(345, 140, "Statement", bold=True), txt(40, 150, "MR J CITIZEN")
    txt(345, 152, "Period", bold=True), txt(535, 152, "1 Feb 2023 - 31 May 2023", right=True)
    txt(40, 162, "13 SAMPLE BEND"), txt(345, 170, "Closing Balance", bold=True), txt(535, 170, "$250.00 CR", right=True)
    txt(40, 174, "SUBURB VIC 3000"), txt(345, 192, "Enquiries", bold=True), txt(535, 192, "13 1998", right=True)
    if not bare:
        txt(40, 400, "Date", bold=True), txt(75, 400, "Transaction", bold=True)
        txt(535, 400, "Balance", bold=True, right=True)
        txt(40, 420, "01 Feb 2023 OPENING BALANCE"), txt(535, 420, "Nil", right=True)
    txt(40, 438, "22 May WOOLWORTHS 1234 SUBURB AUS"), txt(75, 449, "Card xx9999")
    txt(75, 460, "Value Date: 20/05/2023"), txt(385, 460, "10.00", right=True), txt(535, 460, "$10.00 CR", right=True)
    c.save()


def import_by_name_test(tmp):
    """A real-world layout: FY folders, names like CBA_Business-Saving_2023-02_to_2023-05.pdf, statements
    whose header shows no account number, and an address line next to the closing balance."""
    src = tmp / "Bank_Statements_Organized"
    body = ["Date Transaction Debit Credit Balance", "01 Feb 2023 OPENING BALANCE $1,000.00 CR",
            "03 Feb 2023 TRANSFER TO XX5555 NETBANK 50.00 $950.00 CR"]
    no_number = ["Your Statement", "J CITIZEN", "Statement 3 (Page 1 of 1)"] + body
    nab_header = ["National Australia Bank", "J CITIZEN", "5 The Crescent Closing balance $950.00 CR",
                  "Account number 083-123 12342580"]
    files = {"FY2023/CBA_Business-Saving_2023-02_to_2023-05.pdf": ("CommBank/BusinessSaving", no_number),
             "FY2024/CBA_Business-Saving_2023-09_to_2023-10.pdf": ("CommBank/BusinessSaving", no_number + ["x"]),
             "FY2023/CBA_Personal-Transaction_2022-11_to_2023-05.pdf": ("CommBank/PersonalTransaction", no_number + ["y"]),
             "FY2026/NAB_Everyday_2025-07.pdf": ("NAB/Everyday_2580", nab_header + body),
             "FY2025/NAB_Everyday_2024-07.pdf": ("NAB/Everyday_2580", no_number + ["z"])}
    for rel, (_, lines) in files.items():
        make_pdf(src / rel, lines)
    root = tmp / "fresh project"
    subprocess.run([sys.executable, str(TOOLS / "init_project.py"), str(root)], capture_output=True, check=True)
    code, out = run(root, "import_statements.py", str(src), "--survey")
    acc = {r["account_id"]: r for r in rows(root / "config" / "accounts.csv")}
    want = {"CBA-BUSSAV": ("CommBank", "Business Saving", ""), "CBA-PERTRA": ("CommBank", "Personal Transaction", ""),
            "NAB-2580": ("NAB", "Everyday", "2580")}
    got = {k: (v["bank"], v["account_name"], v["last4"]) for k, v in acc.items()}
    check("survey groups files without an account number by bank + name, and finds the number past an address",
          code == 0 and got == want and "5555" not in str(got), f"{got}\n{out[-600:]}")
    for r in acc.values():
        r["default_use"] = "business" if "Business" in r["account_name"] else "personal"
    write_rows(root / "config" / "accounts.csv", list(acc.values()))
    code, out = run(root, "import_statements.py", str(src), "--apply")
    placed = {rel: (root / "00_raw" / d / Path(rel).name).exists() for rel, (d, _) in files.items()}
    check("import places those files by bank + account name and says which last4 are missing",
          code == 0 and all(placed.values()) and "last4 is empty for CBA-BUSSAV, CBA-PERTRA" in out,
          f"{placed}\n{out[-600:]}")
    code, out = run(root, "import_statements.py", str(src), "--show", "FY2026/NAB_Everyday_2025-07.pdf")
    check("--show prints the header masked and finds the account ending",
          code == 0 and "xx2580" in out and "12342580" not in out and "header ends here" in out
          and "Account endings found in the header: xx2580" in out, out[-600:])
    outs = []
    for name, kw in [("fake bold", {"fake_bold": True}), ("number below its label", {"number_drop": 4.5}),
                     ("no table heading", {"bare": True}), ("margin codes", {"margin_codes": True, "bare": True})]:
        pdf = tmp / "cba samples" / f"{name}.pdf"
        make_cba_like_pdf(pdf, **kw)
        outs.append(run(root, "import_statements.py", str(src), "--show", str(pdf))[1])
    check("CommBank-style header (fake bold, number below label, 3-line transactions): account found, card ignored",
          all("Account endings found in the header: xx5678\n" in o and "00005678" not in o for o in outs),
          "\n".join(o[-500:] for o in outs))


def import_two_accounts_test(tmp):
    """One bank, two accounts (Savings and Everyday) laid out like NAB: every statement starts with the
    bank's phone number on a line that says "Accounts", one Everyday statement also shows the linked
    savings account above its own number, one has the mail barcode (read as digits) on the line after
    "Account Balance Summary", and Everyday statements outnumber Savings ones."""
    src = tmp / "two accounts"
    top = ["NAB Classic Banking", "For further information call 13 12 34 for Personal",
           "Accounts or 13 56 78 for Business Accounts.", "J CITIZEN", "BSB number 083-999"]
    table = ["Date Particulars Debits Credits Balance", "01 Jul 2024 Brought forward 100.00 Cr",
             "02 Jul 2024 V2580 WOOLWORTHS Card number 4564 1234 5678 2580 10.00 90.00 Cr"]
    files = {"FY2025/NAB_Savings_2024-07_to_2025-01.pdf": ("NAB/Savings_2468", top + ["Account number 12-345-2468"] + table),
             "FY2026/NAB_Savings_2025-01_to_2025-07.pdf": ("NAB/Savings_2468", top + ["Account number 12-345-2468"] + table[:2]),
             "FY2025/NAB_Transaction_2024-07_to_2025-01.pdf": ("NAB/Transaction_1357", top + [
                 "Linked savings account 12-345-2468", "Account number 55-666-1357"] + table),
             "FY2025/NAB_Transaction_2025-01_to_2025-03.pdf": ("NAB/Transaction_1357", top + [
                 "Account Balance Summary", "0987654321", "Account number 55-666-1357"] + table[:2]),
             "FY2026/NAB_Transaction_2025-07.pdf": ("NAB/Transaction_1357", top + [
                 "Account number 55-666-1357"] + table[:1] + [
                 "Statement number 2 National Australia Bank Limited ABN 11 222 333 444 AFSL"])}
    for rel, (_, lines) in files.items():
        make_pdf(src / rel, lines)
    csv_rel = "FY2026/NAB_Transaction_2026-01_to_2026-06.csv"
    (src / csv_rel).write_text("Date,Amount,Account Number,Transaction Details,Balance\n"
                               "01 Jan 26,-10.00,55-666-1357,WOOLWORTHS,40.00\n")
    files[csv_rel] = ("NAB/Transaction_1357", None)
    root = tmp / "two accounts project"
    subprocess.run([sys.executable, str(TOOLS / "init_project.py"), str(root)], capture_output=True, check=True)
    code, out = run(root, "import_statements.py", str(src), "--survey")
    acc = {r["account_id"]: r for r in rows(root / "config" / "accounts.csv")}
    got = {k: (v["account_name"], v["last4"]) for k, v in acc.items()}
    check("survey splits two accounts at one bank even when one statement shows both numbers",
          got == {"NAB-2468": ("Savings", "2468"), "NAB-1357": ("Transaction", "1357")}, f"{got}\n{out[-500:]}")
    for r in acc.values():
        r["default_use"] = "personal"
    write_rows(root / "config" / "accounts.csv", list(acc.values()))
    code, out = run(root, "import_statements.py", str(src), "--apply")
    placed = {rel: (root / "00_raw" / d / Path(rel).name).exists() for rel, (d, _) in files.items()}
    check("import files each statement under the account its file name names, not the first number",
          code == 0 and all(placed.values()), f"{placed}\n{out[-500:]}")


def main():
    from make_demo import build_events

    tmp = Path(tempfile.mkdtemp(prefix="ledger-selftest-"))
    root = tmp / "books"
    subprocess.run([sys.executable, str(TOOLS / "make_demo.py"), str(root)], capture_output=True, text=True, check=True)
    unit_tests(root)

    # ---- importing from a messy folder: flatten the demo's statements, keep one file that has
    #      no account number in a named folder, add a duplicate, then sort them back into 00_raw
    src = tmp / "messy source" / "Bank Statements"
    (src / "Demo Bank" / "Everyday").mkdir(parents=True)
    original = {}
    for f in (root / "00_raw").rglob("*.*"):
        original[f.name] = f.parent.relative_to(root / "00_raw").as_posix()
        dest = src / "Demo Bank" / "Everyday" if f.name.startswith("export") else src
        shutil.copy2(f, dest / f.name)
    shutil.copy2(next((root / "00_raw" / "DemoBank" / "Business").glob("*.pdf")), src / "copy of a statement.pdf")
    (src / "notes.txt").write_text("not a statement")
    shutil.rmtree(root / "00_raw")
    (root / "00_raw").mkdir()
    code, out = run(root, "import_statements.py", str(src), "--apply")
    placed = {f.name: f.parent.relative_to(root / "00_raw").as_posix() for f in (root / "00_raw").rglob("*.*")}
    check("import_statements puts every statement in its account folder (transfer lines don't mislead it)",
          code == 0 and placed == original, f"{out[-400:]} diff={set(placed.items()) ^ set(original.items())}")
    code, out = run(root, "import_statements.py", str(src), "--apply")
    check("import_statements is safe to re-run (nothing copied twice)",
          sum(1 for _ in (root / "00_raw").rglob("*.*")) == len(original))
    import_by_name_test(tmp)
    import_two_accounts_test(tmp)
    run(root, "inventory.py")

    code, out = run(root, "parse_all.py")
    check("all demo statements parse", code == 0, out[-300:])
    code, out = run(root, "run_all.py")
    check("full pipeline runs on the demo", code == 0, out[-500:])

    truth = collections.Counter((a, e[0].isoformat(), e[2]) for a, es in build_events().items() for e in es)
    led = collections.Counter((r["account_id"], r["date"], Decimal(r["amount"])) for r in rows(root / "output" / "master_ledger.csv"))
    check("ledger equals ground truth (every row, date and amount; duplicates removed)", truth == led,
          f"missing {list((truth - led).items())[:3]} extra {list((led - truth).items())[:3]}")
    m = rows(root / "03_data" / "transfer_matches.csv")
    types = collections.Counter(x["type"] for x in m)
    check("transfers: 9 owner drawings + 11 internal, 1 crosses 30 June, 2 flagged ambiguous",
          types == {"Owner drawing": 9, "Internal transfer": 11} and sum(1 for x in m if x["crosses_fy"]) == 1
          and sum(1 for x in m if x["note"].startswith("ambiguous")) == 2, str(types))
    cl = rows(root / "03_data" / "classified.csv")
    cash = [x for x in cl if "CASH DEPOSIT" in x["original_description"]]
    check("cash deposit goes to review", cash and cash[0]["review_status"] == "Needs review")
    loans = {x["counterparty"] for x in cl if x["type"] in ("Loan in", "Loan out")}
    check("loans attributed to the right people", loans == {"Alex Nguyen", "Sam Lee"}, str(loans))
    ps = rows(root / "03_data" / "payees.csv")
    st = {x["payee_key"]: x["status"] for x in ps}
    check("payee status separates own transfers and people from payees needing rules",
          st.get("TRANSFER FROM XX4321 J CITIZEN") == "own-transfer" and st.get("OSKO PAYMENT TO ALEX NGUYEN") == "person"
          and st.get("BUNNINGS 7722 PENRITH") == "new")

    # ---- adversarial: a sign error in one extracted row
    x = root / "02_extracted" / "S005.csv"
    backup = x.read_text(encoding="utf-8-sig")
    data = rows(x)
    data[4]["amount"] = str(-Decimal(data[4]["amount"]))
    write_rows(x, data)
    code, out = run(root, "reconcile.py")
    errs = rows(root / "review" / "reconcile_row_errors.csv")
    check("sign error: reconcile FAILs and names the exact row", code == 1 and "S005 FAIL" in out
          and errs and errs[0]["seq"] == data[4]["seq"], out[-300:])
    code, out = run(root, "combine.py")
    check("combine refuses while a statement does not balance", code == 1)
    x.write_text(backup, encoding="utf-8-sig")

    # ---- adversarial: day/month swap
    data = rows(x)
    d = dt.date.fromisoformat(data[2]["date"])
    data[2]["date"] = dt.date(d.year, d.day, d.month).isoformat() if d.day <= 12 else "2022-01-08"
    write_rows(x, data)
    code, out = run(root, "reconcile.py")
    check("day/month swap: flagged as dates outside the period", code == 1 and "dates outside period" in out, out[-300:])
    x.write_text(backup, encoding="utf-8-sig")

    # ---- adversarial: a missing statement
    inv = root / "config" / "inventory.csv"
    inv_backup = inv.read_text(encoding="utf-8-sig")
    data = rows(inv)
    for r in data:
        if r["statement_id"] == "S005":
            r["include"] = "N"
    write_rows(inv, data)
    code, out = run(root, "reconcile.py")
    check("missing statement: continuity BREAK and MISSING months reported", code == 1 and "BREAK" in out, out[-300:])
    inv.write_text(inv_backup, encoding="utf-8-sig")

    # ---- adversarial: overlapping CSV export that disagrees with the PDF but balances on its own
    x7 = root / "02_extracted" / "S007.csv"
    b7 = x7.read_text(encoding="utf-8-sig")
    data = rows(x7)
    delta = Decimal("1.00")
    data[3]["amount"] = str(Decimal(data[3]["amount"]) - delta)
    for r in data[3:]:
        r["balance_shown"] = str(Decimal(r["balance_shown"]) - delta)
    write_rows(x7, data)
    meta7 = root / "02_extracted" / "S007.meta.json"
    mb = meta7.read_text()
    import json
    mj = json.loads(mb)
    mj["closing_balance"] = str(Decimal(mj["closing_balance"]) - delta)
    meta7.write_text(json.dumps(mj))
    code, out = run(root, "reconcile.py")
    code2, out2 = run(root, "combine.py")
    check("overlapping sources that disagree: combine stops with overlap conflicts",
          code == 0 and code2 == 1 and "overlapping" in out2, out2[-300:])
    x7.write_text(b7, encoding="utf-8-sig")
    meta7.write_text(mb)
    run(root, "run_all.py")

    # ---- owner review round trip
    from openpyxl import load_workbook
    q = root / "review" / "review_queue.xlsx"
    wb = load_workbook(q)
    ws = wb["Groups"]
    head = [c.value for c in ws[1]]
    col = {h: i + 1 for i, h in enumerate(head)}
    answers = {"BUNNINGS 7722 PENRITH": ("Expense", "Shopping and household", "Personal"),
               "DAN MURPHYS 555 PENRITH": ("Expense", "Dining and takeaway", "Personal"),
               "CASH DEPOSIT BRANCH PARRAMATTA": ("Business income", "Sales and fees", "Business"),
               "JB HI FI 0123 PARRAMATTA": ("Expense", "Equipment purchases", "Business"),
               "BPAY ATO TAX OFFICE PAYMENTS": ("Tax", "Tax payment", "Personal"),
               "INTERNET TRANSFER TO XX3456": ("Internal transfer", "", ""),
               "TRANSFER FROM J CITIZEN": ("Internal transfer", "", "")}
    for r in range(2, ws.max_row + 1):
        key = ws.cell(r, col["key"]).value
        if key in answers:
            t, cat, bp = answers[key]
            ws.cell(r, col["decide_type"], t)
            ws.cell(r, col["decide_category"], cat or None)
            ws.cell(r, col["decide_business_personal"], bp or None)
        elif key and key.startswith("AMAZON"):
            ws.cell(r, col["decide_ask_accountant"], "Y")
            ws.cell(r, col["decide_note"], "work laptop bag or personal?")
    wb.save(q)
    code, out = run(root, "classify.py")
    check("classify refuses to overwrite a filled-in review list", code == 1 and "apply_review" in out)
    code, out = run(root, "run_all.py")
    cl = rows(root / "03_data" / "classified.csv")
    open_ = [x for x in cl if x["review_status"] == "Needs review"]
    check("after the owner's answers nothing is left to review", code == 0 and not open_,
          f"{len(open_)} left: {[x['payee_key'] for x in open_][:5]} {out[-300:]}")
    amb = [x for x in cl if x["match_id"] and "+D" in x["classified_by"]]
    check("confirmed ambiguous transfers keep their pair", len(amb) >= 4, str(len(amb)))
    wb = load_workbook(root / "output" / "FY2023.xlsx")
    check("FY2023 pack status is FINAL after review", str(wb["README"]["A2"].value).startswith("Status: FINAL"),
          wb["README"]["A2"].value)

    # ---- tampering after classification must block the build
    cf = root / "03_data" / "classified.csv"
    data = rows(cf)
    write_rows(cf, data[:-1])
    code, out = run(root, "build_outputs.py")
    check("a row lost after classification blocks the build (check A)", code == 1 and "check A" in out, out[-200:])

    ok = all(r[1] for r in RESULTS)
    print(f"\n{sum(1 for r in RESULTS if r[1])}/{len(RESULTS)} passed")
    if ok:
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print(f"Test project kept for inspection: {root}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
