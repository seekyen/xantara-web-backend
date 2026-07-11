from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('itemcode', 'descshort', 'deptcode', 'classcode', 'sell_price_rp', 'active')
    search_fields = ('itemcode', 'itemcode2', 'descshort', 'desclong')
    list_filter   = ('active', 'deptcode', 'classcode', 'categorycode')
