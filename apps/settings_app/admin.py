from django.contrib import admin
from .models import StoreSettings, Category, SubCategory, Department


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'contact_email', 'vat_rate', 'updated_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'is_active', 'created_at']
    list_filter   = ['is_active']
    search_fields = ['code', 'name']


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'category_code', 'is_active', 'created_at']
    list_filter   = ['category_code', 'is_active']
    search_fields = ['code', 'name', 'category_code']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'class_name', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['code', 'name']