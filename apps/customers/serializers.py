from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from .models import Customer, LoyaltyEntry, LoyaltyPromo

class CustomerSerializer(serializers.ModelSerializer):
    initials       = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Customer
        fields = [
            'id','name','email','phone','status','status_display',
            'total_spent','total_orders','loyalty_points',
            'last_visit','joined_at','initials',
        ]
        read_only_fields = ['total_spent','total_orders','loyalty_points',
                            'last_visit','joined_at']


class LoyaltyPromoSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model  = LoyaltyPromo
        fields = ['id', 'name', 'start_date', 'end_date', 'spend_per_point', 'is_active', 'status']

    def get_status(self, promo):
        today = timezone.localdate()
        if not promo.is_active:
            return 'paused'
        if promo.end_date < today:
            return 'ended'
        return 'upcoming' if promo.start_date > today else 'running'

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter a promo name.')
        return value

    def validate_spend_per_point(self, value):
        if value < Decimal('0.01') or value > Decimal('1000000'):
            raise serializers.ValidationError('Enter an amount between 0.01 and 1,000,000.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'The promo cannot end before it starts.'})
        return attrs


class LoyaltyEntrySerializer(serializers.ModelSerializer):
    # The receipt reference: a web sale's TXN number, or the invoice number of a synced POS invoice.
    txn_no = serializers.SerializerMethodField()

    class Meta:
        model  = LoyaltyEntry
        fields = ['id', 'kind', 'points', 'net_amount', 'spend_per_point', 'promo_name', 'txn_no', 'created_at']

    def get_txn_no(self, entry):
        if entry.transaction_id:
            return entry.transaction.txn_no
        payload = entry.sync_event.payload if entry.sync_event_id else None
        number = payload.get('invoiceNumber') if isinstance(payload, dict) else None
        return str(number) if number else None
