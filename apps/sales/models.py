from django.db import models
from apps.inventory.models import Product
from apps.customers.models import Customer
from apps.accounts.models import Staff
from apps.branches.models import Branch

class Transaction(models.Model):
    STATUS_CHOICES     = [('completed','Completed'),('refunded','Refunded'),
                          ('voided','Voided'),('pending','Pending')]
    PAY_METHOD_CHOICES = [('cash','Cash'),('card','Card'),
                          ('gcash','GCash'),('maya','Maya')]

    txn_no     = models.CharField(max_length=30, unique=True, editable=False)
    customer   = models.ForeignKey(Customer, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='transactions')
    cashier    = models.ForeignKey(Staff,    on_delete=models.SET_NULL,
                                   null=True, related_name='transactions')
    branch     = models.ForeignKey(Branch,   on_delete=models.SET_NULL,
                                   null=True, related_name='transactions')
    subtotal   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pay_method = models.CharField(max_length=10, choices=PAY_METHOD_CHOICES, default='cash')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.txn_no

    def save(self, *args, **kwargs):
        if not self.txn_no:
            from django.utils import timezone
            year       = timezone.now().year
            count      = Transaction.objects.filter(created_at__year=year).count() + 1
            self.txn_no = f'TXN-{year}-{count:05d}'
        super().save(*args, **kwargs)

class TransactionItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    product     = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name        = models.CharField(max_length=200)
    sku         = models.CharField(max_length=50)
    qty         = models.PositiveIntegerField(default=1)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    line_total  = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_total = self.qty * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} x{self.qty}'
