from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Staff
from apps.branches.serializers import BranchSerializer

class StaffSerializer(serializers.ModelSerializer):
    branch_detail     = BranchSerializer(source='branch', read_only=True)
    role_display      = serializers.CharField(source='get_role_display',   read_only=True)
    status_display    = serializers.CharField(source='get_status_display', read_only=True)
    initials          = serializers.ReadOnlyField()
    has_pin           = serializers.ReadOnlyField()

    class Meta:
        model  = Staff
        fields = [
            'id','name','email','phone','role','role_display',
            'branch','branch_detail','status','status_display',
            'avatar','initials','sales_count','last_login_at','joined_at','created_at',
            'has_pin','biometric_enabled',
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
    has_pin       = serializers.ReadOnlyField()

    class Meta:
        model  = Staff
        fields = [
            'id','name','email','phone','role','branch','branch_detail',
            'status','initials','has_pin','biometric_enabled',
        ]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class SetPinSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=6, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must be digits only')
        return value


class PinLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    pin   = serializers.CharField(min_length=4, max_length=6, write_only=True)


class SetBiometricSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)


class BiometricLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(write_only=True)
