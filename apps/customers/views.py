from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Count
from django.utils import timezone
from utils.permissions import IsAdminOrManagerOrReadOnly
from .models import Customer, LoyaltyPromo
from .serializers import CustomerSerializer, LoyaltyEntrySerializer, LoyaltyPromoSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset           = Customer.objects.all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['status']
    search_fields      = ['name','email','phone']
    ordering_fields    = ['name','total_spent','total_orders','last_visit','joined_at']
    ordering           = ['name']

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        customer = self.get_object()
        from apps.sales.models import Transaction
        from apps.sales.serializers import TransactionSerializer
        txns = Transaction.objects.filter(customer=customer).order_by('-created_at')[:20]
        return Response(TransactionSerializer(txns, many=True).data)

    @action(detail=True, methods=['get'])
    def loyalty(self, request, pk=None):
        """The customer's most recent points ledger rows (earned and reversed)."""
        entries = self.get_object().loyalty_entries.select_related('transaction', 'sync_event')[:50]
        return Response(LoyaltyEntrySerializer(entries, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs         = Customer.objects.all()
        this_month = timezone.now().replace(day=1).date()
        agg        = qs.filter(total_spent__gt=0).aggregate(s=Sum('total_spent'), c=Count('id'))
        avg        = (agg['s'] / agg['c']) if agg['c'] else 0
        return Response({
            'total':              qs.count(),
            'active':             qs.filter(status='active').count(),
            'inactive':           qs.filter(status='inactive').count(),
            'new_this_month':     qs.filter(joined_at__date__gte=this_month).count(),
            'avg_lifetime_value': round(avg, 2),
        })


class LoyaltyPromoViewSet(viewsets.ModelViewSet):
    queryset           = LoyaltyPromo.objects.all()
    serializer_class   = LoyaltyPromoSerializer
    permission_classes = [IsAdminOrManagerOrReadOnly]
    pagination_class   = None


class LoyaltyPosSyncView(APIView):
    """One compact download for a POS device: active customers (with their current balance) and the
    promos that are still running or coming up, so a cashier can attach a customer offline."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customers = Customer.objects.filter(status='active').order_by('name', 'id').values(
            'id', 'name', 'phone', 'email', 'loyalty_points')
        promos = LoyaltyPromo.objects.filter(is_active=True, end_date__gte=timezone.localdate()).order_by('start_date', 'id')
        return Response({'customers': list(customers), 'promos': LoyaltyPromoSerializer(promos, many=True).data})
