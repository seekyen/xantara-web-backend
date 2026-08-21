from django.contrib import admin

from .models import CloudSyncEvent, SyncInstallation


@admin.register(SyncInstallation)
class SyncInstallationAdmin(admin.ModelAdmin):
    list_display = (
        'installation_id',
        'business_id',
        'terminal_id',
        'branch',
        'authorized_staff',
        'is_active',
        'sync_enabled',
    )
    list_filter = ('is_active', 'sync_enabled', 'branch')
    search_fields = (
        'installation_id',
        'business_id',
        'terminal_id',
        'local_branch_id',
        'authorized_staff__email',
    )


@admin.register(CloudSyncEvent)
class CloudSyncEventAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'business_id',
        'local_branch_id',
        'event_type',
        'local_event_id',
        'accepted_at',
    )
    list_filter = ('event_type', 'branch')
    search_fields = (
        'business_id',
        'local_branch_id',
        'local_event_id',
        'idempotency_key',
    )
    readonly_fields = (
        'installation',
        'branch',
        'business_id',
        'local_branch_id',
        'local_event_id',
        'aggregate_type',
        'aggregate_id',
        'event_type',
        'idempotency_key',
        'schema_version',
        'payload',
        'device_created_at',
        'accepted_at',
    )
