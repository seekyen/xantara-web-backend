from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Avg
from django.utils import timezone
from .models import Transaction
from .serializers import TransactionSerializer, TransactionCreateSerializer
from utils.permissions import IsAdminOrManager

class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['status','pay_method','cashier','branch']
    search_fields      = ['txn_no','cashier__name','customer__name']
    ordering_fields    = ['created_at','total']
    ordering           = ['-created_at']

    def get_queryset(self):
        return Transaction.objects.select_related(
            'cashier','customer','branch'
        ).prefetch_related('items__product')

    def get_serializer_class(self):
        return TransactionCreateSerializer if self.action == 'create' else TransactionSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        txn = s.save()
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def refund(self, request, pk=None):
        txn = self.get_object()
        if txn.status != 'completed':
            return Response({'error': 'Only completed transactions can be refunded'}, status=400)
        txn.status = 'refunded'
        txn.save()
        for item in txn.items.all():
            if item.product:
                item.product.stock += item.qty
                item.product.sold  -= item.qty
                item.product.save()
        return Response(TransactionSerializer(txn).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def void(self, request, pk=None):
        txn = self.get_object()
        if txn.status != 'pending':
            return Response({'error': 'Only pending transactions can be voided'}, status=400)
        txn.status = 'voided'
        txn.save()
        return Response(TransactionSerializer(txn).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        today = timezone.now().date()
        qs    = Transaction.objects.filter(created_at__date=today, status='completed')
        return Response({
            'today_revenue':   qs.aggregate(t=Sum('total'))['t'] or 0,
            'today_txn_count': qs.count(),
            'today_avg_order': qs.aggregate(a=Avg('total'))['a'] or 0,
            'today_refunds':   Transaction.objects.filter(
                created_at__date=today, status='refunded').count(),
        })
