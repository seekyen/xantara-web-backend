from django.contrib import admin
from .models import Transaction, TransactionItem

class TransactionItemInline(admin.TabularInline):
    model  = TransactionItem
    extra  = 0
    fields = ['name','sku','qty','price','line_total']
    readonly_fields = ['line_total']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display   = ['txn_no','cashier','branch','pay_method','total','status','created_at']
    list_filter    = ['status','pay_method','branch']
    search_fields  = ['txn_no','cashier__name','customer__name']
    readonly_fields = ['txn_no','created_at','updated_at']
    inlines        = [TransactionItemInline]
