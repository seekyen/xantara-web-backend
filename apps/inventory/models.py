from django.db import models
from django.core.exceptions import ValidationError


class Branch(models.Model):
    code       = models.CharField(max_length=10, unique=True, db_index=True)
    name       = models.CharField(max_length=100)
    address    = models.CharField(max_length=255, blank=True)
    active     = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'branch'
        ordering            = ['code']
        verbose_name_plural = 'branches'

    def __str__(self):
        return f"{self.code} — {self.name}"


class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'category'
        ordering            = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Product(models.Model):

    # Identity / Codes
    itemcode      = models.CharField(max_length=15, unique=True, db_index=True)
    itemcode2     = models.CharField(max_length=15, blank=True, db_index=True)
    itemcode3     = models.CharField(max_length=15, blank=True, db_index=True)
    itemcode3type = models.CharField(max_length=10, blank=True)

    # Description
    desclong  = models.CharField(max_length=50, blank=True)
    descshort = models.CharField(max_length=25, blank=True, db_index=True)
    querytext = models.CharField(max_length=15, blank=True)

    # Classification
    categorycode    = models.CharField(max_length=10, blank=True, db_index=True)
    deptcode        = models.CharField(max_length=10, blank=True, db_index=True)
    classcode       = models.CharField(max_length=10, blank=True, db_index=True)
    subcategorycode = models.CharField(max_length=10, blank=True)
    group           = models.CharField(max_length=10, blank=True)

    # Variants
    size      = models.CharField(max_length=10, blank=True)
    color     = models.CharField(max_length=10, blank=True)
    style     = models.CharField(max_length=12, blank=True)
    item_type = models.CharField(max_length=10, blank=True)
    form      = models.CharField(max_length=10, blank=True)

    # Selling — Prices
    sell_price_rp = models.FloatField(default=0.0)
    sell_price_ws = models.FloatField(default=0.0)
    sell_price2   = models.FloatField(default=0.0)
    sell_price3   = models.FloatField(default=0.0)
    sell_price4   = models.FloatField(default=0.0)
    sell_price5   = models.FloatField(default=0.0)
    sell_lastdate = models.DateField(null=True, blank=True)

    # Selling — UOM / Packaging
    sell_uom       = models.CharField(max_length=10, blank=True)
    sell_pack      = models.CharField(max_length=10, blank=True)
    sell_packconv  = models.FloatField(default=0.0)
    sell_dimension = models.CharField(max_length=12, blank=True)
    sell_weight    = models.CharField(max_length=12, blank=True)

    # Selling — Quantity Breaks
    sell_quantity1 = models.FloatField(default=0.0)
    sell_quantity2 = models.FloatField(default=0.0)
    sell_quantity3 = models.FloatField(default=0.0)
    sell_quantity4 = models.FloatField(default=0.0)

    # Promotional Pricing
    pro_allowed  = models.BooleanField(default=False)
    pro_datefr   = models.DateField(null=True, blank=True)
    pro_timefr   = models.CharField(max_length=10, blank=True)
    pro_dateto   = models.DateField(null=True, blank=True)
    pro_timeto   = models.CharField(max_length=10, blank=True)
    pro_priceret = models.FloatField(default=0.0)
    pro_pricewhl = models.FloatField(default=0.0)
    pro_cost     = models.FloatField(default=0.0)

    # Supplier
    suppliercode = models.CharField(max_length=10, blank=True, db_index=True)

    # Costing
    markup_rp   = models.FloatField(default=0.0)
    markup_ws   = models.FloatField(default=0.0)
    acqcost     = models.FloatField(default=0.0)
    unitcost    = models.FloatField(default=0.0)
    unitcostave = models.FloatField(default=0.0)

    # Accounting / Tax
    taxcode     = models.CharField(max_length=10, blank=True)
    glcode      = models.CharField(max_length=10, blank=True)
    invcode     = models.CharField(max_length=10, blank=True)
    pricetype   = models.CharField(max_length=10, blank=True)
    barcodetype = models.CharField(max_length=10, blank=True)

    # Item Behavior Flags
    trackinventory = models.BooleanField(default=False)
    active         = models.BooleanField(default=True)
    withserial     = models.BooleanField(default=False)
    generic        = models.BooleanField(default=False)
    measured       = models.BooleanField(default=False)
    withalias      = models.BooleanField(default=False)
    expirydate     = models.BooleanField(default=False)
    lotnumber      = models.BooleanField(default=False)
    withautoconv   = models.BooleanField(default=False)

    # Misc
    slowfactor    = models.SmallIntegerField(default=0)
    fastfactor    = models.SmallIntegerField(default=0)
    minwhlsaleqty = models.FloatField(default=0.0)
    picturefile   = models.CharField(max_length=15, blank=True)
    image         = models.ImageField(upload_to='products/', blank=True, null=True)
    planerid      = models.CharField(max_length=10, blank=True)
    buyerid       = models.CharField(max_length=10, blank=True)
    printto       = models.CharField(max_length=10, blank=True)
    info1         = models.CharField(max_length=10, blank=True)
    info2         = models.CharField(max_length=10, blank=True)
    tag           = models.CharField(max_length=10, blank=True)

    # Audit
    createdby   = models.CharField(max_length=10, blank=True)
    createddate = models.DateField(null=True, blank=True)
    updatedby   = models.CharField(max_length=10, blank=True)
    updateddate = models.DateField(null=True, blank=True)

    # Stock (merged back from ProductStock — single store-wide value, no per-branch split)
    stock_sa       = models.FloatField(default=0.0)
    stock_book_sa  = models.FloatField(default=0.0)
    beg_balance_sa = models.FloatField(default=0.0)
    stock_sr       = models.FloatField(default=0.0)
    stock_book_sr  = models.FloatField(default=0.0)
    beg_balance_sr = models.FloatField(default=0.0)
    stock_reserved = models.FloatField(default=0.0)
    stock_rop      = models.FloatField(default=0.0)
    stock_limit    = models.FloatField(default=0.0)
    stock_onorder  = models.FloatField(default=0.0)
    beg_cost       = models.FloatField(default=0.0)

    class Meta:
        db_table = 'product'
        ordering = ['itemcode']
        indexes  = [
            models.Index(fields=['itemcode2'],                                   name='idx_product_sku'),
            models.Index(fields=['descshort'],                                   name='idx_product_descshort'),
            models.Index(fields=['suppliercode', 'itemcode'],                    name='idx_product_supplier'),
            models.Index(fields=['deptcode', 'classcode', 'itemcode'],           name='idx_product_dept'),
            models.Index(fields=['categorycode', 'subcategorycode', 'itemcode'], name='idx_product_category'),
            models.Index(fields=['itemcode3', 'itemcode3type'],                  name='idx_product_altcode'),
        ]

    def __str__(self):
        return f"{self.itemcode} — {self.descshort}"

    @property
    def is_on_promo(self):
        from django.utils import timezone
        if not self.pro_allowed:
            return False
        today = timezone.now().date()
        if self.pro_datefr and today < self.pro_datefr:
            return False
        if self.pro_dateto and today > self.pro_dateto:
            return False
        return True


