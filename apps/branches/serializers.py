from rest_framework import serializers
from .models import Branch

class BranchSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model  = Branch
        fields = ['id','name','address','phone','email','is_active','staff_count','created_at']

    def get_staff_count(self, obj):
        return obj.staff_set.filter(status='active').count()
