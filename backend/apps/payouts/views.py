from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ledger.utils import get_balance
from apps.merchants.models import Merchant
from apps.payouts.models import BankAccount, IdempotencyKey, Payout
from apps.payouts.serializers import (
    BankAccountSerializer,
    PayoutCreateSerializer,
    PayoutSerializer,
)
from apps.payouts.tasks import process_payout


# ── Bank Accounts ───────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def bank_accounts(request):
    """List or create bank accounts for the authenticated merchant."""
    if request.method == 'GET':
        accounts = BankAccount.objects.filter(merchant=request.user, is_active=True)
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)

    # POST
    serializer = BankAccountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(merchant=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Payouts ─────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payouts(request):
    """List payouts or create a new payout with idempotency."""
    if request.method == 'GET':
        payout_qs = Payout.objects.filter(merchant=request.user).order_by('-created_at')
        serializer = PayoutSerializer(payout_qs, many=True)
        return Response(serializer.data)

    # ── POST: Create Payout ─────────────────────────────────────

    # 1. Read idempotency key from headers
    idempotency_key = request.headers.get('Idempotency-Key')
    if not idempotency_key:
        return Response(
            {'error': 'Idempotency-Key header is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 2. Check for existing idempotency key
    existing = IdempotencyKey.objects.filter(
        merchant=request.user, key=idempotency_key
    ).first()
    if existing and existing.expires_at > timezone.now():
        return Response(existing.response_body, status=existing.response_status)

    # 3. Validate request body
    create_serializer = PayoutCreateSerializer(data=request.data)
    if not create_serializer.is_valid():
        return Response(create_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    amount_paise = create_serializer.validated_data['amount_paise']
    bank_account_id = create_serializer.validated_data['bank_account_id']

    # 4. Verify bank account belongs to this merchant
    try:
        bank_account = BankAccount.objects.get(
            id=bank_account_id, merchant=request.user, is_active=True
        )
    except BankAccount.DoesNotExist:
        return Response(
            {'error': 'Bank account not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 5. Atomic block: lock merchant row, check balance, create payout
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

        response_data = PayoutSerializer(payout).data

        IdempotencyKey.objects.create(
            merchant=merchant,
            key=idempotency_key,
            response_body=response_data,
            response_status=201,
            expires_at=timezone.now() + timedelta(hours=24),
        )

    # 6. After transaction commits, queue async processing
    process_payout.delay(payout.id)

    # 7. Return response
    return Response(response_data, status=status.HTTP_201_CREATED)
