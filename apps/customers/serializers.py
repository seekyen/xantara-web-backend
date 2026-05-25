from rest_framework import serializers
from .models import Customer

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
