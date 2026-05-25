from django.db import models

class StoreSettings(models.Model):
    store_name          = models.CharField(max_length=200, default='Xantara POS')
    address             = models.TextField(blank=True)
    contact_email       = models.EmailField(blank=True)
    contact_phone       = models.CharField(max_length=20, blank=True)
    currency            = models.CharField(max_length=10, default='PHP')
    currency_symbol     = models.CharField(max_length=5, default='₱')
    timezone            = models.CharField(max_length=50, default='Asia/Manila')
    vat_rate            = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    vat_inclusive       = models.BooleanField(default=False)
    show_vat_receipt    = models.BooleanField(default=True)
    receipt_header      = models.TextField(blank=True)
    receipt_footer      = models.TextField(blank=True)
    print_auto          = models.BooleanField(default=True)
    email_receipt       = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    pay_cash            = models.BooleanField(default=True)
    pay_card            = models.BooleanField(default=True)
    pay_gcash           = models.BooleanField(default=True)
    pay_maya            = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Store Settings'

    def __str__(self):
        return self.store_name

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
