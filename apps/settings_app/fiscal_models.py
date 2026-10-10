import uuid
from django.conf import settings
from django.db import models


class FiscalCompany(models.Model):
    registered_name = models.CharField(max_length=200)
    tin = models.CharField(max_length=9)
    address = models.TextField()
    tax_type = models.CharField(max_length=10, choices=[('vat', 'VAT'), ('nonVat', 'Non-VAT')])
    locked_at = models.DateTimeField(null=True, blank=True)


class FiscalBranch(models.Model):
    branch = models.OneToOneField('inventory.Branch', on_delete=models.PROTECT)
    branch_code = models.CharField(max_length=5, unique=True)
    rdo = models.CharField(max_length=3)
    registered_address = models.TextField()
    locked_at = models.DateTimeField(null=True, blank=True)


class FiscalTerminal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(FiscalBranch, on_delete=models.PROTECT)
    terminal_code = models.CharField(max_length=16, unique=True)
    machine_serial = models.CharField(max_length=100, unique=True)
    min = models.CharField(max_length=100, unique=True)
    ptu = models.CharField(max_length=100)
    ptu_issued_on = models.DateField()
    starting_serial = models.PositiveIntegerField(default=1)
    activated_at = models.DateTimeField(null=True, blank=True)
    enrollment_hash = models.CharField(max_length=128, blank=True)
    installation = models.OneToOneField('syncing.SyncInstallation', on_delete=models.PROTECT, null=True, blank=True)


class FiscalAudit(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
