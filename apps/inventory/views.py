from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Product, Category
from .serializers import ProductSerializer, ProductWriteSerializer, CategorySerializer, StockAdjustSerializer
from utils.permissions import IsAdminOrManager

class CategoryViewSet(viewsets.ModelViewSet):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['name']
    ordering           = ['name']

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['category','status','is_active']
    search_fields      = ['name','sku']
    ordering_fields    = ['name','price','stock','sold','created_at']
    ordering           = ['name']

    def get_queryset(self):
        return Product.objects.select_related('category').filter(is_active=True)

    def get_serializer_class(self):
        if self.action in ('create','update','partial_update'):
            return ProductWriteSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ('create','update','partial_update','destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        product           = self.get_object()
        product.is_active = False
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def adjust_stock(self, request, pk=None):
        product    = self.get_object()
        serializer = StockAdjustSerializer(data=request.data)
        if serializer.is_valid():
            new_stock = product.stock + serializer.validated_data['adjustment']
            if new_stock < 0:
                return Response({'error': 'Stock cannot be negative'}, status=400)
            product.stock = new_stock
            product.save()
            return Response(ProductSerializer(product).data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs          = Product.objects.filter(is_active=True)
        total_value = sum(p.price * p.stock for p in qs)
        return Response({
            'total_products':        qs.count(),
            'in_stock':              qs.filter(status='in_stock').count(),
            'low_stock':             qs.filter(status='low_stock').count(),
            'out_of_stock':          qs.filter(status='out_of_stock').count(),
            'total_inventory_value': total_value,
        })

    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        qs = Product.objects.filter(
            status__in=['low_stock','out_of_stock'], is_active=True
        ).select_related('category')
        return Response(ProductSerializer(qs, many=True).data)
