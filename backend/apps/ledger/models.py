from django.conf import settings
from django.db import models


class LedgerEntry(models.Model):
    """Tracks credit and debit entries for each merchant."""

    ENTRY_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ledger_entries',
    )
    entry_type = models.CharField(max_length=6, choices=ENTRY_TYPE_CHOICES)
    amount = models.BigIntegerField()  # in paise
    description = models.CharField(max_length=255, blank=True, default='')
    reference_payout_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_type} {self.amount} - {self.merchant}"