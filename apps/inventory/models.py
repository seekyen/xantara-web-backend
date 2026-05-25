from django.db import models

class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = [
        ('in_stock','In Stock'), ('low_stock','Low Stock'), ('out_of_stock','Out of Stock'),
    ]

    name       = models.CharField(max_length=200)
    sku        = models.CharField(max_length=50, unique=True)
    category   = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                   null=True, related_name='products')
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    cost       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock      = models.PositiveIntegerField(default=0)
    max_stock  = models.PositiveIntegerField(default=50)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock')
    sold       = models.PositiveIntegerField(default=0)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def save(self, *args, **kwargs):
        if self.stock == 0:
            self.status = 'out_of_stock'
        elif self.stock <= 10:
            self.status = 'low_stock'
        else:
            self.status = 'in_stock'
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        return self.price * self.stock

    @property
    def profit_margin(self):
        if self.price == 0:
            return 0
        return round(((self.price - self.cost) / self.price) * 100, 1)
