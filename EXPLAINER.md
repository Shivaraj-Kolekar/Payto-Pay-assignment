# EXPLAINER.md

## 1. The Ledger

My balance calculation lives in `apps/ledger/utils.py`:

```python
def get_balance(merchant):
    total_credits = LedgerEntry.objects.filter(
        merchant=merchant, entry_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_debits = LedgerEntry.objects.filter(
        merchant=merchant, entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    held_balance = Payout.objects.filter(
        merchant=merchant, status__in=['pending', 'processing']
    ).aggregate(total=Sum('amount_paise'))['total'] or 0

    available_balance = total_credits - total_debits - held_balance

    return {
        'available_balance': available_balance,
        'held_balance': held_balance,
        'total_credits': total_credits,
    }
```

I went with a single `LedgerEntry` model with `entry_type = 'credit' | 'debit'` and `amount` as a `BigIntegerField` in paise. No floats anywhere.

The balance is never stored — it's always derived from the ledger using Django ORM `Sum()` aggregates. This means the database does the arithmetic, not Python. If I fetched all rows and summed in Python, I'd have a race condition window between the read and the next write. With `aggregate()`, Postgres runs `SELECT SUM(amount) FROM ledger_entries WHERE ...` which is atomic.

I split credits from debits instead of using positive/negative amounts because it makes the audit trail cleaner. A debit entry is only created when a payout actually completes (success from the bank simulator), not when the payout is requested. During the pending/processing phase, the funds are "held" by counting pending payout amounts separately.

The invariant holds: `credits - debits - held = available_balance`. Held drops to 0 when a payout either completes (becomes a debit) or fails (payout removed from held count).

## 2. The Lock

The concurrency protection is in `apps/payouts/views.py`:

```python
with transaction.atomic():
    merchant = Merchant.objects.select_for_update().get(id=request.user.id)
    balance = get_balance(merchant)

    if amount_paise > balance['available_balance']:
        return Response(
            {'error': 'Insufficient balance'},
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )

    payout = Payout.objects.create(
        merchant=merchant,
        bank_account=bank_account,
        amount_paise=amount_paise,
        status='pending',
        idempotency_key=idempotency_key,
    )
```

The key line is `Merchant.objects.select_for_update().get(id=request.user.id)`.

This acquires an exclusive row-level lock on the merchant row in Postgres using `SELECT ... FOR UPDATE`. The `transaction.atomic()` block ensures the lock is held for the entire check-then-create sequence.

Here's what happens when two concurrent requests hit:
- Thread A enters the atomic block, locks the merchant row
- Thread B enters the atomic block, tries to lock the same row — Postgres blocks it
- Thread A reads the balance (say 10000), creates the payout (7000), commits → lock released
- Thread B wakes up, reads the balance (now 3000 because Thread A's payout is pending), tries 7000 → rejected with 402

Without `select_for_update()`, both threads would read 10000 simultaneously, both would pass the balance check, and both would create payouts — double-spending the merchant's balance.

I lock on the merchant row specifically because that's the narrowest lock that still serializes balance operations for the same merchant. Two different merchants can create payouts simultaneously without blocking each other.

## 3. The Idempotency

I use a dedicated `IdempotencyKey` model:

```python
class IdempotencyKey(models.Model):
    merchant = models.ForeignKey(...)
    key = models.CharField(max_length=255)
    response_body = models.JSONField()
    response_status = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
```

Before any payout logic runs, I check for an existing key:

```python
existing = IdempotencyKey.objects.filter(
    merchant=request.user, key=idempotency_key
).first()
if existing and existing.expires_at > timezone.now():
    return Response(existing.response_body, status=existing.response_status)
```

If the key exists and hasn't expired (24 hours), I return the cached response body and status code verbatim. No payout logic runs at all.

Keys are scoped per merchant via `merchant` FK. The same UUID used by two different merchants creates separate entries.

For the "first request in-flight when second arrives" case: since the idempotency check happens before the `select_for_update()` lock, two simultaneous first requests with the same key would both pass the check and both enter the atomic block. But the `unique_together = [['merchant', 'idempotency_key']]` constraint on the Payout model catches this at the database level — the second `Payout.objects.create()` would raise an `IntegrityError`, rolling back the transaction. In practice this is a narrow window, but the DB constraint is the safety net.

## 4. The State Machine

Legal transitions are defined on the Payout model itself:

```python
class Payout(models.Model):
    LEGAL_TRANSITIONS = {
        'pending': ['processing'],
        'processing': ['completed', 'failed'],
        'completed': [],    # terminal — nothing allowed
        'failed': [],       # terminal — nothing allowed
    }

    def can_transition_to(self, new_status):
        return new_status in self.LEGAL_TRANSITIONS.get(self.status, [])
```

Every state change in the Celery task calls `can_transition_to()` first:

```python
# In process_payout task:

# Pending → Processing
if not payout.can_transition_to('processing'):
    logger.error(f"Payout {payout_id} cannot transition to processing")
    return

# Processing → Completed
if not payout.can_transition_to('completed'):
    return

# Processing → Failed
if not payout.can_transition_to('failed'):
    return
```

`failed → completed` is blocked because `LEGAL_TRANSITIONS['failed']` is an empty list, so `can_transition_to('completed')` returns `False`. Same for `completed → pending` or any other backward transition.

The check runs inside `transaction.atomic()` + `select_for_update()`, so even if two Celery workers pick up the same payout, only one can transition it — the other will see the already-updated status and bail out.

## 5. The AI Audit

**The problem: Celery's `on_failure` hook doesn't work with `@shared_task` decorator.**

I initially asked AI to add a failure handler that marks a payout as `failed` when the task exhausts all retries. AI gave me this:

```python
@shared_task(bind=True, max_retries=3)
def process_payout(self, payout_id):
    # ... task logic ...

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        payout = Payout.objects.get(id=args[0])
        payout.status = 'failed'
        payout.save()
```

This is wrong in two ways:

1. **`on_failure` defined as a nested method inside the task function does nothing.** Celery ignores it. It needs to be on the Task class, not inside the decorated function.
2. **No transaction protection.** If the status update fails halfway, the payout is in a corrupted state.

What I replaced it with:

```python
class PayoutTask(Task):
    """Custom task class with failure handler."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        payout_id = args[0] if args else kwargs.get('payout_id')
        if payout_id:
            with transaction.atomic():
                try:
                    payout = Payout.objects.select_for_update().get(id=payout_id)
                    payout.status = 'failed'
                    payout.save()
                except Payout.DoesNotExist:
                    pass
        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(bind=True, base=PayoutTask, max_retries=3, default_retry_delay=10)
def process_payout(self, payout_id):
    # ... task logic ...
```

I created a custom `PayoutTask` class that extends `celery.Task` and overrides `on_failure` at the class level. Then I pass `base=PayoutTask` to `@shared_task`. This way Celery actually calls the handler when retries are exhausted. The status update is also wrapped in `transaction.atomic()` + `select_for_update()` so it's safe against concurrent access.

I caught this because I tested the failure path manually — stopped the worker mid-task, restarted it, and the payout was stuck in `processing` forever instead of moving to `failed`. That's when I realized the hook wasn't being called at all.
