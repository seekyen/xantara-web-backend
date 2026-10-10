"""Receiving and batch movements. Expiry affects availability, never physical stock."""
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from .models import (Product, ProductStock, Branch, StockMovement, InventoryProfile,
                     InventoryRevision, InventoryBatch, InventoryBatchBalance, InventoryBatchMovement)


def stock_summary(stock):
    if not stock:
        return {'on_hand': 0, 'sellable': 0, 'expired': 0, 'reserved': 0, 'last_restocked': None, 'untracked': 0}
    balances = list(stock.batch_balances.select_related('batch'))
    today = timezone.localdate()
    # Expiry date is the last valid day; exclusion starts the following local day.
    expired = sum(b.quantity for b in balances if b.batch.expiry_date and b.batch.expiry_date < today)
    receipts = InventoryBatchMovement.objects.filter(branch_code=stock.branch_code,
        batch__product__itemcode=stock.itemcode, kind__in=['receive', 'opening'], batch__received_date__isnull=False)
    dates = list(receipts.values_list('batch__received_date', flat=True))
    incoming = InventoryBatchMovement.objects.filter(branch_code=stock.branch_code, batch__product__itemcode=stock.itemcode, kind='transfer_in').order_by('-created_at').first()
    if incoming:
        dates.append(timezone.localdate(incoming.created_at))
    latest = max(dates) if dates else None
    return {'on_hand': stock.total_stock, 'sellable': max(0, stock.total_stock - expired - stock.stock_reserved),
            'expired': expired, 'reserved': stock.stock_reserved,
            'untracked': max(0, stock.total_stock - sum(b.quantity for b in balances)),
            'last_restocked': latest.isoformat() if latest else None}


def batch_data(stock):
    if not stock:
        return []
    from apps.suppliers.models import Supplier
    balances = list(stock.batch_balances.select_related('batch').order_by('batch__expiry_date', 'pk'))
    supplier_ids = {b.batch.supplier_id for b in balances if b.batch.supplier_id}
    suppliers = dict(Supplier.objects.filter(pk__in=supplier_ids).values_list('pk', 'company_name'))
    return [{'id': b.pk, 'batch_id': b.batch_id, 'number': b.batch.number, 'quantity': b.quantity,
             'location': b.location, 'received_date': b.batch.received_date, 'expiry_date': b.batch.expiry_date,
             'unit_cost': str(Decimal(b.batch.unit_cost_centavos) / 100),
             'base_uom': b.batch.base_uom, 'purchase_uom': b.batch.purchase_uom,
             'package_quantity': b.batch.package_quantity, 'units_per_package': b.batch.units_per_package,
             'package_cost': str(Decimal(b.batch.package_cost_centavos) / 100),
             'pricing_factors': b.batch.pricing_factors,
             'markup_percent': str(b.batch.markup_percent), 'vat_percent': str(b.batch.vat_percent),
             'selling_price': str(Decimal(b.batch.selling_price_centavos) / 100),
             'supplier_id': b.batch.supplier_id, 'supplier': suppliers.get(b.batch.supplier_id),
             'expired': bool(b.batch.expiry_date and b.batch.expiry_date < timezone.localdate())}
            for b in balances]


class PricingFactorSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=40)
    amount = serializers.DecimalField(max_digits=11, decimal_places=2, min_value=Decimal('0'))


class ReceiveSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=80)
    quantity = serializers.IntegerField(min_value=1, max_value=999999999)
    received_date = serializers.DateField()
    expiry_date = serializers.DateField(required=False, allow_null=True)
    unit_cost = serializers.DecimalField(max_digits=11, decimal_places=2, min_value=Decimal('0'), required=False)
    reason = serializers.CharField(max_length=255)
    supplier_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    base_uom = serializers.CharField(max_length=10, required=False, default='pc')
    purchase_uom = serializers.CharField(max_length=10, required=False)
    package_quantity = serializers.IntegerField(min_value=1, max_value=999999999, required=False)
    units_per_package = serializers.IntegerField(min_value=1, max_value=999999999, required=False, default=1)
    package_cost = serializers.DecimalField(max_digits=11, decimal_places=2, min_value=Decimal('0'), required=False)
    pricing_factors = PricingFactorSerializer(many=True, required=False, default=list)
    markup_percent = serializers.DecimalField(max_digits=7, decimal_places=2, min_value=Decimal('0'), required=False, default=0)
    vat_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('100'), required=False, default=0)
    selling_price = serializers.DecimalField(max_digits=11, decimal_places=2, min_value=Decimal('0'), required=False)

    def validate(self, data):
        if data['received_date'] > timezone.localdate():
            raise serializers.ValidationError({'received_date': 'Received date cannot be in the future.'})
        if data.get('expiry_date') and data['expiry_date'] < data['received_date']:
            raise serializers.ValidationError({'expiry_date': 'Expiry cannot precede the received date.'})
        units = data.get('units_per_package', 1)
        packages = data.get('package_quantity')
        if packages is None:
            if units > 1 and data['quantity'] % units:
                raise serializers.ValidationError({'quantity': 'Total minimum units must equal whole purchase packages.'})
            packages = data['quantity'] // units
            data['package_quantity'] = packages
        if packages * units != data['quantity']:
            raise serializers.ValidationError({'quantity': 'Total minimum units must equal packages received × units per package.'})
        data['purchase_uom'] = data.get('purchase_uom') or data['base_uom']
        if 'package_cost' in data:
            data['unit_cost'] = (data['package_cost'] / units).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        elif 'unit_cost' in data:
            data['package_cost'] = (data['unit_cost'] * units).quantize(Decimal('.01'))
        else:
            raise serializers.ValidationError({'package_cost': 'Enter the amount paid per purchase unit.'})
        return data


def record_batch(balance, delta, kind, reference, reason, actor):
    InventoryBatchMovement.objects.create(batch=balance.batch, branch_code=balance.stock.branch_code,
        kind=kind, quantity=delta, quantity_before=balance.quantity, quantity_after=balance.quantity + delta,
        reference=reference, reason=reason, actor=str(actor))
    balance.quantity += delta
    balance.save(update_fields=['quantity'])


def project(product):
    stocks = list(ProductStock.objects.filter(itemcode=product.itemcode))
    product.stock_sa = sum(s.stock_sa for s in stocks)
    product.stock_sr = sum(s.stock_sr for s in stocks)
    product.save(update_fields=['stock_sa', 'stock_sr'])


def revision(product, branch, before, reason, actor):
    from .workspace import document
    profile, _ = InventoryProfile.objects.get_or_create(product=product)
    profile.revision += 1
    profile.save(update_fields=['revision', 'updated_at'])
    InventoryRevision.objects.create(product=product, branch_code=branch, revision=profile.revision,
        actor=str(actor), reason=reason, before=before, after=document(product, branch))


