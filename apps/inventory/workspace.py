"""Tiered inventory document API. Stock changes and history commit atomically."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from utils.permissions import IsAdminOrManager
from .models import Branch, Product, ProductStock, StockMovement, InventoryProfile, InventoryRevision

SCHEMA = json.loads(Path(__file__).with_name('inventory_schema.json').read_text(encoding='utf-8'))
TIERS = [tier['key'] for tier in SCHEMA['tiers']]
FIELD_KEYS = {field['key'] for field in SCHEMA['fields']}
CORE = {'name': 'desclong', 'sku': 'itemcode', 'barcode': 'itemcode2', 'category': 'categorycode',
        'unit': 'sell_uom', 'selling_price': 'sell_price_rp', 'cost_price': 'unitcost',
        'supplier': 'suppliercode', 'subcategory': 'subcategorycode', 'wholesale_price': 'sell_price_ws',
        'reorder_level': 'stock_rop', 'tax_category': 'taxcode'}


def validate_fields(data, fields):
    if not isinstance(data, dict):
        raise serializers.ValidationError('Expected an inventory object.')
    unknown = set(data) - {field['key'] for field in fields}
    if unknown:
        raise serializers.ValidationError(f'Unknown fields: {", ".join(sorted(unknown))}')
    cleaned = {}
    for field in fields:
        key, kind = field['key'], field['type']
        value = data.get(key, field.get('default'))
        if value is None or value == '':
            if field.get('required'):
                raise serializers.ValidationError({key: 'Required.'})
            continue
        try:
            if kind in ('money', 'decimal', 'integer'):
                if isinstance(value, bool):
                    raise ValueError()
                number = Decimal(str(value))
                if not number.is_finite() or number < 0 or number > Decimal('999999999'):
                    raise ValueError()
                if field.get('positive') and number <= 0:
                    raise ValueError()
                if 'max' in field and number > field['max']:
                    raise ValueError()
                if kind == 'integer' and number != number.to_integral_value():
                    raise ValueError()
                if kind == 'money' and number != number.quantize(Decimal('.01')):
                    raise ValueError()
                cleaned[key] = int(number) if kind == 'integer' else format(number, '.2f' if kind == 'money' else 'f')
            elif kind == 'rows':
                if not isinstance(value, list) or len(value) > 500:
                    raise ValueError()
                cleaned[key] = [validate_fields(row, field['fields']) for row in value]
            elif kind == 'boolean':
                if not isinstance(value, bool):
                    raise ValueError()
                cleaned[key] = value
            elif kind == 'date':
                cleaned[key] = serializers.DateField().run_validation(value).isoformat()
            elif kind == 'url':
                cleaned[key] = serializers.URLField().run_validation(value)
            else:
                if not isinstance(value, str) or len(value) > field.get('maxLength', 255):
                    raise ValueError()
                if kind == 'select' and value not in field['options']:
                    raise ValueError()
                cleaned[key] = value.strip()
        except (ValueError, InvalidOperation):
            raise serializers.ValidationError({key: 'Enter a valid non-negative value within the field limits.'})
    for row in cleaned.get('price_tiers', []):
        if row.get('effective_from') and row.get('effective_to') and row['effective_to'] < row['effective_from']:
            raise serializers.ValidationError({'price_tiers': 'End date must follow start date.'})
    for key, identity in [('units', 'unit'), ('batches', 'lot')]:
        identifiers = [row[identity].casefold() for row in cleaned.get(key, [])]
        if len(identifiers) != len(set(identifiers)):
            raise serializers.ValidationError({key: 'Duplicate identifiers are not allowed.'})
    return cleaned


def document(product, branch_code):
    from .batches import stock_summary
    profile = InventoryProfile.objects.filter(product=product).first()
    data = dict(profile.data) if profile else {}
    for key, column in CORE.items():
        if key not in data:
            value = getattr(product, column)
            data[key] = str(value) if isinstance(value, float) else value
    data['sku'] = product.itemcode
    data['name'] = data.get('name') or product.descshort or product.itemcode
    data['unit'] = data.get('unit') or 'pc'
    # A real uploaded file (set via the Products endpoint's multipart image upload)
    # takes precedence over the manually-typed external URL, if one was ever entered.
    if product.image:
        data['image_url'] = product.image.url
    if data.get('tax_category') not in ('vat12', 'vat_exempt', 'zero_rated', 'non_vat'):
        data['tax_category'] = 'vat12'
    stock = ProductStock.objects.filter(itemcode=product.itemcode, branch_code=branch_code).first()
    data['quantity'] = stock.total_stock if stock else 0
    data['reorder_level'] = stock.stock_rop if stock else 0
    # Location and lot allocations belong to the selected branch.
    if profile:
        data.update(profile.branch_data.get(branch_code, {}))
    price = Decimal(str(data.get('selling_price') or 0))
    cost = Decimal(str(data.get('cost_price') or 0))
    landed = cost + sum((Decimal(row['amount']) for row in data.get('landed_costs', [])), Decimal(0))
    # Values stored for fields the schema no longer defines (older purchasing/serial/location
    # blocks) are ignored, not returned: the editor round-trips `data` whole on save and the
    # strict validator would reject them as unknown fields. They are dropped on the next save.
    data = {key: value for key, value in data.items() if key in FIELD_KEYS}
    # Lazy import: apps.suppliers.models already imports Product from here, so a
    # module-level import would be circular.
    from apps.suppliers.models import Supplier
    supplier_id = profile.last_purchase_supplier_id if profile else None
    # Top-level, like `stock`/`margin_percent` — never inside `data`, which the tiered
    # editor's save flow round-trips whole; a computed field placed in `data` comes back
    # as a phantom "unknown field" on the very next save.
    last_purchase_supplier = (
        Supplier.objects.filter(pk=supplier_id).values_list('company_name', flat=True).first()
        if supplier_id else None
    )
    return {'id': product.pk, 'branch': branch_code, 'tier': profile.tier if profile else 'basic',
            'revision': profile.revision if profile else 0, 'data': data,
            'stock': stock_summary(stock), 'last_purchase_supplier': last_purchase_supplier,
            'margin_percent': str(((price - landed) / price * 100).quantize(Decimal('.01'))) if price else None,
            'landed_unit_cost': str(landed), 'low_stock': data['quantity'] <= float(data.get('reorder_level') or 0)}


@transaction.atomic
def save_document(payload, actor, product=None):
    branch_code = payload.get('branch', 'MAIN')
    if not Branch.objects.filter(code=branch_code, active=True).exists():
        raise serializers.ValidationError({'branch': 'Choose an active branch.'})
    if branch_code != 'MAIN':
        raise serializers.ValidationError({'branch': 'Product definitions and receiving belong to Main Inventory. Distribute stock to branches instead.'})
    tier = payload.get('tier', 'basic')
    if tier not in TIERS:
        raise serializers.ValidationError({'tier': 'Choose Basic, Standard, Medium or Large.'})
    data = validate_fields(payload.get('data', {}), SCHEMA['fields'])
    reason = str(payload.get('reason', '')).strip()
    if not reason or len(reason) > 255:
        raise serializers.ValidationError({'reason': 'Provide a change reason of up to 255 characters.'})
    if product:
        product = Product.objects.select_for_update().get(pk=product.pk)
        if data.get('sku') and data['sku'] != product.itemcode:
            raise serializers.ValidationError({'sku': 'Existing product codes cannot change because stock history references them.'})
    else:
        sku = data.get('sku') or f'ITM{uuid4().hex[:12].upper()}'
        if Product.objects.filter(itemcode=sku).exists():
            raise serializers.ValidationError({'sku': 'This SKU already exists. Open the existing product.'})
        # A new product's barcode starts out equal to its SKU (typed or generated) unless one was given.
        if not data.get('barcode'):
            data['barcode'] = sku
        product = Product.objects.create(itemcode=sku, descshort=data['name'][:25])
    profile, _ = InventoryProfile.objects.get_or_create(product=product)
    if payload.get('revision', 0) != profile.revision:
        raise serializers.ValidationError({'revision': 'This product changed elsewhere. Reload before saving.'})
    stock, _ = ProductStock.objects.get_or_create(itemcode=product.itemcode, branch_code=branch_code)
    stock = ProductStock.objects.select_for_update().get(pk=stock.pk)
    before = document(product, branch_code)
    quantity = data.get('quantity', stock.total_stock)
    if quantity != stock.total_stock and payload.get('expected_quantity') != stock.total_stock:
        raise serializers.ValidationError({'quantity': 'Stock changed since this form opened. Reload before changing stock.'})
    if sum(row.get('quantity', 0) for row in data.get('batches', [])) > quantity:
        raise serializers.ValidationError({'batches': 'Batch quantities cannot exceed stock on hand.'})
    delta = quantity - stock.total_stock
    if delta:
        # Consolidate this explicitly edited balance into the sales area.
        for location, new_value in [('sr', 0), ('sa', quantity)]:
            old = getattr(stock, f'stock_{location}')
            if new_value != old:
                StockMovement.record(stock, 'adjustment', new_value - old, location=location,
                                     remarks=reason, created_by=str(actor)[:10])
                setattr(stock, f'stock_{location}', new_value)
    stock.stock_rop = data.get('reorder_level', stock.stock_rop)
    stock.save()
    for key, column in CORE.items():
        if key in data and key not in ('sku', 'reorder_level'):
            field = Product._meta.get_field(column)
            value = data[key]
            if getattr(field, 'max_length', None):
                value = str(value)[:field.max_length]
            setattr(product, column, value)
    product.descshort = data['name'][:25]
    product.trackinventory = True
    # Legacy product list remains a projection of per-branch stock.
    stocks = ProductStock.objects.filter(itemcode=product.itemcode)
    product.stock_sa = sum(s.stock_sa for s in stocks)
    product.stock_sr = sum(s.stock_sr for s in stocks)
    product.stock_rop = data.get('reorder_level', product.stock_rop)
    product.save()
    branch_keys = ('location', 'batches', 'last_restocked', 'expiry_date')
    profile.branch_data = {**profile.branch_data, branch_code: {k: data[k] for k in branch_keys if k in data}}
    profile.data = {k: v for k, v in data.items() if k not in (*branch_keys, 'quantity', 'reorder_level')}
    profile.tier = tier
    profile.revision += 1
    profile.save()
    after = document(product, branch_code)
    InventoryRevision.objects.create(product=product, branch_code=branch_code, revision=profile.revision,
                                     actor=str(actor), reason=reason, before=before, after=after)
    return after


class LookupThrottle(UserRateThrottle):
    """Keeps online lookups (which call third-party services) modest per signed-in user."""
    scope = 'product_lookup'
    rate = '60/min'


class InventoryWorkspaceViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminOrManager]

    def list(self, request):
        branch = request.query_params.get('branch', 'MAIN')
        products = Product.objects.filter(active=True).order_by('itemcode')
        if not Branch.objects.filter(code=branch, active=True).exists():
            raise serializers.ValidationError({'branch': 'Choose an active inventory branch.'})
        if branch != 'MAIN':
            products = products.filter(itemcode__in=ProductStock.objects.filter(branch_code=branch).values('itemcode'))
        if request.query_params.get('sku'):
            products = products.filter(itemcode=request.query_params['sku'])
        return Response([document(product, branch) for product in products])

    def retrieve(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        product = get_object_or_404(Product, pk=pk, active=True)
        branch = request.query_params.get('branch', 'MAIN')
        if not Branch.objects.filter(code=branch, active=True).exists():
            raise serializers.ValidationError({'branch': 'Choose an active inventory branch.'})
        if branch != 'MAIN':
            get_object_or_404(ProductStock, itemcode=product.itemcode, branch_code=branch)
        return Response(document(product, branch))

    def create(self, request):
        return Response(save_definition(request.data, request.user.pk), status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        return Response(save_definition(request.data, request.user.pk, get_object_or_404(Product, pk=pk, active=True)))

    @action(detail=True, methods=['post'])
    def distribute(self, request, pk=None):
        return Response(distribute_stock(pk, request.data, request.user.pk))

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        from .batches import receive_stock
        return Response(receive_stock(pk, request.data, request.user.pk))

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        from .batches import archive_product
        return Response(archive_product(pk, request.data.get('reason', ''), request.user.pk))

    @action(detail=True, methods=['post'], url_path='write-off')
    def write_off(self, request, pk=None):
        from .batches import write_off
        return Response(write_off(pk, request.data, request.user.pk))

    @action(detail=True, methods=['get'], url_path='batches')
    def batches(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        from .batches import stock_summary, batch_data
        from .models import InventoryBatchMovement
        product = get_object_or_404(Product, pk=pk, active=True)
        branch = request.query_params.get('branch', 'MAIN')
        get_object_or_404(Branch, code=branch, active=True)
        stock = ProductStock.objects.filter(itemcode=product.itemcode, branch_code=branch).first()
        movements = InventoryBatchMovement.objects.filter(batch__product=product, branch_code=branch).select_related('batch')[:200]
        return Response({'stock': stock_summary(stock), 'batches': batch_data(stock), 'history': [
            {'id': m.pk, 'batch': m.batch.number, 'kind': m.kind, 'quantity': m.quantity,
             'before': m.quantity_before, 'after': m.quantity_after, 'reason': m.reason,
             'reference': m.reference, 'date': m.created_at, 'actor': m.actor} for m in movements]})

    @action(detail=False, methods=['get'], url_path='lookup', throttle_classes=[LookupThrottle])
    def lookup(self, request):
        """Online suggestions: ?barcode=&name= (barcode is tried first, then the name)."""
        from . import product_lookup
        barcode = request.query_params.get('barcode', '').strip()
        name = request.query_params.get('name', '').strip()
        if barcode and not (barcode.isdigit() and 6 <= len(barcode) <= 14):
            barcode = ''
        if not barcode and not (2 <= len(name) <= 80):
            raise serializers.ValidationError({'name': 'Enter a product name (2-80 characters) or a numeric barcode.'})
        result = product_lookup.lookup(barcode, name if 2 <= len(name) <= 80 else '')
        if not result['results'] and len(result['unavailable']) == len(product_lookup.SOURCES):
            return Response({'detail': 'Online lookup is unavailable right now. Try again later.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='lookup-image', throttle_classes=[LookupThrottle])
    def lookup_image(self, request):
        """Proxies one suggested image (allowlisted hosts only) so the browser can attach it."""
        from django.http import HttpResponse
        from . import product_lookup
        try:
            body, content_type = product_lookup.fetch_image(request.query_params.get('url', ''))
        except ValueError as error:
            raise serializers.ValidationError({'url': str(error)})
        return HttpResponse(body, content_type=content_type)

    @action(detail=True, methods=['get'], url_path='movement-report')
    def movement_report(self, request, pk=None):
        """Downloadable movement ledger: ?branch=MAIN&file=xlsx|pdf&date_from=&date_to="""
        from django.http import HttpResponse
        from django.shortcuts import get_object_or_404
        from . import movement_report as report
        product = get_object_or_404(Product, pk=pk, active=True)
        branch = request.query_params.get('branch', 'MAIN')
        get_object_or_404(Branch, code=branch, active=True)
        kind = request.query_params.get('file', 'xlsx')
        if kind not in ('xlsx', 'pdf'):
            raise serializers.ValidationError({'file': 'Choose xlsx or pdf.'})
        start, end = report.parse_range(request.query_params)
        data = report.movement_report(product, branch, start, end)
        body = report.build_xlsx(data) if kind == 'xlsx' else report.build_pdf(data)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if kind == 'xlsx' else 'application/pdf'
        name = f'stock-movements-{product.itemcode}-{branch}-{timezone.localdate():%Y%m%d}.{kind}'
        response = HttpResponse(body, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{name}"'
        return response

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        records = InventoryRevision.objects.filter(product_id=pk).order_by('-created_at', '-pk')[:100]
        return Response([{'revision': r.revision, 'branch': r.branch_code, 'actor': r.actor,
                          'reason': r.reason, 'date': r.created_at, 'before': r.before, 'after': r.after} for r in records])


class DistributionSerializer(serializers.Serializer):
    branch = serializers.CharField(max_length=10)
    quantity = serializers.IntegerField(min_value=1, max_value=999999999)
    expected_quantity = serializers.FloatField(min_value=0)
    reason = serializers.CharField(max_length=255, allow_blank=False)


@transaction.atomic
def distribute_stock(product_id, payload, actor):
    from django.shortcuts import get_object_or_404
    validator = DistributionSerializer(data=payload)
    validator.is_valid(raise_exception=True)
    values = validator.validated_data
    destination = values['branch']
    if destination == 'MAIN' or not Branch.objects.filter(code=destination, active=True).exists():
        raise serializers.ValidationError({'branch': 'Choose an active destination branch other than Main Warehouse.'})
    if not Branch.objects.filter(code='MAIN', active=True).exists():
        raise serializers.ValidationError({'branch': 'Main Warehouse is not active.'})
    product = get_object_or_404(Product.objects.select_for_update(), pk=product_id, active=True)
    source = ProductStock.objects.select_for_update().filter(itemcode=product.itemcode, branch_code='MAIN').first()
    quantity = values['quantity']
    if not source or quantity > source.available_stock:
        raise serializers.ValidationError({'quantity': 'Not enough available stock in Main Warehouse.'})
    if values['expected_quantity'] != source.total_stock:
        raise serializers.ValidationError({'quantity': 'Main Warehouse stock changed. Refresh and try again.'})
    profile, _ = InventoryProfile.objects.get_or_create(product=product)
    target, _ = ProductStock.objects.get_or_create(itemcode=product.itemcode, branch_code=destination)
    target = ProductStock.objects.select_for_update().get(pk=target.pk)
    before_main, before_branch = document(product, 'MAIN'), document(product, destination)
    reference = 'DIST-' + uuid4().hex[:20]
    from .batches import move_batches
    for location, amount in move_batches(source, target, quantity, reference, values['reason'], actor):
        StockMovement.record(source, 'transfer_out', -amount, location=location,
                             ref_no=reference, remarks=values['reason'], created_by=str(actor)[:10])
        setattr(source, 'stock_' + location, getattr(source, 'stock_' + location) - amount)
        source.save(update_fields=['stock_sa', 'stock_sr', 'updated_at'])
    StockMovement.record(target, 'transfer_in', quantity, ref_no=reference,
                         remarks=values['reason'], created_by=str(actor)[:10])
    target.restock(quantity)
    stocks = list(ProductStock.objects.filter(itemcode=product.itemcode))
    product.stock_sa = sum(stock.stock_sa for stock in stocks)
    product.stock_sr = sum(stock.stock_sr for stock in stocks)
    product.save(update_fields=['stock_sa', 'stock_sr'])
    for branch, before in [('MAIN', before_main), (destination, before_branch)]:
        profile.revision += 1
        profile.save(update_fields=['revision', 'updated_at'])
        after = document(product, branch)
        InventoryRevision.objects.create(product=product, branch_code=branch, revision=profile.revision,
                                         actor=str(actor), reason=values['reason'], before=before, after=after)
    return {'reference': reference, 'main': document(product, 'MAIN'), 'branch': document(product, destination)}


@transaction.atomic
def save_definition(payload, actor, product=None):
    """The editor cannot overwrite operational stock; receiving is explicit."""
    data = dict(payload.get('data', {}))
    if product:
        product = Product.objects.select_for_update().get(pk=product.pk)
        current = document(product, 'MAIN')
    else:
        current = {'data': {'quantity': 0}}
    if 'quantity' in data and data['quantity'] != current['data']['quantity']:
        raise serializers.ValidationError({'quantity': 'Stock is read-only. Use Receive stock or Write off.'})
    for key in ('expiry_date', 'last_restocked', 'batches'):
        if key in data and data[key] != current['data'].get(key):
            raise serializers.ValidationError({key: 'Manage batch dates through Receive stock.'})
    data = {**current['data'], **data, 'quantity': current['data']['quantity']}
    result = save_document({**payload, 'data': data, 'expected_quantity': current['data']['quantity']}, actor, product)
    if payload.get('opening_stock'):
        if product:
            raise serializers.ValidationError('Opening stock is only available when creating a product.')
        from .batches import receive_stock
        result = receive_stock(result['id'], payload['opening_stock'], actor)
    return result
