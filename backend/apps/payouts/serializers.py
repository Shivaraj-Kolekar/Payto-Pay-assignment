from rest_framework import serializers
from apps.payouts.models import BankAccount, Payout


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'


class PayoutSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.CharField(
        source='bank_account.account_holder_name', read_only=True
    )

    class Meta:
        model = Payout
        fields = [
            'id', 'amount_paise', 'status', 'bank_account',
            'bank_account_name', 'idempotency_key', 'attempts',
            'created_at', 'updated_at',
        ]


class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.IntegerField()
