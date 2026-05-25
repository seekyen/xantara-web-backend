from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Staff
from apps.branches.serializers import BranchSerializer

class StaffSerializer(serializers.ModelSerializer):
    branch_detail  = BranchSerializer(source='branch', read_only=True)
    role_display   = serializers.CharField(source='get_role_display',   read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    initials       = serializers.ReadOnlyField()

    class Meta:
        model  = Staff
        fields = [
            'id','name','email','phone','role','role_display',
            'branch','branch_detail','status','status_display',
            'avatar','initials','sales_count','last_login_at','joined_at','created_at',
        ]
        read_only_fields = ['sales_count','last_login_at','created_at']

class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = Staff
        fields = ['name','email','phone','role','branch','status','password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        staff    = Staff(**validated_data)
        staff.set_password(password)
        staff.avatar = ''.join(p[0].upper() for p in validated_data['name'].split()[:2])
        staff.save()
        return staff

class StaffMeSerializer(serializers.ModelSerializer):
    branch_detail = BranchSerializer(source='branch', read_only=True)

    class Meta:
        model  = Staff
        fields = ['id','name','email','phone','role','branch','branch_detail','status','initials']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
