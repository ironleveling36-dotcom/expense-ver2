"""
Export service: generate CSV, Excel, JSON and PDF files from a user's data.

Files are written to a temporary directory and their paths returned so the
caller can send them via Telegram and then clean them up.
"""
import csv
import json
import os
import tempfile
from datetime import datetime

from database import models
from utils.helpers import fmt_datetime


def _collect(user_id):
    """Gather all of a user's data into a serialisable dict."""
    return {
        "expenses": models.list_expenses(user_id),
        "income": models.list_income(user_id),
        "borrow": models.list_borrow(user_id),
        "lending": models.list_lending(user_id),
        "friends": models.list_friends(user_id),
        "bills": models.list_bills(user_id),
        "savings": models.list_savings(user_id),
        "ledger": models.list_ledger(user_id),
        "reminders": models.list_reminders(user_id, only_active=False),
    }


def _json_default(obj):
    from bson import ObjectId
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _tmp_path(prefix, ext):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = tempfile.gettempdir()
    return os.path.join(directory, "%s_%s.%s" % (prefix, ts, ext))


def export_json(user_id):
    data = _collect(user_id)
    path = _tmp_path("backup", "json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, default=_json_default, ensure_ascii=False, indent=2)
    return path


def export_csv(user_id):
    """Export expenses + income to a single CSV file."""
    path = _tmp_path("transactions", "csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Type", "Amount", "Category/Source", "Payment/Note",
                         "Date"])
        for e in models.list_expenses(user_id):
            writer.writerow(["Expense", e.get("amount"), e.get("category", ""),
                             e.get("payment_mode", ""),
                             fmt_datetime(e.get("date"))])
        for i in models.list_income(user_id):
            writer.writerow(["Income", i.get("amount"), i.get("source", ""),
                             i.get("note", ""), fmt_datetime(i.get("date"))])
    return path


def export_excel(user_id):
    """Export all sections to a multi-sheet Excel workbook."""
    from openpyxl import Workbook

    data = _collect(user_id)
    wb = Workbook()
    first = True
    for section, rows in data.items():
        if first:
            ws = wb.active
            ws.title = section[:31]
            first = False
        else:
            ws = wb.create_sheet(section[:31])
        if not rows:
            ws.append(["No data"])
            continue
        keys = [k for k in rows[0].keys() if k not in ("_id",)]
        ws.append([str(k) for k in keys])
        for row in rows:
            ws.append([_cell(row.get(k)) for k in keys])
    path = _tmp_path("report", "xlsx")
    wb.save(path)
    return path


def _cell(value):
    from bson import ObjectId
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return fmt_datetime(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=_json_default)
    return value


def export_pdf(user_id, currency="₹"):
    """Generate a summary PDF report."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    from services import report_service

    path = _tmp_path("statement", "pdf")
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, "Expense Tracker Statement")
    y -= 10 * mm
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, "Generated: %s" % fmt_datetime(datetime.now()))
    y -= 12 * mm

    for period in ("month", "year"):
        data = report_service.summary(user_id, period)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, "%s Summary" % period.capitalize())
        y -= 7 * mm
        c.setFont("Helvetica", 10)
        for label, key in (("Income", "income"), ("Expense", "expense"),
                           ("Savings", "savings"), ("Balance", "balance")):
            c.drawString(25 * mm, y, "%s: %s%s" % (
                label, currency, round(data.get(key, 0), 2)))
            y -= 6 * mm
        y -= 6 * mm
        if y < 40 * mm:
            c.showPage()
            y = height - 25 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Recent Expenses")
    y -= 7 * mm
    c.setFont("Helvetica", 9)
    for e in models.list_expenses(user_id, limit=20):
        line = "%s  |  %s%s  |  %s" % (
            fmt_datetime(e.get("date")), currency, e.get("amount"),
            e.get("category", ""))
        c.drawString(25 * mm, y, line[:90])
        y -= 5.5 * mm
        if y < 20 * mm:
            c.showPage()
            y = height - 25 * mm
    c.save()
    return path


def generate(user_id, fmt, currency="₹"):
    if fmt == "csv":
        return export_csv(user_id)
    if fmt == "xlsx":
        return export_excel(user_id)
    if fmt == "json":
        return export_json(user_id)
    if fmt == "pdf":
        return export_pdf(user_id, currency)
    raise ValueError("Unknown format: %s" % fmt)