@transaction.atomic
def receive_stock(product_id, payload, actor, supplier_id=None):
    from .workspace import document
    validator = ReceiveSerializer(data=payload)
    validator.is_valid(raise_exception=True)
    data = validator.validated_data
    supplier_id = supplier_id or data.get('supplier_id')
    if supplier_id:
        from apps.suppliers.models import Supplier
        if not Supplier.objects.filter(pk=supplier_id).exists():
            raise serializers.ValidationError({'supplier_id': 'Choose a valid supplier.'})
    product = get_object_or_404(Product.objects.select_for_update(), pk=product_id, active=True)
    if not Branch.objects.filter(code='MAIN', active=True).exists():
        raise serializers.ValidationError('Main Warehouse must be active.')
    if InventoryBatch.objects.filter(product=product, number=data['number']).exists():
        raise serializers.ValidationError({'number': 'This receipt/batch number already exists. Use a unique receipt batch number.'})
    stock, _ = ProductStock.objects.get_or_create(itemcode=product.itemcode, branch_code='MAIN')
    stock = ProductStock.objects.select_for_update().get(pk=stock.pk)
    before = document(product, 'MAIN')
    factors = [{'type': row['type'], 'amount': str(row['amount'])} for row in data.get('pricing_factors', [])]
    batch = InventoryBatch.objects.create(product=product, number=data['number'], received_date=data['received_date'],
        expiry_date=data.get('expiry_date'), unit_cost_centavos=int(data['unit_cost'] * 100), supplier_id=supplier_id,
        base_uom=data['base_uom'], purchase_uom=data['purchase_uom'], package_quantity=data['package_quantity'],
        units_per_package=data['units_per_package'], package_cost_centavos=int(data['package_cost'] * 100),
        pricing_factors=factors, markup_percent=data['markup_percent'], vat_percent=data['vat_percent'],
        selling_price_centavos=int(data.get('selling_price', Decimal('0')) * 100))
    balance = InventoryBatchBalance.objects.create(batch=batch, stock=stock)
    reference = 'RCV-' + uuid4().hex[:20]
    record_batch(balance, data['quantity'], 'receive', reference, data['reason'], actor)
    StockMovement.record(stock, 'receive', data['quantity'], ref_no=reference, remarks=data['reason'], created_by=str(actor)[:10])
    stock.restock(data['quantity'])
    profile, _ = InventoryProfile.objects.get_or_create(product=product)
    if not before['stock']['last_restocked'] or data['received_date'].isoformat() >= before['stock']['last_restocked']:
        # Both travel together: whichever receipt is most recent wins for cost AND
        # the supplier it's attributed to (cleared to None for an untraceable manual receipt).
        # last_purchase_supplier_id is its own column, not part of `data` — see the
        # model field's comment for why it can't live in the round-tripped JSON blob.
        profile_data = {**profile.data, 'cost_price': str(data['unit_cost'])}
        if any(key in payload for key in ('base_uom', 'purchase_uom', 'units_per_package')):
            profile_data['unit'] = data['base_uom']
            profile_data['units'] = ([{'unit': data['purchase_uom'], 'factor': str(data['units_per_package'])}]
                                     if data['units_per_package'] > 1 else [])
        if 'pricing_factors' in payload:
            profile_data['landed_costs'] = factors
        if 'selling_price' in data:
            profile_data['selling_price'] = str(data['selling_price'])
        profile.data = profile_data
        profile.last_purchase_supplier_id = supplier_id
        profile.save(update_fields=['data', 'last_purchase_supplier_id'])
        product.unitcost = float(data['unit_cost'])
        product.acqcost = float(data['unit_cost'])
        product.unitcostave = float(data['unit_cost'] + sum((row['amount'] for row in data.get('pricing_factors', [])), Decimal('0')))
        update_fields = ['unitcost', 'acqcost', 'unitcostave']
        if any(key in payload for key in ('base_uom', 'purchase_uom', 'units_per_package')):
            product.sell_uom = data['base_uom']
            product.sell_pack = data['purchase_uom']
            product.sell_packconv = data['units_per_package']
            product.withautoconv = data['units_per_package'] > 1
            update_fields += ['sell_uom', 'sell_pack', 'sell_packconv', 'withautoconv']
        if 'selling_price' in data:
            product.sell_price_rp = float(data['selling_price'])
            product.markup_rp = float(data['markup_percent'])
            product.sell_lastdate = data['received_date']
            update_fields += ['sell_price_rp', 'markup_rp', 'sell_lastdate']
        if supplier_id:
            supplier_code = Supplier.objects.filter(pk=supplier_id).values_list('supplier_code', flat=True).first()
            if supplier_code:
                product.suppliercode = supplier_code
                update_fields.append('suppliercode')
        product.save(update_fields=update_fields)
    project(product)
    revision(product, 'MAIN', before, data['reason'], actor)
    return document(product, 'MAIN')


class WriteOffSerializer(serializers.Serializer):
    branch = serializers.CharField(max_length=10)
    balance_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=999999999)
    expected_quantity = serializers.FloatField(min_value=0)
    reason = serializers.CharField(max_length=255)


@transaction.atomic
def write_off(product_id, payload, actor):
    from .workspace import document
    validator = WriteOffSerializer(data=payload)
    validator.is_valid(raise_exception=True)
    data = validator.validated_data
    product = get_object_or_404(Product.objects.select_for_update(), pk=product_id, active=True)
    stock = get_object_or_404(ProductStock.objects.select_for_update(), itemcode=product.itemcode, branch_code=data['branch'])
    balance = get_object_or_404(InventoryBatchBalance.objects.select_for_update().select_related('batch', 'stock'),
        pk=data['balance_id'], stock=stock, batch__product=product)
    quantity = data['quantity']
    if balance.quantity != data['expected_quantity'] or quantity > balance.quantity:
        raise serializers.ValidationError('Batch quantity changed or is insufficient. Refresh before writing off.')
    if quantity > getattr(stock, 'stock_' + balance.location):
        raise serializers.ValidationError('Physical stock is insufficient. Reconcile the stock balance first.')
    before = document(product, data['branch'])
    reference = 'WO-' + uuid4().hex[:20]
    record_batch(balance, -quantity, 'write_off', reference, data['reason'], actor)
    StockMovement.record(stock, 'write_off', -quantity, location=balance.location, ref_no=reference,
        remarks=data['reason'], created_by=str(actor)[:10])
    setattr(stock, 'stock_' + balance.location, getattr(stock, 'stock_' + balance.location) - quantity)
    stock.save(update_fields=['stock_sa', 'stock_sr', 'updated_at'])
    project(product)
    revision(product, data['branch'], before, data['reason'], actor)
    return document(product, data['branch'])


