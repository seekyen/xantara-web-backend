from django.db import models, transaction

class Branch(models.Model):
    inventory_branch = models.OneToOneField('inventory.Branch', on_delete=models.PROTECT, null=True, blank=True, editable=False, related_name='managed_branch')
    name       = models.CharField(max_length=100, unique=True)
    address    = models.TextField(blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


    @transaction.atomic
    def save(self, *args, **kwargs):
        from apps.inventory.models import Branch as StockBranch
        super().save(*args, **kwargs)
        if not self.inventory_branch_id:
            code = f'BR{self.pk:06d}'
            suffix = 0
            while StockBranch.objects.filter(code=code).exists():
                suffix += 1
                code = f'B{self.pk:05d}{suffix:04d}'
            location = StockBranch.objects.create(code=code, name=self.name, address=self.address[:255], active=self.is_active)
            type(self).objects.filter(pk=self.pk).update(inventory_branch=location)
            self.inventory_branch = location
        else:
            StockBranch.objects.filter(pk=self.inventory_branch_id).update(name=self.name, address=self.address[:255], active=self.is_active)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        from apps.inventory.models import Branch as StockBranch
        if self.inventory_branch_id:
            StockBranch.objects.filter(pk=self.inventory_branch_id).update(active=False)
        return super().delete(*args, **kwargs)
