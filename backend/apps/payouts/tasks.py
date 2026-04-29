import logging
import random

from celery import shared_task, Task
from django.db import transaction
from django.utils import timezone

from apps.ledger.models import LedgerEntry
from apps.payouts.models import Payout

logger = logging.getLogger(__name__)


class PayoutTask(Task):
    """Custom task class with failure handler that marks payout as failed."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        payout_id = args[0] if args else kwargs.get('payout_id')
        if payout_id:
            with transaction.atomic():
                try:
                    payout = Payout.objects.select_for_update().get(id=payout_id)
                    payout.status = 'failed'
                    payout.save()
                    logger.error(f"Payout {payout_id} failed after max retries: {exc}")
                except Payout.DoesNotExist:
                    pass
        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(bind=True, base=PayoutTask, max_retries=3, default_retry_delay=10)
def process_payout(self, payout_id):
    """
    Process a single payout through the bank simulator.
    Retries up to 3 times on exception.
    """
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        logger.error(f"Payout {payout_id} not found")
        return

    # 1. Only process pending payouts
    if payout.status != 'pending' and payout.status != 'processing':
        logger.info(f"Payout {payout_id} is {payout.status}, skipping")
        return

    # 2. Transition to processing
    if payout.status == 'pending':
        if not payout.can_transition_to('processing'):
            logger.error(f"Payout {payout_id} cannot transition to processing")
            return

        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            payout.status = 'processing'
            payout.processing_started_at = timezone.now()
            payout.attempts += 1
            payout.save()

    # 3. Bank simulator
    roll = random.random()
    if roll < 0.70:
        outcome = 'success'
    elif roll < 0.90:
        outcome = 'failure'
    else:
        outcome = 'hang'

    logger.info(f"Payout {payout_id}: bank simulator outcome = {outcome}")

    # 4. Success → completed + debit entry
    if outcome == 'success':
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if not payout.can_transition_to('completed'):
                return
            payout.status = 'completed'
            payout.save()

            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type='debit',
                amount=payout.amount_paise,
                description=f"Payout #{payout.id} to bank account",
                reference_payout_id=str(payout.id),
            )
        logger.info(f"Payout {payout_id} completed successfully")

    # 5. Failure → failed (no debit, held funds freed)
    elif outcome == 'failure':
        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)
            if not payout.can_transition_to('failed'):
                return
            payout.status = 'failed'
            payout.save()
        logger.info(f"Payout {payout_id} failed")

    # 6. Hang → do nothing, periodic task will retry
    else:
        logger.info(f"Payout {payout_id} hung, will be retried by scan_stuck_payouts")
        return


@shared_task
def scan_stuck_payouts():
    """
    Find payouts stuck in 'processing' for more than 30 seconds
    and retry them.
    """
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(seconds=30)
    stuck_payouts = Payout.objects.filter(
        status='processing',
        processing_started_at__lt=cutoff,
        attempts__lt=3,
    )

    count = stuck_payouts.count()
    if count:
        logger.info(f"Found {count} stuck payouts, requeueing...")

    for payout in stuck_payouts:
        process_payout.delay(payout.id)
