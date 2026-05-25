from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Customer
from .serializers import CustomerSerializer

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