class ProductStock(models.Model):
    # No FKs — linked by codes
    itemcode    = models.CharField(max_length=15, db_index=True)
    branch_code = models.CharField(max_length=10, db_index=True)

    # Sales area (SA)
    stock_sa       = models.FloatField(default=0.0)
    stock_book_sa  = models.FloatField(default=0.0)
    beg_balance_sa = models.FloatField(default=0.0)

    # Store room (SR)
    stock_sr       = models.FloatField(default=0.0)
    stock_book_sr  = models.FloatField(default=0.0)
    beg_balance_sr = models.FloatField(default=0.0)

    # Control
    stock_reserved = models.FloatField(default=0.0)
    stock_rop      = models.FloatField(default=0.0)
    stock_limit    = models.FloatField(default=0.0)
    stock_onorder  = models.FloatField(default=0.0)
    beg_cost       = models.FloatField(default=0.0)

    # Audit
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'product_stock'
        unique_together = [('itemcode', 'branch_code')]
        indexes         = [
            models.Index(fields=['branch_code', 'itemcode'], name='idx_stock_branch_item'),
        ]

    def __str__(self):
        return f"{self.itemcode} @ {self.branch_code}"

    @property
    def total_stock(self):
        return self.stock_sa + self.stock_sr

    @property
    def available_stock(self):
        from .batches import stock_summary
        return stock_summary(self)['sellable']

    @property
    def is_below_rop(self):
        return self.stock_rop > 0 and self.total_stock < self.stock_rop

    def deduct(self, qty, location='sa'):
        """
        Deduct qty from stock_sa or stock_sr.
        Call inside atomic() with select_for_update() on the queryset.
        Raises ValidationError if insufficient stock.
        """
        if location not in ('sa', 'sr') or qty <= 0:
            raise ValidationError('Choose a valid storage area and positive quantity.')
        from .batches import consume_batches
        consume_batches(self, qty, location)
        if location == 'sa':
            if self.stock_sa < qty:
                raise ValidationError(
                    f"Insufficient SA stock for {self.itemcode} @ {self.branch_code}. "
                    f"Available: {self.stock_sa}, requested: {qty}"
                )
            self.stock_sa -= qty
        elif location == 'sr':
            if self.stock_sr < qty:
                raise ValidationError(
                    f"Insufficient SR stock for {self.itemcode} @ {self.branch_code}. "
                    f"Available: {self.stock_sr}, requested: {qty}"
                )
            self.stock_sr -= qty
        else:
            raise ValueError(f"Invalid location '{location}'. Use 'sa' or 'sr'.")
        self.save(update_fields=['stock_sa', 'stock_sr', 'updated_at'])

    def restock(self, qty, location='sa'):
        """Add qty back — used for returns, receiving, adjustments."""
        if location == 'sa':
            self.stock_sa += qty
        elif location == 'sr':
            self.stock_sr += qty
        else:
            raise ValueError(f"Invalid location '{location}'. Use 'sa' or 'sr'.")
        self.save(update_fields=['stock_sa', 'stock_sr', 'updated_at'])


