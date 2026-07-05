"""
Data-access layer (repositories).

Every collection gets small, focused helper functions with automatic
timestamps and soft-delete support. Handlers should use these functions
instead of touching pymongo directly.
"""
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING, ASCENDING

from database.db import database
from utils.helpers import utcnow


def _oid(value):
    """Coerce a value to an ObjectId, returning None if invalid."""
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def _col(name):
    return database.collection(name)


# --------------------------------------------------------------------------- #
# Users & settings
# --------------------------------------------------------------------------- #
def get_or_create_user(user_id, first_name="", username=""):
    users = _col("users")
    user = users.find_one({"user_id": user_id})
    if user:
        users.update_one(
            {"user_id": user_id},
            {"$set": {"last_seen": utcnow(), "first_name": first_name,
                      "username": username}},
        )
        return user
    doc = {
        "user_id": user_id,
        "first_name": first_name,
        "username": username,
        "role": "user",
        "blocked": False,
        "created_at": utcnow(),
        "last_seen": utcnow(),
        "settings": {
            "currency": "₹",
            "timezone": "Asia/Kolkata",
            "notifications": True,
            "language": "en",
            "report_schedule": "monthly",
        },
    }
    users.insert_one(doc)
    return doc


def get_user(user_id):
    return _col("users").find_one({"user_id": user_id})


def update_user_setting(user_id, key, value):
    return _col("users").update_one(
        {"user_id": user_id},
        {"$set": {"settings.%s" % key: value, "updated_at": utcnow()}},
    )


def get_user_settings(user_id):
    user = get_user(user_id)
    if not user:
        return {}
    return user.get("settings", {})


def set_user_blocked(user_id, blocked):
    return _col("users").update_one(
        {"user_id": user_id}, {"$set": {"blocked": blocked, "updated_at": utcnow()}}
    )


def set_user_role(user_id, role):
    return _col("users").update_one(
        {"user_id": user_id}, {"$set": {"role": role, "updated_at": utcnow()}}
    )


def list_users(limit=100, skip=0):
    return list(_col("users").find().sort("created_at", DESCENDING).skip(skip).limit(limit))


def count_users():
    return _col("users").count_documents({})


def count_active_users(since):
    return _col("users").count_documents({"last_seen": {"$gte": since}})


# --------------------------------------------------------------------------- #
# Generic soft-delete CRUD factory
# --------------------------------------------------------------------------- #
def _insert(collection, user_id, data):
    doc = dict(data)
    doc["user_id"] = user_id
    doc["created_at"] = utcnow()
    doc["updated_at"] = utcnow()
    doc["deleted"] = False
    result = _col(collection).insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def _get(collection, user_id, item_id):
    oid = _oid(item_id)
    if oid is None:
        return None
    return _col(collection).find_one(
        {"_id": oid, "user_id": user_id, "deleted": {"$ne": True}}
    )


def _update(collection, user_id, item_id, changes):
    oid = _oid(item_id)
    if oid is None:
        return None
    changes = dict(changes)
    changes["updated_at"] = utcnow()
    return _col(collection).update_one(
        {"_id": oid, "user_id": user_id}, {"$set": changes}
    )


def _soft_delete(collection, user_id, item_id):
    oid = _oid(item_id)
    if oid is None:
        return None
    return _col(collection).update_one(
        {"_id": oid, "user_id": user_id},
        {"$set": {"deleted": True, "deleted_at": utcnow()}},
    )


def _list(collection, user_id, query=None, sort_field="date", limit=0, skip=0):
    q = {"user_id": user_id, "deleted": {"$ne": True}}
    if query:
        q.update(query)
    cursor = _col(collection).find(q).sort(
        [(sort_field, DESCENDING), ("_id", DESCENDING)]).skip(skip)
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)


def _sum(collection, user_id, query=None, field="amount"):
    q = {"user_id": user_id, "deleted": {"$ne": True}}
    if query:
        q.update(query)
    pipeline = [
        {"$match": q},
        {"$group": {"_id": None, "total": {"$sum": "$%s" % field}}},
    ]
    result = list(_col(collection).aggregate(pipeline))
    return result[0]["total"] if result else 0.0


