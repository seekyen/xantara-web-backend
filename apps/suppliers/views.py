from datetime import date, datetime, time
from uuid import uuid4
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.inventory.batches import receive_stock
from .models import (
    Supplier, SupplierAddress, SupplierContact,
    SupplierBankDetail, SupplierProductCategory,
    PurchaseOrder,
)
from .serializers import (
    SupplierSerializer, SupplierAddressSerializer, SupplierContactSerializer,
    SupplierBankDetailSerializer, SupplierProductCategorySerializer,
    PurchaseOrderSerializer, PurchaseOrderCreateSerializer, PurchaseOrderReceiveSerializer,
)

class SupplierViewSet(viewsets.ModelViewSet):
    queryset           = Supplier.objects.all()
    serializer_class   = SupplierSerializer
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['supplier_type', 'is_active', 'is_accredited', 'is_vat_registered']
    search_fields      = ['company_name', 'supplier_code', 'trade_name']
    ordering_fields    = ['company_name', 'supplier_code', 'created_at', 'rating']
    ordering           = ['company_name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Soft delete: suppliers are referenced by procurement history, so they're
        # deactivated rather than removed. Returns the updated object (200), not 204.
        supplier = self.get_object()
        supplier.is_active = False
        supplier.updated_by = request.user
        supplier.save()
        return Response(self.get_serializer(supplier).data)


class SupplierAddressViewSet(viewsets.ModelViewSet):
    queryset           = SupplierAddress.objects.all()
    serializer_class   = SupplierAddressSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['supplier_id', 'address_type']


class SupplierContactViewSet(viewsets.ModelViewSet):
    queryset           = SupplierContact.objects.all()
    serializer_class   = SupplierContactSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['supplier_id']


class SupplierBankDetailViewSet(viewsets.ModelViewSet):
    queryset           = SupplierBankDetail.objects.all()
    serializer_class   = SupplierBankDetailSerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['supplier_id']


class SupplierProductCategoryViewSet(viewsets.ModelViewSet):
    queryset           = SupplierProductCategory.objects.all()
    serializer_class   = SupplierProductCategorySerializer
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['supplier_id']


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['supplier_id', 'status']
    search_fields      = ['po_number']
    ordering_fields    = ['created_at', 'po_number']
    ordering           = ['-created_at']

    def get_queryset(self):
        return PurchaseOrder.objects.prefetch_related('lines__product')

    def get_serializer_class(self):
        return PurchaseOrderCreateSerializer if self.action == 'create' else PurchaseOrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        po = serializer.save()
        return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        po = self.get_object()
        if po.status != 'draft':
            return Response({'error': 'Only draft purchase orders can be sent.'}, status=400)
        po.status = 'sent'
        po.updated_by = request.user
        po.save()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        po = self.get_object()
        if po.status not in ('draft', 'sent'):
            return Response({'error': 'Only a draft or sent purchase order can be cancelled.'}, status=400)
        po.status = 'cancelled'
        po.updated_by = request.user
        po.save()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Records an actual delivery against this PO. Deliveries are frequently short
        or split across trips, so callers send only the lines (and quantities) that
        actually showed up this time — not every line has to be present, and a line's
        quantity can be less than what's still outstanding. The PO stays open
        ('partially_received') until every line's cumulative received_quantity catches
        up to what was ordered; `close` lets a user finalize it early instead."""
        po = self.get_object()
        if po.status not in ('sent', 'partially_received'):
            return Response({'error': 'Only a sent or partially received purchase order can receive stock.'}, status=400)

        serializer = PurchaseOrderReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        received_date = (data.get('received_date') or timezone.localdate()).isoformat()

        with db_transaction.atomic():
            lines_by_id = {line.id: line for line in po.lines.select_for_update()}
            total_received = 0
            for entry in data['lines']:
                line = lines_by_id.get(entry['id'])
                if not line:
                    return Response({'error': f"Line {entry['id']} does not belong to this purchase order."}, status=400)
                if entry['quantity_received'] > line.remaining:
                    return Response({'error': f"{line.product_name}: cannot receive {entry['quantity_received']}, "
                                               f"only {line.remaining} still outstanding."}, status=400)
                total_received += entry['quantity_received']

            if total_received <= 0:
                return Response({'error': 'No quantities were received.'}, status=400)

            for entry in data['lines']:
                qty = entry['quantity_received']
                if qty <= 0:
                    continue
                line = lines_by_id[entry['id']]
                # Prefer the expiry entered now (what's actually on the delivered goods)
                # over whatever guess was made when the PO was created, if any.
                expiry_date = entry.get('expiry_date', line.expiry_date)
                receive_stock(line.product_id, {
                    'number':        f'{po.po_number}-L{line.id}-{uuid4().hex[:6]}',
                    'quantity':      qty,
                    'received_date': received_date,
                    'expiry_date':   expiry_date,
                    'unit_cost':     line.unit_cost,
                    'reason':        f'Purchase Order {po.po_number} received',
                }, actor=str(request.user), supplier_id=po.supplier_id)
                line.received_quantity += qty
                line.save(update_fields=['received_quantity'])

            # lines_by_id holds the objects we just mutated — po.lines.all() would instead
            # return get_object()'s stale prefetch cache from before this update.
            fully_received = all(l.received_quantity >= l.quantity for l in lines_by_id.values())
            po.status = 'received' if fully_received else 'partially_received'
            if fully_received:
                # The date the delivery actually happened, as entered — not the moment
                # this request happened to be processed (they can differ, e.g. backdating
                # a receipt that was recorded a day late).
                po.received_at = timezone.make_aware(datetime.combine(date.fromisoformat(received_date), time.min))
            po.updated_by = request.user
            po.save()

        # Drop the stale prefetched `lines` so the response reflects what was just saved.
        if hasattr(po, '_prefetched_objects_cache'):
            po._prefetched_objects_cache.pop('lines', None)
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Finalizes a PO as done even though some lines never fully arrived — for when
        the supplier confirms the shortfall isn't coming. Whatever was actually received
        stays on record via each line's received_quantity."""
        po = self.get_object()
        if po.status not in ('sent', 'partially_received'):
            return Response({'error': 'Only a sent or partially received purchase order can be closed.'}, status=400)
        po.status = 'received'
        po.received_at = timezone.now()
        po.updated_by = request.user
        po.save()
        return Response(PurchaseOrderSerializer(po).data)