def move_batches(source, target, quantity, reference, reason, actor):
    """FEFO, then undated balances. Caller holds stock locks and a transaction."""
    if quantity > stock_summary(source)['sellable']:
        raise serializers.ValidationError('Insufficient unexpired, unreserved stock for distribution.')
    remaining = quantity
    allocations = []
    balances = list(source.batch_balances.select_for_update().select_related('batch', 'stock').filter(quantity__gt=0)
        .order_by(F('batch__expiry_date').asc(nulls_last=True), 'batch__received_date', 'pk'))
    for location in ('sa', 'sr'):
        if sum(b.quantity for b in balances if b.location == location) > getattr(source, 'stock_' + location):
            raise serializers.ValidationError('Batch balances exceed physical stock. Reconcile before distribution.')
    for balance in balances:
        if balance.batch.expiry_date and balance.batch.expiry_date < timezone.localdate():
            continue
        amount = min(remaining, balance.quantity)
        if amount:
            allocations.append((balance.location, amount))
            dest, _ = InventoryBatchBalance.objects.get_or_create(batch=balance.batch, stock=target, location='sa')
            record_batch(balance, -amount, 'transfer_out', reference, reason, actor)
            record_batch(dest, amount, 'transfer_in', reference, reason, actor)
            remaining -= amount
    # Legacy/untracked stock remains undated, without inventing an expiry.
    for location in ('sa', 'sr'):
        tracked = sum(b.quantity for b in balances if b.location == location)
        already = sum(amount for loc, amount in allocations if loc == location)
        available = max(0, getattr(source, 'stock_' + location) - tracked - already)
        amount = min(remaining, available)
        if amount:
            allocations.append((location, amount))
            remaining -= amount
    if remaining:
        raise serializers.ValidationError('Batch allocations do not match physical stock. Reconcile before distribution.')
    return allocations

def consume_batches(stock, quantity, location):
    """Batch-aware stock deduction used by the online stock API."""
    from django.core.exceptions import ValidationError
    if quantity > stock_summary(stock)['sellable']:
        raise ValidationError('Insufficient unexpired, unreserved stock.')
    balances = list(stock.batch_balances.select_for_update().select_related('batch', 'stock').filter(location=location, quantity__gt=0)
                    .order_by(F('batch__expiry_date').asc(nulls_last=True), 'batch__received_date', 'pk'))
    total_tracked = sum(b.quantity for b in balances)
    physical = getattr(stock, 'stock_' + location)
    expired = sum(b.quantity for b in balances if b.batch.expiry_date and b.batch.expiry_date < timezone.localdate())
    if total_tracked > physical or quantity > physical - expired:
        raise ValidationError('Insufficient valid batch stock in this storage area.')
    remaining = quantity
    reference = 'USE-' + uuid4().hex[:20]
    for balance in balances:
        if balance.batch.expiry_date and balance.batch.expiry_date < timezone.localdate():
            continue
        amount = min(remaining, balance.quantity)
        if amount:
            record_batch(balance, -amount, 'deduct', reference, 'Stock deduction', 'stock-api')
            remaining -= amount


@transaction.atomic
def archive_product(product_id, reason, actor):
    """Hide a product without erasing history. Refused while any branch still holds stock."""
    from .workspace import document
    reason = (reason or '').strip()
    if not reason or len(reason) > 255:
        raise serializers.ValidationError({'reason': 'Provide a reason of up to 255 characters.'})
    product = get_object_or_404(Product.objects.select_for_update(), pk=product_id, active=True)
    stocks = list(ProductStock.objects.select_for_update().filter(itemcode=product.itemcode))
    held = [(s.branch_code, s.total_stock) for s in stocks if s.total_stock > 0]
    if held:
        detail = ', '.join(f'{branch}: {quantity:g}' for branch, quantity in held)
        raise serializers.ValidationError({'stock': f'Stock is still on hand ({detail}). Write off or transfer it before archiving.'})
    before = document(product, 'MAIN')
    product.active = False
    product.save(update_fields=['active'])
    revision(product, 'MAIN', before, 'Archived: ' + reason, actor)
    return {'id': product.pk, 'archived': True}
