from django.contrib import admin
from .models import Branch

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name','is_active','created_at')
