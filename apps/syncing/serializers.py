from rest_framework import serializers


class SyncEventUploadSerializer(serializers.Serializer):
    schemaVersion = serializers.IntegerField(min_value=1, max_value=1)
    localEventId = serializers.CharField(max_length=64)
    businessId = serializers.CharField(max_length=64)
    branchId = serializers.CharField(max_length=64)
    aggregateType = serializers.CharField(max_length=64)
    aggregateId = serializers.CharField(max_length=128)
    eventType = serializers.CharField(max_length=96)
    idempotencyKey = serializers.CharField(max_length=191)
    payload = serializers.JSONField()
    createdAt = serializers.DateTimeField()

    def validate(self, attrs):
        header_key = self.context['request'].headers.get('Idempotency-Key', '')
        if not header_key:
            raise serializers.ValidationError(
                {'idempotencyKey': 'Idempotency-Key header is required.'},
            )
        if header_key != attrs['idempotencyKey']:
            raise serializers.ValidationError(
                {'idempotencyKey': 'Header and body values must match.'},
            )
        return attrs
