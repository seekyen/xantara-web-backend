from django.conf import settings
from django.db import models


class SyncInstallation(models.Model):
    business_id = models.CharField(max_length=64, db_index=True)
    installation_id = models.CharField(max_length=64, unique=True)
    terminal_id = models.CharField(max_length=64)
    local_branch_id = models.CharField(max_length=64)
    branch = models.ForeignKey(
        'inventory.Branch',
        on_delete=models.PROTECT,
        related_name='sync_installations',
    )
    authorized_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sync_installations',
    )
    is_active = models.BooleanField(default=True)
    sync_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sync_installation'
        ordering = ['business_id', 'installation_id']
        constraints = [
            models.UniqueConstraint(
                fields=['business_id', 'terminal_id'],
                name='uniq_sync_business_terminal',
            ),
            models.UniqueConstraint(
                fields=['business_id', 'local_branch_id', 'installation_id'],
                name='uniq_sync_business_branch_install',
            ),
        ]

    def __str__(self):
        return f'{self.business_id}:{self.installation_id}'


class CloudSyncEvent(models.Model):
    installation = models.ForeignKey(
        SyncInstallation,
        on_delete=models.PROTECT,
        related_name='events',
    )
    branch = models.ForeignKey(
        'inventory.Branch',
        on_delete=models.PROTECT,
        related_name='sync_events',
    )
    business_id = models.CharField(max_length=64, db_index=True)
    local_branch_id = models.CharField(max_length=64)
    local_event_id = models.CharField(max_length=64)
    aggregate_type = models.CharField(max_length=64)
    aggregate_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=96, db_index=True)
    idempotency_key = models.CharField(max_length=191)
    schema_version = models.PositiveSmallIntegerField()
    payload = models.JSONField()
    device_created_at = models.DateTimeField()
    accepted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'cloud_sync_event'
        ordering = ['accepted_at', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['business_id', 'idempotency_key'],
                name='uniq_sync_business_idempotency',
            ),
        ]
        indexes = [
            models.Index(
                fields=['business_id', 'local_branch_id', 'accepted_at'],
                name='idx_sync_business_branch_time',
            ),
        ]

    def __str__(self):
        return f'{self.business_id}:{self.event_type}:{self.local_event_id}'
