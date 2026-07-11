from django.db import transaction
from django.db.models import F, FloatField, ExpressionWrapper, Sum
from django.core.exceptions import ValidationError

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Branch, Category, Product, ProductStock, StockMovement
from .serializers import (
    BranchSerializer,
    CategorySerializer,
    ProductSerializer, ProductWriteSerializer,
    ProductStockSerializer, ProductStockWriteSerializer,
    StockMovementSerializer,
    StockAdjustSerializer, StockDeductSerializer, StockTransferSerializer,
)
from utils.permissions import IsAdminOrManager


# ---------------------------------------------------------------------------
# Branch
# ---------------------------------------------------------------------------

class BranchViewSet(viewsets.ModelViewSet):
    queryset           = Branch.objects.all()
    serializer_class   = BranchSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [SearchFilter, OrderingFilter]
    search_fields      = ['code', 'name']
    ordering           = ['code']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        branch        = self.get_object()
        branch.active = False
        branch.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategoryViewSet(viewsets.ModelViewSet):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['name']
    ordering           = ['name']


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['deptcode', 'classcode', 'categorycode', 'active', 'suppliercode']
    search_fields      = ['itemcode', 'itemcode2', 'descshort', 'desclong']
    ordering_fields    = ['itemcode', 'descshort', 'sell_price_rp']
    ordering           = ['itemcode']

    def get_queryset(self):
        return Product.objects.filter(active=True)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ProductWriteSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        product        = self.get_object()
        product.active = False
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # GET /products/{pk}/stock/
    # Returns all branch stock levels for a product
    # ------------------------------------------------------------------
    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        product = self.get_object()
        qs      = ProductStock.objects.filter(itemcode=product.itemcode)
        return Response(ProductStockSerializer(qs, many=True).data)

    # ------------------------------------------------------------------
    # GET /products/stats/
    # Migrated from your original — now aggregates across ProductStock
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def stats(self, request):
        products    = Product.objects.filter(active=True)
        stock_qs    = ProductStock.objects.filter(itemcode__in=products.values('itemcode'))

        total_value = (
            stock_qs
            .annotate(
                line_val=ExpressionWrapper(
                    F('stock_sa') * F('sell_price_rp'),
                    output_field=FloatField()
                )
            )
            .aggregate(total=Sum('line_val'))['total'] or 0
        )

        below_rop = (
            stock_qs
            .filter(stock_rop__gt=0)
            .annotate(
                total_stk=ExpressionWrapper(
                    F('stock_sa') + F('stock_sr'),
                    output_field=FloatField()
                )
            )
            .filter(total_stk__lt=F('stock_rop'))
            .values('itemcode')
            .distinct()
            .count()
        )

        return Response({
            'total_products':        products.count(),
            'below_rop':             below_rop,
            'total_inventory_value': total_value,
        })

    # ------------------------------------------------------------------
    # GET /products/low_stock_alerts/
    # Migrated — now queries ProductStock per branch
    # ------------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        branch_code = request.query_params.get('branch_code')

        qs = ProductStock.objects.filter(stock_rop__gt=0).annotate(
            total_stk=ExpressionWrapper(
                F('stock_sa') + F('stock_sr'),
                output_field=FloatField()
            )
        ).filter(total_stk__lt=F('stock_rop'))

        if branch_code:
            qs = qs.filter(branch_code=branch_code)

        return Response(ProductStockSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# ProductStock
# ---------------------------------------------------------------------------

class ProductStockViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['itemcode', 'branch_code']
    search_fields      = ['itemcode', 'branch_code']
    ordering           = ['branch_code', 'itemcode']

    def get_queryset(self):
        return ProductStock.objects.all()

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ProductStockWriteSerializer
        return ProductStockSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    # ------------------------------------------------------------------
    # POST /stock/{pk}/adjust/
    # Your original adjust_stock — now operates on ProductStock
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def adjust(self, request, pk=None):
        stock_record = self.get_object()
        serializer   = StockAdjustSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        adjustment = serializer.validated_data['adjustment']
        location   = serializer.validated_data.get('location', 'sa')
        reason     = serializer.validated_data.get('reason', '')
        field      = 'stock_sa' if location == 'sa' else 'stock_sr'
        new_qty    = getattr(stock_record, field) + adjustment

        if new_qty < 0:
            return Response({'error': 'Stock cannot go negative.'}, status=400)

        with transaction.atomic():
            locked = ProductStock.objects.select_for_update().get(pk=stock_record.pk)
            setattr(locked, field, new_qty)
            locked.save(update_fields=[field, 'updated_at'])

            StockMovement.record(
                product_stock=locked,
                movement_type='adjustment',
                qty=adjustment,
                location=location,
                remarks=reason,
                created_by=str(request.user),
            )

        return Response(ProductStockSerializer(locked).data)

    # ------------------------------------------------------------------
    # POST /stock/deduct/
    # Atomic sale deduction with row lock
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def deduct(self, request):
        serializer = StockDeductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        d = serializer.validated_data

        try:
            with transaction.atomic():
                stock_record = (
                    ProductStock.objects
                    .select_for_update()
                    .get(itemcode=d['itemcode'], branch_code=d['branch_code'])
                )
                stock_record.deduct(d['qty'], location=d['location'])

                StockMovement.record(
                    product_stock=stock_record,
                    movement_type='sale',
                    qty=-d['qty'],
                    location=d['location'],
                    ref_no=d.get('ref_no', ''),
                    remarks=d.get('remarks', ''),
                    created_by=d.get('created_by', str(request.user)),
                )

        except ProductStock.DoesNotExist:
            return Response(
                {'error': f"No stock record for {d['itemcode']} @ {d['branch_code']}."},
                status=404
            )
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

        return Response(ProductStockSerializer(stock_record).data)

    # ------------------------------------------------------------------
    # POST /stock/transfer/
    # Branch-to-branch stock transfer — two locked rows, one transaction
    # ------------------------------------------------------------------
    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrManager])
    def transfer(self, request):
        serializer = StockTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        d = serializer.validated_data

        try:
            with transaction.atomic():
                # Lock both rows in consistent order (by pk) to avoid deadlocks
                records = (
                    ProductStock.objects
                    .select_for_update()
                    .filter(
                        itemcode=d['itemcode'],
                        branch_code__in=[d['from_branch_code'], d['to_branch_code']]
                    )
                    .order_by('pk')
                )

                stock_map = {r.branch_code: r for r in records}

                if d['from_branch_code'] not in stock_map:
                    raise ValidationError(
                        f"No stock record for {d['itemcode']} @ {d['from_branch_code']}."
                    )
                if d['to_branch_code'] not in stock_map:
                    raise ValidationError(
                        f"No stock record for {d['itemcode']} @ {d['to_branch_code']}."
                    )

                src = stock_map[d['from_branch_code']]
                dst = stock_map[d['to_branch_code']]

                src.deduct(d['qty'], location=d['location'])
                dst.restock(d['qty'], location=d['location'])

                StockMovement.record(
                    product_stock=src,
                    movement_type='transfer_out',
                    qty=-d['qty'],
                    location=d['location'],
                    ref_no=d.get('ref_no', ''),
                    remarks=d.get('remarks', ''),
                    created_by=d.get('created_by', str(request.user)),
                )
                StockMovement.record(
                    product_stock=dst,
                    movement_type='transfer_in',
                    qty=d['qty'],
                    location=d['location'],
                    ref_no=d.get('ref_no', ''),
                    remarks=d.get('remarks', ''),
                    created_by=d.get('created_by', str(request.user)),
                )

        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

        return Response({
            'from': ProductStockSerializer(src).data,
            'to':   ProductStockSerializer(dst).data,
        })


# ---------------------------------------------------------------------------
# StockMovement (read-only — movements are created via deduct/adjust/transfer)
# ---------------------------------------------------------------------------

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['itemcode', 'branch_code', 'movement_type', 'location']
    search_fields      = ['itemcode', 'branch_code', 'ref_no']
    ordering_fields    = ['created_at', 'movement_type']
    ordering           = ['-created_at']

    def get_queryset(self):
        qs          = StockMovement.objects.all()
        branch_code = self.request.query_params.get('branch_code')
        itemcode    = self.request.query_params.get('itemcode')
        if branch_code:
            qs = qs.filter(branch_code=branch_code)
        if itemcode:
            qs = qs.filter(itemcode=itemcode)
        return qs