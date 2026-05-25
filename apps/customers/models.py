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
