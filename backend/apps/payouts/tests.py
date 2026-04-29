from concurrent.futures import ThreadPoolExecutor

from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ledger.models import LedgerEntry
from apps.ledger.utils import get_balance
from apps.merchants.models import Merchant
from apps.payouts.models import BankAccount, IdempotencyKey, Payout


class PayoutConcurrencyTest(TransactionTestCase):
    """Test that concurrent payout requests don't double-spend."""

    def setUp(self):
        self.merchant = Merchant.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            business_name='Test Shop',
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number='1234567890',
            ifsc_code='HDFC0001234',
            account_holder_name='Test User',
        )
        # Seed 10000 paise credit
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='credit',
            amount=10000,
            description='Test credit',
        )
        # Get JWT token
        refresh = RefreshToken.for_user(self.merchant)
        self.token = str(refresh.access_token)

    def _make_payout_request(self, idempotency_key):
        """Helper to make a payout POST request."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        return client.post(
            '/api/v1/payouts/',
            {'amount_paise': 7000, 'bank_account_id': self.bank_account.id},
            format='json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
        )

    def test_concurrent_payouts_prevent_double_spend(self):
        """Two concurrent 7000 paise payouts with 10000 balance: one succeeds, one fails."""
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(self._make_payout_request, 'key-1')
            future2 = executor.submit(self._make_payout_request, 'key-2')

            response1 = future1.result()
            response2 = future2.result()

        status_codes = sorted([response1.status_code, response2.status_code])
        self.assertEqual(status_codes, [201, 402], "Exactly one should succeed (201) and one should fail (402)")

        # Verify balance is correct
        balance = get_balance(self.merchant)
        self.assertEqual(balance['available_balance'], 3000)  # 10000 - 7000 held
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)


class PayoutIdempotencyTest(TestCase):
    """Test that duplicate payout requests with same idempotency key return same response."""

    def setUp(self):
        self.merchant = Merchant.objects.create_user(
            username='idempuser',
            email='idemp@example.com',
            password='testpass123',
            business_name='Idemp Shop',
        )
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number='9876543210',
            ifsc_code='ICIC0005678',
            account_holder_name='Idemp User',
        )
        # Seed 20000 paise credit
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='credit',
            amount=20000,
            description='Test credit',
        )
        # Get JWT token
        refresh = RefreshToken.for_user(self.merchant)
        self.token = str(refresh.access_token)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_idempotent_payout_requests(self):
        """Same idempotency key should return same response and create only one payout."""
        payload = {
            'amount_paise': 5000,
            'bank_account_id': self.bank_account.id,
        }

        response1 = self.client.post(
            '/api/v1/payouts/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY='test-uuid-1234',
        )
        response2 = self.client.post(
            '/api/v1/payouts/',
            payload,
            format='json',
            HTTP_IDEMPOTENCY_KEY='test-uuid-1234',
        )

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(response1.data, response2.data)

        # Only one payout and one idempotency key should exist
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)
        self.assertEqual(IdempotencyKey.objects.filter(merchant=self.merchant).count(), 1)
