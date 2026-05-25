from django.contrib import admin
from .models import StoreSettings

@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ['store_name','contact_email','vat_rate','updated_at']
