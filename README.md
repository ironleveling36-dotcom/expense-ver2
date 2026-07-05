# 💰 Telegram Expense Tracker Bot (INR)

A production-ready, modular **Telegram Expense Tracker Bot** built with
**pyTelegramBotAPI (TeleBot)** and **MongoDB**, optimised for **Railway**
deployment. Fully inline-button driven, tailored for Indian users (₹).

---

## ✨ Features

- **Expenses** – add, categorize (default + custom), payment mode (Cash/Card/UPI),
  notes, list, view, delete, budget alerts.
- **Income** – multiple sources (Salary, Business, Investment, etc.), notes, listing.
- **Borrow & Lending** – track who you borrowed from / lent to, partial repayments,
  remaining balance, payment history, due dates, overdue tracking, summaries.
- **Friends / Contacts** – profiles with phone, UPI, notes, per-friend balance,
  quick Borrow / Lend / History / Reminder actions.
- **Ledger** – credit/debit entries with running balance and statement.
- **Reports** – daily / weekly / monthly / yearly, category, payment-mode,
  profit/loss and savings reports.
- **Bills** – add, categorize, due dates, paid/unpaid, auto-log paid bills as
  expenses, due-soon reminders.
- **Savings Goals** – targets, contributions, progress bar, deadlines.
- **Budgets** – daily / weekly / monthly / category limits with 50/75/90/100%
  alerts.
- **Reminders** – one-time and recurring (daily/weekly/monthly) via a background
  scheduler.
- **Dashboard** – wallet balance, today/month spend, income, savings, borrowed,
  lent, pending bills, reminders, recent transactions.
- **Export** – CSV, Excel (multi-sheet), JSON (full backup), PDF statement.
- **Settings** – currency, timezone, notifications, report schedule.
- **Admin Panel** – users, block/unblock, statistics, health, storage, audit
  logs, maintenance mode, broadcast.
- **Security** – Telegram-ID auth, admin whitelist, role-based access, input
  validation, rate limiting, soft deletes, secrets via env vars, auto restart.

---

## 🏗 Project Structure

```
expense_tracker_bot/
├── bot.py                  # entry point
├── config.py               # env-based configuration
├── requirements.txt
├── Procfile / railway.json / nixpacks.toml / runtime.txt
├── .env.example
├── database/
│   ├── db.py               # MongoDB connection + indexes
│   └── models.py           # repositories / CRUD
├── keyboards/
│   └── keyboards.py        # all inline keyboards
├── handlers/               # one module per feature
│   ├── common.py           # access control, safe edits, rate limiting
│   ├── router.py           # multi-step text-flow dispatcher
│   ├── start.py expense.py income.py borrow_lending.py friends.py
│   ├── ledger.py reports.py bills.py savings.py reminders.py
│   ├── dashboard.py budget.py settings.py export.py admin.py
│   └── fallback.py
├── services/
│   ├── reminder_service.py # background scheduler
│   ├── report_service.py   # report computation
│   └── export_service.py   # CSV/Excel/JSON/PDF
└── utils/
    ├── helpers.py states.py logger.py
```

---

## 🚀 Deployment on Railway

1. **Create the bot** with [@BotFather](https://t.me/BotFather) → get `BOT_TOKEN`.
2. **Create a free MongoDB Atlas cluster** → get the connection string
   (`MONGO_URI`). Whitelist `0.0.0.0/0` in Atlas Network Access.
3. **Get your Telegram ID** from [@userinfobot](https://t.me/userinfobot) →
   set as `ADMIN_IDS`.
4. **Push this repo to GitHub.**
5. On [Railway](https://railway.app): *New Project → Deploy from GitHub repo*.
6. Add the environment variables (see `.env.example`):
   - `BOT_TOKEN`, `MONGO_URI`, `DB_NAME`, `ADMIN_IDS` (required)
   - optional tuning vars.
7. Railway auto-detects the `Procfile` / `railway.json` and starts `python bot.py`.

### Moving to a new Railway account without losing data
Because MongoDB Atlas is **independent of Railway**, migration is trivial:
1. Deploy this same GitHub repo on the new Railway account.
2. Set the **same** `MONGO_URI` (and other env vars).
3. Done — all user data persists in Atlas.

---

## 🖥 Local Development

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env with your values
python bot.py
```

Requires a running MongoDB (local or Atlas).

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram bot token from BotFather |
| `MONGO_URI` | ✅ | MongoDB / Atlas connection string |
| `DB_NAME` | – | Database name (default `expense_tracker`) |
| `ADMIN_IDS` | – | Comma-separated admin Telegram IDs |
| `DEFAULT_CURRENCY` | – | Default currency symbol (default `₹`) |
| `DEFAULT_TIMEZONE` | – | Default timezone (default `Asia/Kolkata`) |
| `MAINTENANCE_MODE` | – | `true`/`false` |
| `RATE_LIMIT_MESSAGES` / `RATE_LIMIT_WINDOW` | – | Rate limiting |
| `REMINDER_INTERVAL` | – | Scheduler poll interval (seconds) |
| `LOG_LEVEL` | – | `INFO`, `DEBUG`, etc. |

---

## 🧭 Usage

Send `/start` to your bot and use the inline menu. Everything is button-driven;
type values only when prompted (amounts, names, dates). Use `/cancel` to abort a
step and `/help` for tips.

---

## 📝 Notes

- Conversation state is in-memory (single instance) and rebuilds from the menu
  after a restart.
- All records use **soft delete** (`deleted` flag) for backup safety.
- Collections are indexed automatically on first connect.
