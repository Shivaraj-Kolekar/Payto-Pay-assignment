# Playto Payout Engine

A payout engine where merchants can view their balance, request payouts to Indian bank accounts, and track payout status in real-time. Built as part of the Playto Pay engineering challenge.

## Tech Stack

- **Backend:** Django + Django REST Framework
- **Frontend:** React + Tailwind CSS + Vite
- **Database:** PostgreSQL (Neon)
- **Background Jobs:** Celery + Redis (Upstash)
- **Auth:** JWT (SimpleJWT)

## Project Structure

```
playto-payout/
├── backend/
│   ├── apps/
│   │   ├── merchants/    # Custom user model, dashboard serializer
│   │   ├── ledger/       # Credit/debit entries, balance calculation
│   │   └── payouts/      # Payout CRUD, Celery tasks, tests
│   ├── config/           # Django settings, Celery config, URLs
│   └── scripts/seed.py   # Seed script for test data
└── frontend/
    └── src/
        ├── api/client.ts       # Axios instance with JWT interceptor
        ├── pages/              # Login, Dashboard
        └── components/         # BalanceCard, PayoutForm, PayoutTable
```

## Setup (Local Development)

### Prerequisites

- Python 3.12+
- Node.js 18+ with pnpm
- PostgreSQL database (or Neon)
- Redis instance (or Upstash)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
DATABASE_URL=postgresql://user:pass@host/dbname
REDIS_URL=rediss://default:token@host:6379
```

Run migrations and seed:

```bash
python3 manage.py migrate
python3 manage.py shell
>>> exec(open('scripts/seed.py').read())
```

Start the server and workers:

```bash
# Terminal 1 — Django
python3 manage.py runserver

# Terminal 2 — Celery worker
celery -A config worker -l info

# Terminal 3 — Celery beat (periodic tasks)
celery -A config beat -l info
```

### Frontend

```bash
cd frontend
pnpm install
```

Create a `.env` file in `frontend/`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

```bash
pnpm dev
```

Open `http://localhost:5173` and log in with:

- **Email:** alice@example.com, bob@example.com, or charlie@example.com
- **Password:** password123

## Test Accounts (Seeded)

| Merchant | Email | Password |
|----------|-------|----------|
| Alice's Electronics | alice@example.com | password123 |
| Bob's Groceries | bob@example.com | password123 |
| Charlie's Clothing | charlie@example.com | password123 |

Each merchant has 2 bank accounts and 6 credit entries (random amounts between ₹100–₹5,000).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login/` | JWT login (email + password) |
| POST | `/api/v1/auth/refresh/` | Refresh JWT token |
| GET | `/api/v1/merchants/me/` | Merchant dashboard (balance info) |
| GET | `/api/v1/ledger/` | Ledger entries for current merchant |
| GET | `/api/v1/payouts/` | List payouts |
| POST | `/api/v1/payouts/` | Create payout (requires Idempotency-Key header) |
| GET | `/api/v1/payouts/bank-accounts/` | List bank accounts |
| POST | `/api/v1/payouts/bank-accounts/` | Create bank account |

## Running Tests

```bash
cd backend
source venv/bin/activate
python3 manage.py test apps.payouts -v 2
```

Two tests:
1. **Concurrency test** — Two threads submit 70 rupee payouts against 100 rupee balance simultaneously. Asserts exactly one succeeds (201) and one is rejected (402).
2. **Idempotency test** — Same idempotency key sent twice returns identical response with only one payout created.

## Architecture Decisions

- **Paise as BigIntegerField** — No floats, no decimals. ₹100.50 = 10050 paise. Avoids floating point errors entirely.
- **Balance from aggregation** — `get_balance()` uses `Sum()` aggregates on the ledger table, not Python arithmetic. The database is the source of truth.
- **Row-level locking** — `select_for_update()` on the merchant row inside `transaction.atomic()` serializes concurrent payout requests.
- **Idempotency via dedicated table** — `IdempotencyKey` stores the full response body and status code. Second call with same key returns the cached response without touching the payout logic.
- **Celery for background processing** — `process_payout` task runs async after payout creation. Bank simulator: 70% success, 20% failure, 10% hang.
- **Periodic stuck-payout scanner** — Celery Beat runs `scan_stuck_payouts` every 30 seconds to retry payouts stuck in processing for >30s (max 3 attempts).

See [EXPLAINER.md](EXPLAINER.md) for detailed technical explanations.
