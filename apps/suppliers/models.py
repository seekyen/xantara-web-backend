from django.db import models
from django.utils import timezone
from apps.accounts.models import Staff
from apps.inventory.models import Product

class Supplier(models.Model):
    SUPPLIER_TYPES = [
        ('manufacturer', 'Manufacturer'),
        ('distributor',  'Distributor'),
        ('local',        'Local'),
        ('imported',     'Imported'),
    ]

    supplier_code             = models.CharField(max_length=20, unique=True)
    company_name              = models.CharField(max_length=150)
    trade_name                = models.CharField(max_length=150, blank=True, null=True)
    legal_name                = models.CharField(max_length=150, blank=True, null=True)
    tin                       = models.CharField(max_length=30, blank=True, null=True)
    business_permit_no        = models.CharField(max_length=50, blank=True, null=True)
    is_vat_registered         = models.BooleanField(default=False)
    payment_terms             = models.CharField(max_length=20, default='COD')
    preferred_payment_method  = models.CharField(max_length=30, blank=True, null=True)
    currency                  = models.CharField(max_length=10, default='PHP')
    lead_time_days            = models.PositiveIntegerField(default=0)
    minimum_order_quantity    = models.PositiveIntegerField(default=0)
    supplier_type             = models.CharField(max_length=20, choices=SUPPLIER_TYPES, default='local')
    is_active                 = models.BooleanField(default=True)
    is_accredited             = models.BooleanField(default=False)
    rating                    = models.CharField(max_length=10, blank=True, null=True)
    created_at                = models.DateTimeField(auto_now_add=True)
    created_by                = models.ForeignKey(Staff, on_delete=models.SET_NULL,
                                                   null=True, blank=True, related_name='+')
    updated_at                = models.DateTimeField(auto_now=True)
    updated_by                = models.ForeignKey(Staff, on_delete=models.SET_NULL,
                                                   null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['company_name']

    def __str__(self):
        return self.company_name


# The four sub-resources below intentionally reference their parent by a plain
# `supplier_id` integer rather than a ForeignKey — callers (frontend) always
# filter/fetch by supplier_id explicitly, matching how this codebase already
# treats other cross-cutting references (e.g. inventory's branch_code).

class SupplierAddress(models.Model):
    ADDRESS_TYPES = [('billing', 'Billing'), ('shipping', 'Shipping')]

    supplier_id   = models.PositiveIntegerField(db_index=True)
    address_type  = models.CharField(max_length=10, choices=ADDRESS_TYPES)
    unit_bldg_no  = models.CharField(max_length=100, blank=True, null=True)
    street        = models.CharField(max_length=150, blank=True, null=True)
    subdivision   = models.CharField(max_length=150, blank=True, null=True)
    # blank=True: the frontend unconditionally sends every sub-resource on every save,
    # even for a supplier that never visited the Medium tier where these fields live.
    barangay      = models.CharField(max_length=100, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    province      = models.CharField(max_length=100, blank=True, null=True)
    region        = models.CharField(max_length=100, blank=True, null=True)
    postal_code   = models.CharField(max_length=20, blank=True, null=True)
    country       = models.CharField(max_length=100, default='Philippines')
    is_default    = models.BooleanField(default=False)

    class Meta:
        ordering = ['supplier_id', 'address_type']


class SupplierContact(models.Model):
    supplier_id   = models.PositiveIntegerField(db_index=True)
    contact_name  = models.CharField(max_length=150, blank=True)
    position      = models.CharField(max_length=100, blank=True, null=True)
    phone         = models.CharField(max_length=20, blank=True, null=True)
    email         = models.EmailField(blank=True, null=True)
    is_primary    = models.BooleanField(default=False)

    class Meta:
        ordering = ['supplier_id', '-is_primary']


class SupplierBankDetail(models.Model):
    supplier_id    = models.PositiveIntegerField(db_index=True)
    bank_name      = models.CharField(max_length=100, blank=True)
    account_name   = models.CharField(max_length=150, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    is_default     = models.BooleanField(default=False)

    class Meta:
        ordering = ['supplier_id', '-is_default']


class SupplierProductCategory(models.Model):
    supplier_id    = models.PositiveIntegerField(db_index=True)
    category_name  = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['supplier_id', 'category_name']


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft',              'Draft'),
        ('sent',               'Sent'),
        ('partially_received', 'Partially Received'),
        ('received',           'Received'),
        ('cancelled',          'Cancelled'),
    ]

    po_number   = models.CharField(max_length=30, unique=True, editable=False)
    supplier_id = models.PositiveIntegerField(db_index=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes       = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    created_by  = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_at  = models.DateTimeField(auto_now=True)
    updated_by  = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.po_number

    def save(self, *args, **kwargs):
        if not self.po_number:
            year  = timezone.now().year
            count = PurchaseOrder.objects.filter(created_at__year=year).count() + 1
            self.po_number = f'PO-{year}-{count:04d}'
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return sum((line.total for line in self.lines.all()), 0)


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    # PROTECT: a product with procurement history shouldn't be deletable out from
    # under a purchase order — deactivate it instead.
    product        = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    product_name   = models.CharField(max_length=100, blank=True)  # snapshot at order time
    quantity       = models.PositiveIntegerField()
    unit_cost      = models.DecimalField(max_digits=11, decimal_places=2)
    expiry_date    = models.DateField(null=True, blank=True)
    # Cumulative quantity actually received so far — deliveries often arrive short or in
    # multiple batches, so this can sit below `quantity` indefinitely (see PurchaseOrder
    # status 'partially_received') rather than the line always being all-or-nothing.
    received_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        if not self.product_name and self.product_id:
            self.product_name = self.product.descshort or self.product.desclong
        super().save(*args, **kwargs)

    @property
    def total(self):
        return self.quantity * self.unit_cost

    @property
    def remaining(self):
        return self.quantity - self.received_quantity
