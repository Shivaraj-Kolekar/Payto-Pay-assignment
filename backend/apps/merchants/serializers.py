from rest_framework import serializers
from apps.merchants.models import Merchant
from apps.ledger.utils import get_balance


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['id', 'email', 'business_name']


class MerchantDashboardSerializer(serializers.ModelSerializer):
    available_balance = serializers.SerializerMethodField()
    held_balance = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = ['id', 'email', 'business_name', 'available_balance', 'held_balance']

    def get_available_balance(self, obj):
        return get_balance(obj)['available_balance']

    def get_held_balance(self, obj):
        return get_balance(obj)['held_balance']
