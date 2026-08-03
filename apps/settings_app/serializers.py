from rest_framework import serializers
from .models import StoreSettings, Category, SubCategory, Department, Class, Size, Color, Unit, Form, ItemType


class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model   = StoreSettings
        exclude = ['id']


class CategorySerializer(serializers.ModelSerializer):
    sub_category_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id', 'code', 'name', 'is_active', 'sub_category_count', 'created_at', 'updated_at']
        read_only_fields = ['code', 'created_at', 'updated_at']

    def get_sub_category_count(self, obj):
        return SubCategory.objects.filter(category_code=obj.code).count()


class CategoryMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'code', 'name']


class SubCategorySerializer(serializers.ModelSerializer):
    category_detail = serializers.SerializerMethodField()

    class Meta:
        model  = SubCategory
        fields = [
            'id', 'code', 'name',
            'category_code', 'category_detail',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['code', 'created_at', 'updated_at']

    def get_category_detail(self, obj):
        try:
            cat = Category.objects.get(code=obj.category_code)
            return CategoryMinimalSerializer(cat).data
        except Category.DoesNotExist:
            return None

    def validate_category_code(self, value):
        if not Category.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError(
                f"Category '{value}' does not exist or is inactive."
            )
        return value


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Department
        fields = ['id', 'code', 'name', 'class_name', 'is_active']
        read_only_fields = ['code']


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Class
        fields = ['id', 'code', 'name', 'is_active']
        read_only_fields = ['code']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Size
        fields = ['id', 'code', 'name', 'is_active']
        read_only_fields = ['code']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Color
        fields = ['id', 'code', 'name', 'is_active']
        read_only_fields = ['code']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Unit
        fields = ['id', 'code', 'name', 'is_active']
        read_only_fields = ['code']


class FormSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Form
        fields = ['id', 'code', 'name', 'is_active']
        read_only_fields = ['code']


class ItemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ItemType
        fields = ['id', 'code', 'name', 'is_active']
        read_only_fields = ['code']