class StockMovement(models.Model):

    MOVEMENT_TYPES = [
        ('sale',         'Sale'),
        ('return',       'Customer return'),
        ('void',         'Void / cancel'),
        ('receive',      'Stock receiving'),
        ('adjustment',   'Manual adjustment'),
        ('transfer_in',  'Transfer in'),
        ('transfer_out', 'Transfer out'),
        ('write_off',    'Write-off / damage'),
    ]

    LOCATION_CHOICES = [
        ('sa', 'Sales area'),
        ('sr', 'Store room'),
    ]

    # No FKs — linked by codes
    itemcode      = models.CharField(max_length=15, db_index=True)
    branch_code   = models.CharField(max_length=10, db_index=True)

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, db_index=True)
    location      = models.CharField(max_length=10, choices=LOCATION_CHOICES, default='sa')

    # Signed qty: negative = out, positive = in
    qty        = models.FloatField()
    qty_before = models.FloatField()
    qty_after  = models.FloatField()

    # Reference — sale order no, PO no, transfer doc, etc.
    ref_no   = models.CharField(max_length=30, blank=True, db_index=True)
    remarks  = models.CharField(max_length=255, blank=True)

    # Audit
    created_by = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'stock_movement'
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['itemcode', 'branch_code', 'created_at'], name='idx_movement_item_branch_date'),
            models.Index(fields=['movement_type', 'created_at'],           name='idx_movement_type_date'),
            models.Index(fields=['ref_no'],                                name='idx_movement_ref'),
        ]

    def __str__(self):
        return (
            f"{self.movement_type} | {self.itemcode} @ {self.branch_code} "
            f"| qty={self.qty} | {self.created_at:%Y-%m-%d %H:%M}"
        )

    @classmethod
    def record(cls, product_stock, movement_type, qty, location='sa',
               ref_no='', remarks='', created_by=''):
        """
        Factory method — always use this to create movement records.
        Captures qty_before / qty_after from the live ProductStock instance.
        """
        qty_before = (
            product_stock.stock_sa if location == 'sa' else product_stock.stock_sr
        )
        qty_after = qty_before + qty  # qty is signed

        return cls.objects.create(
            itemcode=product_stock.itemcode,
            branch_code=product_stock.branch_code,
            movement_type=movement_type,
            location=location,
            qty=qty,
            qty_before=qty_before,
            qty_after=qty_after,
            ref_no=ref_no,
            remarks=remarks,
            created_by=created_by,
        )

