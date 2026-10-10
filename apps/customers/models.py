from django.db import models

class Customer(models.Model):
    STATUS_CHOICES = [('active','Active'),('inactive','Inactive')]

    name           = models.CharField(max_length=150)
    email          = models.EmailField(unique=True, blank=True, null=True)
    phone          = models.CharField(max_length=20, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_spent    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orders   = models.PositiveIntegerField(default=0)
    loyalty_points = models.PositiveIntegerField(default=0)
    last_visit     = models.DateField(null=True, blank=True)
    joined_at      = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0].upper() for p in parts[:2])


class LoyaltyPromo(models.Model):
    """A named period (dates inclusive) in which customers earn points: every `spend_per_point`
    pesos of a sale, net of VAT, earns one point. There is no store-wide rate outside promos."""
    name            = models.CharField(max_length=100)
    start_date      = models.DateField()
    end_date        = models.DateField()
    spend_per_point = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', 'name']

    def __str__(self):
        return f'{self.name} ({self.start_date} to {self.end_date}, P{self.spend_per_point} per point)'


class LoyaltyEntry(models.Model):
    """Immutable points ledger. `customer.loyalty_points` is the running total of these rows;
    the promo and rate that applied are copied onto the row so later edits never rewrite history."""
    KIND_CHOICES = [('earn', 'Earned'), ('reversal', 'Reversed')]

    customer        = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loyalty_entries')
    # A web sale (`transaction`) or a POS invoice synced from a device (`sync_event`) earned this row.
    transaction     = models.ForeignKey('sales.Transaction', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='loyalty_entries')
    sync_event      = models.ForeignKey('syncing.CloudSyncEvent', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='loyalty_entries')
    kind            = models.CharField(max_length=10, choices=KIND_CHOICES)
    points          = models.IntegerField()
    net_amount      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    spend_per_point = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promo           = models.ForeignKey(LoyaltyPromo, on_delete=models.SET_NULL, null=True, blank=True)
    promo_name      = models.CharField(max_length=100, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['transaction', 'kind'], name='one_loyalty_entry_per_kind'),
            models.UniqueConstraint(fields=['sync_event', 'kind'], name='one_loyalty_entry_per_event_kind'),
        ]
