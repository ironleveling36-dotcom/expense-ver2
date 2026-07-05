"""Report computation service."""
from datetime import timezone

from database import models
from utils.helpers import period_bounds, fmt_money


def _aware(dt):
    """Ensure a datetime is timezone-aware (assume UTC if naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def summary(user_id, period, tz_name=None):
    """Return a dict summary for a period ('day','week','month','year')."""
    start, end = period_bounds(period, tz_name=tz_name)
    date_q = {"date": {"$gte": start, "$lt": end}}
    income = models.sum_income(user_id, date_q)
    expense = models.sum_expenses(user_id, date_q)
    borrow = _range_sum(models.list_borrow(user_id), start, end, "amount")
    lend = _range_sum(models.list_lending(user_id), start, end, "amount")
    savings = expense_savings = income - expense
    return {
        "period": period,
        "start": start,
        "end": end,
        "income": income,
        "expense": expense,
        "savings": savings,
        "borrow": borrow,
        "lend": lend,
        "balance": income - expense,
    }


def _range_sum(items, start, end, field):
    total = 0.0
    for it in items:
        d = _aware(it.get("date"))
        if d and start <= d < end:
            total += float(it.get(field, 0))
    return total


def format_summary(user_id, period, currency, tz_name=None):
    data = summary(user_id, period, tz_name)
    titles = {"day": "Daily", "week": "Weekly", "month": "Monthly", "year": "Yearly"}
    lines = [
        "📊 <b>%s Report</b>\n" % titles.get(period, period.capitalize()),
        "💵 Income:   %s" % fmt_money(data["income"], currency),
        "💸 Expense:  %s" % fmt_money(data["expense"], currency),
        "💰 Savings:  %s" % fmt_money(data["savings"], currency),
        "🤝 Borrowed: %s" % fmt_money(data["borrow"], currency),
        "📤 Lent:     %s" % fmt_money(data["lend"], currency),
        "\n⚖️ Net Balance: <b>%s</b>" % fmt_money(data["balance"], currency),
    ]
    return "\n".join(lines)


def category_report(user_id, currency, tz_name=None):
    start, end = period_bounds("month", tz_name=tz_name)
    rows = models.expenses_by_category(user_id, start, end)
    if not rows:
        return "🏷 <b>Category Report</b>\n\nNo expenses this month."
    total = sum(r["total"] for r in rows)
    lines = ["🏷 <b>Category Report (This Month)</b>\n"]
    for r in rows:
        pct = (r["total"] / total * 100) if total else 0
        lines.append("• %s: %s (%.0f%%)" % (
            r["_id"] or "Other", fmt_money(r["total"], currency), pct))
    lines.append("\nTotal: <b>%s</b>" % fmt_money(total, currency))
    return "\n".join(lines)


def payment_mode_report(user_id, currency, tz_name=None):
    start, end = period_bounds("month", tz_name=tz_name)
    rows = models.expenses_by_payment_mode(user_id, start, end)
    if not rows:
        return "💳 <b>Payment Mode Report</b>\n\nNo expenses this month."
    lines = ["💳 <b>Payment Mode Report (This Month)</b>\n"]
    for r in rows:
        lines.append("• %s: %s (%d txns)" % (
            r["_id"] or "Other", fmt_money(r["total"], currency), r["count"]))
    return "\n".join(lines)


def profit_loss(user_id, currency, tz_name=None):
    start, end = period_bounds("month", tz_name=tz_name)
    date_q = {"date": {"$gte": start, "$lt": end}}
    income = models.sum_income(user_id, date_q)
    expense = models.sum_expenses(user_id, date_q)
    net = income - expense
    status = "🟢 Profit" if net >= 0 else "🔴 Loss"
    return ("💹 <b>Profit / Loss (This Month)</b>\n\n"
            "Income:  %s\nExpense: %s\n\n%s: <b>%s</b>") % (
        fmt_money(income, currency), fmt_money(expense, currency),
        status, fmt_money(abs(net), currency))


def savings_report(user_id, currency):
    goals = models.list_savings(user_id)
    if not goals:
        return "💰 <b>Savings Report</b>\n\nNo savings goals yet."
    lines = ["💰 <b>Savings Report</b>\n"]
    for g in goals:
        saved = float(g.get("saved", 0))
        target = float(g.get("target", 0))
        pct = (saved / target * 100) if target else 0
        lines.append("• %s: %s / %s (%.0f%%)" % (
            g["name"], fmt_money(saved, currency), fmt_money(target, currency), pct))
    return "\n".join(lines)