class InventoryProfile(models.Model):
    product = models.OneToOneField(Product, on_delete=models.PROTECT, related_name='inventory_profile')
    tier = models.CharField(max_length=12, default='basic')
    data = models.JSONField(default=dict)
    branch_data = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    # Deliberately its own column, not part of `data` — `data` is round-tripped whole
    # through the tiered editor's save flow (merged with whatever the client sends), so
    # anything computed/backend-managed placed in there leaks back in as a phantom
    # "unknown field" on the next save. This is backend bookkeeping only.
    last_purchase_supplier_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'inventory_profile'


class InventoryRevision(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='inventory_revisions')
    branch_code = models.CharField(max_length=10)
    revision = models.PositiveIntegerField()
    actor = models.CharField(max_length=100)
    reason = models.CharField(max_length=255)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_revision'
        ordering = ['-created_at', '-pk']
        constraints = [models.UniqueConstraint(fields=['product', 'revision'], name='unique_inventory_revision')]

class InventoryBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_batches')
    number = models.CharField(max_length=80)
    received_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    unit_cost_centavos = models.PositiveBigIntegerField(default=0)
    # A batch is always stocked in its minimum/base UOM, while these fields retain
    # how the supplier delivered and priced it (for example 2 boxes x 12 bottles).
    base_uom = models.CharField(max_length=10, default='pc')
    purchase_uom = models.CharField(max_length=10, default='pc')
    package_quantity = models.PositiveIntegerField(default=1)
    units_per_package = models.PositiveIntegerField(default=1)
    package_cost_centavos = models.PositiveBigIntegerField(default=0)
    pricing_factors = models.JSONField(default=list)
    markup_percent = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    vat_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    selling_price_centavos = models.PositiveBigIntegerField(default=0)
    # Plain id (not a FK) matching how this codebase already references suppliers
    # elsewhere — set when this batch came from a Purchase Order; null for ad-hoc/manual
    # receipts, which have no traceable supplier.
    supplier_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['product', 'number'], name='unique_product_batch')]


class InventoryBatchBalance(models.Model):
    batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, related_name='balances')
    stock = models.ForeignKey(ProductStock, on_delete=models.PROTECT, related_name='batch_balances')
    location = models.CharField(max_length=2, choices=[('sa', 'Sales area'), ('sr', 'Store room')], default='sa')
    quantity = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['batch', 'stock', 'location'], name='unique_batch_stock_location'),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name='batch_quantity_nonnegative'),
        ]


class InventoryBatchMovement(models.Model):
    batch = models.ForeignKey(InventoryBatch, on_delete=models.PROTECT, related_name='movements')
    branch_code = models.CharField(max_length=10)
    kind = models.CharField(max_length=20)
    quantity = models.FloatField()
    quantity_before = models.FloatField()
    quantity_after = models.FloatField()
    reason = models.CharField(max_length=255)
    reference = models.CharField(max_length=30)
    actor = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
