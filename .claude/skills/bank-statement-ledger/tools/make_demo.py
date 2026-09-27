"""Build a demo bookkeeping project from made-up statements, to watch the whole pipeline
work before touching real data (and to regression-test the scripts after any change).

  pip install pdfplumber openpyxl reportlab     # reportlab is only needed for the demo
  python <skill>/tools/make_demo.py /tmp/demo-books
  cd /tmp/demo-books
  python scripts/parse_all.py && python scripts/run_all.py

Everything is fictional. Inside:
  Demo Bank   - PDF statements (Everyday + Business), no year on dates, wrapped descriptions,
                brought/carried forward lines, CR balances
  Sample Bank - CSV savings exports, newest transaction first, running balance
  Other Bank  - CSV with debit/credit columns and NO balance (needs config/balance_anchors.csv)
  An extra CSV export that overlaps a PDF month (duplicates to remove)
  Monthly owner drawings, cross-bank transfers, one transfer across 30 June, two identical
  $100 transfers on the same day (ambiguous), loans with two friends (one only ever pays in),
  a cash deposit, an ATO payment, a large equipment purchase, and payees with no rule.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import json
import random
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from init_project import init  # noqa: E402

D = Decimal
ACCTS = {
    "DEMO-EVE-5678": dict(bank="Demo Bank", name="Everyday", last4="5678", number="1234 5678", use="personal",
                          folder="DemoBank/Everyday", prefix="_example", opening=D("1200.00")),
    "DEMO-BUS-4321": dict(bank="Demo Bank", name="Business", last4="4321", number="8765 4321", use="business",
                          folder="DemoBank/Business", prefix="_example", opening=D("5000.00")),
    "SMP-SAV-9012": dict(bank="Sample Bank", name="Savings", last4="9012", number="4455 9012", use="personal",
                         folder="SampleBank/Savings", prefix="_example", opening=D("10000.00")),
    "OTH-EVE-3456": dict(bank="Other Bank", name="Everyday", last4="3456", number="7788 3456", use="personal",
                         folder="OtherBank/Everyday", prefix="", opening=D("400.00")),
}
QUARTERS = [(dt.date(2022, 4, 1), dt.date(2022, 6, 30)), (dt.date(2022, 7, 1), dt.date(2022, 9, 30)),
            (dt.date(2022, 10, 1), dt.date(2022, 12, 31))]


def build_events():
    rng = random.Random(7)
    ev = {k: [] for k in ACCTS}

    def add(acct, date, desc, amount):
        ev[acct].append((date, desc, D(amount)))

    def cents(lo, hi):
        return D(rng.randint(lo * 100, hi * 100)) / 100

    for i, month in enumerate(range(4, 13)):
        y, last = 2022, calendar.monthrange(2022, month)[1]
        d = lambda day: dt.date(y, month, day)  # noqa: E731
        add("DEMO-EVE-5678", d(1), "RENT PAYMENT RAY WHITE PENRITH", "-1100.00")
        add("DEMO-BUS-4321", d(5), f"DIRECT CREDIT ACME PTY LTD INV {1001 + i}", "2200.00")
        add("DEMO-BUS-4321", d(8), "VISA PURCHASE CANVA* I0341122 SYDNEY AU CARD xx9911", "-17.99")
        add("OTH-EVE-3456", d(9), "BUNNINGS 7722 PENRITH", -cents(30, 80))
        add("DEMO-BUS-4321", d(12), "TELSTRA CORP LTD BPAY", "-89.00")
        add("DEMO-EVE-5678", d(14), "NETFLIX.COM MELBOURNE AU", "-16.99")
        add("DEMO-BUS-4321", d(rng.randint(10, 20)), "EFTPOS OFFICEWORKS 0423 PARRAMATTA NSW AU", -cents(20, 150))
        add("DEMO-BUS-4321", d(18), "DIRECT CREDIT BRIGHT IDEAS CO", "950.00")
        for day in (3, 17):
            add("DEMO-EVE-5678", d(day), "EFTPOS SHELL COLES EXPRESS 2201 PENRITH NSW", -cents(50, 90))
        for day in range(1, last + 1):
            if d(day).weekday() == 5:
                add("DEMO-EVE-5678", d(day), "VISA PURCHASE WOOLWORTHS 1234 SYDNEY AU", -cents(60, 180))
        add("DEMO-BUS-4321", d(25), "INTERNET TRANSFER TO XX5678 J CITIZEN", "-2500.00")
        add("DEMO-EVE-5678", d(25), "TRANSFER FROM XX4321 J CITIZEN", "2500.00")
        if month == 6:  # transfer that leaves on 30 June and arrives on 1 July: crosses the FY
            add("DEMO-EVE-5678", d(30), "OSKO PAYMENT TO J CITIZEN XX9012", "-500.00")
            add("SMP-SAV-9012", dt.date(2022, 7, 1), "TRANSFER FROM J CITIZEN", "500.00")
        else:
            add("DEMO-EVE-5678", d(26), "OSKO PAYMENT TO J CITIZEN XX9012", "-300.00")
            add("SMP-SAV-9012", d(27), "TRANSFER FROM J CITIZEN", "300.00")
        add("SMP-SAV-9012", d(last), "CREDIT INTEREST", cents(12, 20))
        add("DEMO-BUS-4321", d(last), "MONTHLY ACCOUNT FEE", "-10.00")

    add("DEMO-EVE-5678", dt.date(2022, 5, 10), "OSKO PAYMENT TO ALEX NGUYEN", "-20.00")
    add("DEMO-EVE-5678", dt.date(2022, 6, 2), "TRANSFER FROM ALEX NGUYEN", "20.00")
    add("DEMO-EVE-5678", dt.date(2022, 8, 15), "OSKO PAYMENT TO ALEX NGUYEN", "-50.00")
    add("DEMO-EVE-5678", dt.date(2022, 9, 20), "TRANSFER FROM ALEX NGUYEN", "30.00")
    add("DEMO-EVE-5678", dt.date(2022, 7, 22), "PAYID PAYMENT FROM SAM LEE", "50.00")
    add("DEMO-EVE-5678", dt.date(2022, 11, 11), "PAYID PAYMENT FROM SAM LEE", "80.00")
    add("DEMO-EVE-5678", dt.date(2022, 7, 19),
        "VISA PURCHASE AMAZON MARKETPLACE AU SYDNEY SOUTH NSW AU CARD xx9911 FOREIGN TXN", "-64.50")
    for _ in range(2):  # two identical transfers on the same day: the matcher must flag ambiguity
        add("DEMO-EVE-5678", dt.date(2022, 10, 10), "INTERNET TRANSFER TO XX3456", "-100.00")
        add("OTH-EVE-3456", dt.date(2022, 10, 11), "TRANSFER FROM J CITIZEN", "100.00")
    add("DEMO-BUS-4321", dt.date(2022, 9, 14), "CASH DEPOSIT BRANCH PARRAMATTA", "300.00")
    add("DEMO-BUS-4321", dt.date(2022, 10, 21), "BPAY ATO TAX OFFICE PAYMENTS", "-1200.00")
    add("DEMO-BUS-4321", dt.date(2022, 8, 3), "VISA PURCHASE JB HI FI 0123 PARRAMATTA NSW", "-2399.00")
    add("OTH-EVE-3456", dt.date(2022, 11, 4), "DAN MURPHYS 555 PENRITH", "-45.00")
    for k in ev:
        ev[k].sort(key=lambda e: e[0])  # stable: same-day order is kept
    return ev


def balances(acct, events, start, end):
    bal = ACCTS[acct]["opening"] + sum((e[2] for e in events if e[0] < start), D("0"))
    rows = [e for e in events if start <= e[0] <= end]
    return bal, rows


def wrap(text, width=34):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur] if cur else lines


def draw_pdf(path, acct, start, end, opening, rows):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    a = ACCTS[acct]
    closing = opening + sum((r[2] for r in rows), D("0"))
    fmt = lambda v: f"{abs(v):,.2f} {'CR' if v >= 0 else 'DR'}"  # noqa: E731
    items, bal = [], opening
    for d, desc, amt in rows:
        bal += amt
        items.append((d, wrap(desc), amt, bal))
    # paginate: 44 lines per page after the first page's header block
    pages, cur, room = [], [], 34
    for it in items:
        need = len(it[1])
        if need > room - 1:
            pages.append(cur)
            cur, room = [], 46
        cur.append(it)
        room -= need
    pages.append(cur)

    c = canvas.Canvas(str(path), pagesize=A4)
    run = opening
    for pno, page in enumerate(pages, 1):
        y = 800
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "DEMO BANK")
        c.setFont("Helvetica", 9)
        if pno == 1:
            for line in [f"{a['name']} Account Statement", "Customer: J CITIZEN",
                         f"BSB 062-000   Account number {a['number']}",
                         f"Statement period {start:%d %b %Y} to {end:%d %b %Y}",
                         f"Opening balance ${opening:,.2f} CR", f"Closing balance ${closing:,.2f} CR"]:
                y -= 14
                c.drawString(40, y, line)
        else:
            y -= 14
            c.drawString(40, y, f"{a['name']} Account Statement (continued)")
        y -= 30
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Date")
        c.drawString(90, y, "Transaction details")
        c.drawRightString(400, y, "Debit")
        c.drawRightString(480, y, "Credit")
        c.drawRightString(560, y, "Balance")
        c.setFont("Helvetica", 9)
        y -= 14
        c.drawString(90, y, "OPENING BALANCE" if pno == 1 else "BALANCE BROUGHT FORWARD")
        c.drawRightString(560, y, fmt(run))
        for d, lines, amt, b in page:
            y -= 13
            c.drawString(40, y, f"{d:%d %b}")
            c.drawString(90, y, lines[0])
            c.drawRightString(400 if amt < 0 else 480, y, f"{abs(amt):,.2f}")
            c.drawRightString(560, y, fmt(b))
            for extra in lines[1:]:
                y -= 13
                c.drawString(90, y, extra)
            run = b
        y -= 13
        c.drawString(90, y, "CLOSING BALANCE" if pno == len(pages) else "BALANCE CARRIED FORWARD")
        c.drawRightString(560, y, fmt(run))
        c.drawString(40, 30, f"Page {pno} of {len(pages)}")
        c.showPage()
    c.save()


def write_example_csv(path, opening, rows):
    out, bal = [], opening
    for d, desc, amt in rows:
        bal += amt
        out.append([f"{d:%d/%m/%Y}", desc, f"{amt:.2f}", f"{bal:.2f}"])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Amount", "Balance"])
        w.writerows(reversed(out))  # newest first, like many bank exports


def write_other_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for d, desc, amt in rows:
            w.writerow([f"{d:%d %b %Y}", desc, f"{-amt:.2f}" if amt < 0 else "", f"{amt:.2f}" if amt > 0 else ""])


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    root = Path(sys.argv[1]).expanduser().resolve()
    if (root / "00_raw").exists() and any((root / "00_raw").rglob("*.*")):
        print(f"{root} already has statements - choose an empty folder")
        sys.exit(1)
    init(root)
    ev = build_events()
    anchors = []
    for acct, a in ACCTS.items():
        folder = root / "00_raw" / a["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        for qs, qe in QUARTERS:
            opening, rows = balances(acct, ev[acct], qs, qe)
            name = f"{a['bank'].replace(' ', '')}_{a['number'].replace(' ', '')}_{qs:%Y%m}"
            if a["bank"] == "Demo Bank":
                draw_pdf(folder / f"{name}.pdf", acct, qs, qe, opening, rows)
            elif a["bank"] == "Sample Bank":
                write_example_csv(folder / f"{name}.csv", opening, rows)
            else:
                write_other_csv(folder / f"{name}.csv", rows)
                closing = opening + sum((r[2] for r in rows), D("0"))
                anchors.append((f"{name}.csv", opening, closing))
    aug0, aug_rows = balances("DEMO-EVE-5678", ev["DEMO-EVE-5678"], dt.date(2022, 8, 1), dt.date(2022, 8, 31))
    write_example_csv(root / "00_raw" / "DemoBank" / "Everyday" / "export_aug_2022.csv", aug0, aug_rows)

    with open(root / "config" / "accounts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["account_id", "bank", "account_name", "last4", "default_use", "opened", "closed", "raw_folder", "parser_prefix"])
        for aid, a in ACCTS.items():
            w.writerow([aid, a["bank"], a["name"], a["last4"], a["use"], "2022-04-01", "2022-12-31", a["folder"], a["prefix"]])
    cfg = json.loads((root / "config" / "project.json").read_text())
    cfg.update(first_fy="FY2022", last_fy="FY2023", own_names=["J CITIZEN"])
    (root / "config" / "project.json").write_text(json.dumps(cfg, indent=2))
    (root / "scripts" / "parsers" / "otherbank_csv.py").write_text(
        '"""Demo: Other Bank CSV - no header; date, narrative, debit (positive = money out), credit; no balance."""\n'
        "from parsers._generic_csv import parse_csv\n\n"
        'MAPPING = {"has_header": False, "date": 0, "description": [1], "debit": 2, "credit": 3,\n'
        '           "debit_is_positive": True, "balance": None}\n\n\n'
        "def parse(path, ctx):\n    return parse_csv(path, ctx, MAPPING)\n")
    with open(root / "config" / "rules.csv", "a", newline="") as f:
        w = csv.writer(f)
        for r in [
            ("R0101", "contains", "ACME PTY LTD", "in", "any", "Business income", "Sales and fees", "Business", "", "high", "Customer payment"),
            ("R0102", "contains", "BRIGHT IDEAS", "in", "any", "Business income", "Sales and fees", "Business", "", "high", "Customer payment"),
            ("R0103", "startswith", "CANVA", "out", "any", "Expense", "Software and subscriptions", "Business", "", "high", "Design software"),
            ("R0104", "contains", "TELSTRA", "out", "any", "Expense", "Phone and internet", "Mixed", "60", "high", "Phone, 60% business per DECISIONS.md"),
            ("R0105", "contains", "OFFICEWORKS", "out", "any", "Expense", "Office supplies and postage", "account", "", "high", "Stationery"),
            ("R0106", "contains", "JB HI FI", "out", "any", "Expense", "Equipment purchases", "Business", "", "medium", "Electronics - could be personal"),
            ("R0107", "contains", "WOOLWORTHS", "out", "any", "Expense", "Groceries", "Personal", "", "high", "Supermarket"),
            ("R0108", "contains", "SHELL", "out", "any", "Expense", "Fuel and transport", "Personal", "", "high", "Fuel"),
            ("R0109", "contains", "NETFLIX", "out", "any", "Expense", "Subscriptions and entertainment", "Personal", "", "high", "Streaming"),
            ("R0110", "contains", "RAY WHITE", "out", "any", "Expense", "Housing", "Personal", "", "high", "Home rent"),
            ("R0111", "contains", "AMAZON", "out", "any", "Expense", "Shopping and household", "Personal", "", "medium", "Online shopping - could be business"),
        ]:
            w.writerow(r)
    with open(root / "config" / "people.csv", "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Alex Nguyen", "contains", "ALEX NGUYEN", "friend", "Loan", "lends small amounts back and forth"])
        w.writerow(["Sam Lee", "contains", "SAM LEE", "friend", "Loan", "pays me back for things"])

    subprocess.run([sys.executable, str(root / "scripts" / "inventory.py")], cwd=root, check=False)
    inv = {r["original_name_masked"]: r["statement_id"] for r in csv.DictReader(open(root / "config" / "inventory.csv", encoding="utf-8-sig"))}
    from importlib import util
    spec = util.spec_from_file_location("common", root / "scripts" / "common.py")
    common = util.module_from_spec(spec)
    spec.loader.exec_module(common)
    with open(root / "config" / "balance_anchors.csv", "a", newline="") as f:
        w = csv.writer(f)
        for fname, o, cl in anchors:
            w.writerow([inv[common.mask(fname)], f"{o:.2f}", f"{cl:.2f}", "copied from the Other Bank PDF statement"])
    print(f"\nDemo project ready: {root}")
    print("Next:  cd " + str(root) + "  &&  python scripts/parse_all.py  &&  python scripts/run_all.py")


if __name__ == "__main__":
    main()
