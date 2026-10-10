from django.contrib import admin
from .models import (
    Supplier, SupplierAddress, SupplierContact,
    SupplierBankDetail, SupplierProductCategory,
)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('supplier_code', 'company_name', 'supplier_type', 'is_active')

admin.site.register(SupplierAddress)
admin.site.register(SupplierContact)
admin.site.register(SupplierBankDetail)
admin.site.register(SupplierProductCategory)