# --------------------------------------------------------------------------- #
# Expenses
# --------------------------------------------------------------------------- #
def add_expense(user_id, amount, category, payment_mode="Cash", note="",
                date=None, attachment=None):
    return _insert("expenses", user_id, {
        "amount": amount,
        "category": category,
        "payment_mode": payment_mode,
        "note": note,
        "date": date or utcnow(),
        "attachment": attachment,
    })


def get_expense(user_id, item_id):
    return _get("expenses", user_id, item_id)


def update_expense(user_id, item_id, changes):
    return _update("expenses", user_id, item_id, changes)


def delete_expense(user_id, item_id):
    return _soft_delete("expenses", user_id, item_id)


def list_expenses(user_id, query=None, limit=0, skip=0):
    return _list("expenses", user_id, query, "date", limit, skip)


def sum_expenses(user_id, query=None):
    return _sum("expenses", user_id, query)


def count_expenses(user_id, query=None):
    q = {"user_id": user_id, "deleted": {"$ne": True}}
    if query:
        q.update(query)
    return _col("expenses").count_documents(q)


def expenses_by_category(user_id, start=None, end=None):
    match = {"user_id": user_id, "deleted": {"$ne": True}}
    if start or end:
        rng = {}
        if start:
            rng["$gte"] = start
        if end:
            rng["$lt"] = end
        match["date"] = rng
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"},
                    "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    return list(_col("expenses").aggregate(pipeline))


def expenses_by_payment_mode(user_id, start=None, end=None):
    match = {"user_id": user_id, "deleted": {"$ne": True}}
    if start or end:
        rng = {}
        if start:
            rng["$gte"] = start
        if end:
            rng["$lt"] = end
        match["date"] = rng
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$payment_mode", "total": {"$sum": "$amount"},
                    "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    return list(_col("expenses").aggregate(pipeline))


# --------------------------------------------------------------------------- #
# Income
# --------------------------------------------------------------------------- #
def add_income(user_id, amount, source, note="", date=None):
    return _insert("income", user_id, {
        "amount": amount,
        "source": source,
        "note": note,
        "date": date or utcnow(),
    })


def get_income(user_id, item_id):
    return _get("income", user_id, item_id)


def delete_income(user_id, item_id):
    return _soft_delete("income", user_id, item_id)


def list_income(user_id, query=None, limit=0, skip=0):
    return _list("income", user_id, query, "date", limit, skip)


def sum_income(user_id, query=None):
    return _sum("income", user_id, query)


def income_by_source(user_id, start=None, end=None):
    match = {"user_id": user_id, "deleted": {"$ne": True}}
    if start or end:
        rng = {}
        if start:
            rng["$gte"] = start
        if end:
            rng["$lt"] = end
        match["date"] = rng
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$source", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
    ]
    return list(_col("income").aggregate(pipeline))


# --------------------------------------------------------------------------- #
# Borrow (money the user borrowed from someone)
# --------------------------------------------------------------------------- #
def add_borrow(user_id, name, amount, purpose="", due_date=None):
    return _insert("borrow", user_id, {
        "name": name,
        "amount": amount,
        "paid": 0.0,
        "purpose": purpose,
        "date": utcnow(),
        "due_date": due_date,
        "status": "open",
        "payments": [],
    })


def get_borrow(user_id, item_id):
    return _get("borrow", user_id, item_id)


def list_borrow(user_id, query=None, limit=0, skip=0):
    return _list("borrow", user_id, query, "date", limit, skip)


def delete_borrow(user_id, item_id):
    return _soft_delete("borrow", user_id, item_id)


def add_borrow_payment(user_id, item_id, amount):
    doc = get_borrow(user_id, item_id)
    if not doc:
        return None
    paid = float(doc.get("paid", 0)) + amount
    status = "closed" if paid >= float(doc["amount"]) else "open"
    payment = {"amount": amount, "date": utcnow()}
    _col("borrow").update_one(
        {"_id": doc["_id"], "user_id": user_id},
        {"$set": {"paid": paid, "status": status, "updated_at": utcnow()},
         "$push": {"payments": payment}},
    )
    return get_borrow(user_id, item_id)


