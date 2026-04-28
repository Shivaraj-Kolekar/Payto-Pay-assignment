"""
Seed script — re-runnable.
Usage: python manage.py shell  →  exec(open('scripts/seed.py').read())
"""
import random
from apps.merchants.models import Merchant
from apps.payouts.models import BankAccount, Payout, IdempotencyKey
from apps.ledger.models import LedgerEntry

# ── 1. Wipe existing seed data ──────────────────────────────────
IdempotencyKey.objects.all().delete()
Payout.objects.all().delete()
LedgerEntry.objects.all().delete()
BankAccount.objects.all().delete()
Merchant.objects.all().delete()
print("🗑️  Cleared existing data.")

# ── 2. Merchants ────────────────────────────────────────────────
merchants_data = [
    {"email": "alice@example.com",   "password": "password123", "business_name": "Alice's Electronics"},
    {"email": "bob@example.com",     "password": "password123", "business_name": "Bob's Groceries"},
    {"email": "charlie@example.com", "password": "password123", "business_name": "Charlie's Clothing"},
]

merchants = []
for data in merchants_data:
    merchant = Merchant.objects.create_user(
        username=data["email"].split("@")[0],  # AbstractUser requires username
        email=data["email"],
        password=data["password"],
        business_name=data["business_name"],
    )
    merchants.append(merchant)
    print(f"✅ Created merchant: {merchant.email}")

# ── 3. Bank accounts (2 per merchant) ──────────────────────────
for i, merchant in enumerate(merchants):
    for j in range(2):
        BankAccount.objects.create(
            merchant=merchant,
            account_number=f"10{i}{j}00123456{j}",
            ifsc_code=f"HDFC000{i}{j}12",
            account_holder_name=f"{merchant.business_name} Account {j+1}",
            is_active=True,
        )
    print(f"✅ Created 2 bank accounts for {merchant.email}")

# ── 4. Ledger entries (6 credits per merchant) ─────────────────
for merchant in merchants:
    for k in range(6):
        amount = random.randint(10000, 500000)
        LedgerEntry.objects.create(
            merchant=merchant,
            entry_type="credit",
            amount=amount,
            description=f"Customer payment #{1001 + k}",
        )
    print(f"✅ Created 6 credit entries for {merchant.email}")

print("\n🎉 Seed complete!")
