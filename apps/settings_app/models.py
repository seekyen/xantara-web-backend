from django.db import models


class Category(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['code']
        verbose_name_plural = 'categories'

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Category.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class SubCategory(models.Model):
    code          = models.CharField(max_length=4, unique=True, editable=False)
    name          = models.CharField(max_length=100)
    category_code = models.CharField(max_length=4, db_index=True)  # no FK
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['code']
        verbose_name_plural = 'sub categories'

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = SubCategory.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)

    @property
    def sub_category_count(self):
        return SubCategory.objects.filter(category_code=self.category_code).count()


class Department(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    class_name = models.CharField(max_length=100, blank=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Department.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class Class(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering            = ['code']
        verbose_name_plural = 'classes'

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Class.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class Size(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Size.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class Color(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering            = ['code']
        verbose_name_plural = 'colors'

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Color.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class Unit(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Unit.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class Form(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = Form.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


class ItemType(models.Model):
    code       = models.CharField(max_length=4, unique=True, editable=False)
    name       = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.code:
            last = ItemType.objects.order_by('code').last()
            if last and last.code.isdigit():
                next_num = int(last.code) + 1
            else:
                next_num = 1
            self.code = f"{next_num:04d}"
        super().save(*args, **kwargs)


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