# --------------------------------------------------------------------------- #
# Lending (money the user lent to someone)
# --------------------------------------------------------------------------- #
def add_lending(user_id, name, amount, phone="", interest=0.0, due_date=None):
    return _insert("lending", user_id, {
        "name": name,
        "phone": phone,
        "amount": amount,
        "received": 0.0,
        "interest": interest,
        "date": utcnow(),
        "due_date": due_date,
        "status": "open",
        "payments": [],
    })


def get_lending(user_id, item_id):
    return _get("lending", user_id, item_id)


def list_lending(user_id, query=None, limit=0, skip=0):
    return _list("lending", user_id, query, "date", limit, skip)


def delete_lending(user_id, item_id):
    return _soft_delete("lending", user_id, item_id)


def add_lending_payment(user_id, item_id, amount):
    doc = get_lending(user_id, item_id)
    if not doc:
        return None
    received = float(doc.get("received", 0)) + amount
    status = "closed" if received >= float(doc["amount"]) else "open"
    payment = {"amount": amount, "date": utcnow()}
    _col("lending").update_one(
        {"_id": doc["_id"], "user_id": user_id},
        {"$set": {"received": received, "status": status, "updated_at": utcnow()},
         "$push": {"payments": payment}},
    )
    return get_lending(user_id, item_id)


# --------------------------------------------------------------------------- #
# Friends / contacts
# --------------------------------------------------------------------------- #
def add_friend(user_id, name, **fields):
    data = {
        "name": name,
        "nickname": fields.get("nickname", ""),
        "phone": fields.get("phone", ""),
        "upi": fields.get("upi", ""),
        "address": fields.get("address", ""),
        "notes": fields.get("notes", ""),
        "tags": fields.get("tags", []),
    }
    return _insert("friends", user_id, data)


def get_friend(user_id, item_id):
    return _get("friends", user_id, item_id)


def list_friends(user_id, limit=0, skip=0):
    return _list("friends", user_id, None, "name", limit, skip)


def update_friend(user_id, item_id, changes):
    return _update("friends", user_id, item_id, changes)


def delete_friend(user_id, item_id):
    return _soft_delete("friends", user_id, item_id)


def friend_balance(user_id, name):
    """Return (total_borrowed, total_lent) with this friend by name."""
    borrowed = _sum("borrow", user_id, {"name": name})
    lent = _sum("lending", user_id, {"name": name})
    return borrowed, lent


# --------------------------------------------------------------------------- #
# Ledger (credit/debit)
# --------------------------------------------------------------------------- #
def add_ledger_entry(user_id, entry_type, amount, category="", note="",
                     reference="", attachment=None):
    last = _col("ledger").find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        sort=[("date", DESCENDING), ("_id", DESCENDING)],
    )
    prev_balance = float(last.get("balance", 0)) if last else 0.0
    delta = amount if entry_type == "credit" else -amount
    balance = prev_balance + delta
    return _insert("ledger", user_id, {
        "type": entry_type,
        "amount": amount,
        "balance": balance,
        "category": category,
        "note": note,
        "reference": reference,
        "attachment": attachment,
        "date": utcnow(),
    })


def list_ledger(user_id, query=None, limit=0, skip=0):
    return _list("ledger", user_id, query, "date", limit, skip)


def ledger_balance(user_id):
    last = _col("ledger").find_one(
        {"user_id": user_id, "deleted": {"$ne": True}},
        sort=[("date", DESCENDING), ("_id", DESCENDING)],
    )
    return float(last.get("balance", 0)) if last else 0.0


# --------------------------------------------------------------------------- #
# Bills
# --------------------------------------------------------------------------- #
def add_bill(user_id, name, amount, category="Other", due_date=None, recurring=False):
    return _insert("bills", user_id, {
        "name": name,
        "amount": amount,
        "category": category,
        "due_date": due_date,
        "recurring": recurring,
        "status": "unpaid",
    })


def get_bill(user_id, item_id):
    return _get("bills", user_id, item_id)


def list_bills(user_id, query=None, limit=0, skip=0):
    return _list("bills", user_id, query, "due_date", limit, skip)


def mark_bill_paid(user_id, item_id):
    return _update("bills", user_id, item_id, {"status": "paid", "paid_at": utcnow()})


def delete_bill(user_id, item_id):
    return _soft_delete("bills", user_id, item_id)


