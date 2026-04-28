from django.db.models import Sum, Q
from apps.ledger.models import LedgerEntry
from apps.payouts.models import Payout


def get_balance(merchant):
    """
    Returns balance dict using pure Django ORM aggregates.
    All amounts are in paise.
    """
    # Total credits
    total_credits = LedgerEntry.objects.filter(
        merchant=merchant, entry_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Total debits
    total_debits = LedgerEntry.objects.filter(
        merchant=merchant, entry_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Held balance = sum of pending + processing payouts
    held_balance = Payout.objects.filter(
        merchant=merchant, status__in=['pending', 'processing']
    ).aggregate(total=Sum('amount_paise'))['total'] or 0

    # Available = credits - debits - held
    available_balance = total_credits - total_debits - held_balance

    return {
        'available_balance': available_balance,
        'held_balance': held_balance,
        'total_credits': total_credits,
    }
