from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name','created_at')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','sku','price','stock','status','is_active')