# --------------------------------------------------------------------------- #
# Savings goals
# --------------------------------------------------------------------------- #
def add_savings(user_id, name, target, deadline=None):
    return _insert("savings", user_id, {
        "name": name,
        "target": target,
        "saved": 0.0,
        "deadline": deadline,
    })


def get_savings(user_id, item_id):
    return _get("savings", user_id, item_id)


def list_savings(user_id):
    return _list("savings", user_id, None, "created_at")


def add_savings_contribution(user_id, item_id, amount):
    doc = get_savings(user_id, item_id)
    if not doc:
        return None
    saved = float(doc.get("saved", 0)) + amount
    _update("savings", user_id, item_id, {"saved": saved})
    return get_savings(user_id, item_id)


def delete_savings(user_id, item_id):
    return _soft_delete("savings", user_id, item_id)


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #
def set_budget(user_id, period, amount, category=None):
    query = {"user_id": user_id, "period": period, "category": category}
    _col("budget").update_one(
        query,
        {"$set": {"amount": amount, "updated_at": utcnow()},
         "$setOnInsert": {"created_at": utcnow(), "deleted": False}},
        upsert=True,
    )
    return _col("budget").find_one(query)


def list_budgets(user_id):
    return list(_col("budget").find(
        {"user_id": user_id, "deleted": {"$ne": True}}))


def get_budget(user_id, period, category=None):
    return _col("budget").find_one(
        {"user_id": user_id, "period": period, "category": category,
         "deleted": {"$ne": True}})


def delete_budget(user_id, item_id):
    return _soft_delete("budget", user_id, item_id)


# --------------------------------------------------------------------------- #
# Reminders
# --------------------------------------------------------------------------- #
def add_reminder(user_id, text, next_run, repeat="once"):
    return _insert("reminders", user_id, {
        "text": text,
        "next_run": next_run,
        "repeat": repeat,
        "active": True,
    })


def list_reminders(user_id, only_active=True):
    q = {"active": True} if only_active else None
    return _list("reminders", user_id, q, "next_run")


def get_reminder(user_id, item_id):
    return _get("reminders", user_id, item_id)


def delete_reminder(user_id, item_id):
    return _soft_delete("reminders", user_id, item_id)


def due_reminders(now):
    return list(_col("reminders").find({
        "active": True,
        "deleted": {"$ne": True},
        "next_run": {"$lte": now},
    }))


def update_reminder(item_id, changes):
    oid = _oid(item_id)
    if oid is None:
        return None
    changes = dict(changes)
    changes["updated_at"] = utcnow()
    return _col("reminders").update_one({"_id": oid}, {"$set": changes})


# --------------------------------------------------------------------------- #
# Categories
# --------------------------------------------------------------------------- #
DEFAULT_EXPENSE_CATEGORIES = [
    "Food", "Groceries", "Transport", "Shopping", "Bills", "Rent",
    "Health", "Entertainment", "Education", "Travel", "Fuel", "Other",
]

DEFAULT_INCOME_SOURCES = [
    "Salary", "Business", "Investment", "Bonus", "Cashback",
    "Interest", "Freelance", "Other",
]


def get_categories(user_id):
    doc = _col("categories").find_one({"user_id": user_id})
    if not doc:
        return list(DEFAULT_EXPENSE_CATEGORIES)
    custom = doc.get("expense", [])
    merged = list(DEFAULT_EXPENSE_CATEGORIES)
    for c in custom:
        if c not in merged:
            merged.append(c)
    return merged


def add_category(user_id, name):
    _col("categories").update_one(
        {"user_id": user_id},
        {"$addToSet": {"expense": name}, "$setOnInsert": {"created_at": utcnow()}},
        upsert=True,
    )


# --------------------------------------------------------------------------- #
# Notifications
# --------------------------------------------------------------------------- #
def add_notification(user_id, text, kind="info"):
    return _insert("notifications", user_id, {"text": text, "kind": kind,
                                              "read": False})


# --------------------------------------------------------------------------- #
# Admin logs / audit
# --------------------------------------------------------------------------- #
def add_admin_log(admin_id, action, detail=""):
    _col("admin_logs").insert_one({
        "admin_id": admin_id,
        "action": action,
        "detail": detail,
        "created_at": utcnow(),
    })


def list_admin_logs(limit=20):
    return list(_col("admin_logs").find().sort("created_at", DESCENDING).limit(limit))
