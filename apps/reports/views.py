from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import timedelta
from apps.sales.models import Transaction, TransactionItem
from apps.inventory.models import Product

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today, yesterday = timezone.now().date(), timezone.now().date() - timedelta(days=1)
        tq = Transaction.objects.filter(created_at__date=today,     status='completed')
        yq = Transaction.objects.filter(created_at__date=yesterday, status='completed')
        tr = tq.aggregate(t=Sum('total'))['t'] or 0
        yr = yq.aggregate(t=Sum('total'))['t'] or 1
        return Response({
            'today_revenue':      tr,
            'revenue_change_pct': round(((tr - yr) / yr) * 100, 1),
            'today_txn_count':    tq.count(),
            'txn_change':         tq.count() - (yq.count() or 1),
            'today_avg_order':    tq.aggregate(a=Avg('total'))['a'] or 0,
            'total_products':     Product.objects.filter(is_active=True).count(),
            'low_stock_count':    Product.objects.filter(status='low_stock').count(),
            'out_of_stock_count': Product.objects.filter(status='out_of_stock').count(),
        })

class WeeklySalesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today  = timezone.now().date()
        result = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            qs  = Transaction.objects.filter(created_at__date=day, status='completed')
            result.append({
                'day':   day.strftime('%a'),
                'date':  day.isoformat(),
                'sales': qs.aggregate(t=Sum('total'))['t'] or 0,
                'txns':  qs.count(),
            })
        return Response(result)

class MonthlySalesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        result = []
        for i in range(4, -1, -1):
            month = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            qs    = Transaction.objects.filter(
                created_at__year=month.year,
                created_at__month=month.month,
                status='completed',
            )
            result.append({
                'month': month.strftime('%b'),
                'year':  month.year,
                'sales': qs.aggregate(t=Sum('total'))['t'] or 0,
                'txns':  qs.count(),
            })
        return Response(result)

class TopProductsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit  = int(request.query_params.get('limit', 5))
        period = request.query_params.get('period', 'all')
        qs     = TransactionItem.objects.filter(transaction__status='completed')
        if period == 'today':
            qs = qs.filter(transaction__created_at__date=timezone.now().date())
        elif period == 'week':
            qs = qs.filter(
                transaction__created_at__date__gte=timezone.now().date() - timedelta(days=7)
            )
        return Response(list(
            qs.values('product__id','product__name','product__sku').annotate(
                total_qty=Sum('qty'), total_revenue=Sum('line_total')
            ).order_by('-total_revenue')[:limit]
        ))

class PaymentBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'all')
        qs     = Transaction.objects.filter(status='completed')
        if period == 'today':
            qs = qs.filter(created_at__date=timezone.now().date())
        elif period == 'week':
            qs = qs.filter(
                created_at__date__gte=timezone.now().date() - timedelta(days=7)
            )
        total  = qs.aggregate(t=Sum('total'))['t'] or 1
        colors = {'cash':'#1A9E5C','card':'#1A5FD6','gcash':'#D68910','maya':'#C0392B'}
        return Response([{
            'method':     label,
            'amount':     qs.filter(pay_method=m).aggregate(t=Sum('total'))['t'] or 0,
            'percentage': round(
                ((qs.filter(pay_method=m).aggregate(t=Sum('total'))['t'] or 0) / total) * 100, 1
            ),
            'color': colors[m],
        } for m, label in [('card','Card'),('cash','Cash'),('gcash','GCash'),('maya','Maya')]])

class CategoryRevenueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs    = TransactionItem.objects.filter(transaction__status='completed')
        qs    = qs.values('product__category__name').annotate(
            revenue=Sum('line_total'), units=Sum('qty')
        ).order_by('-revenue')
        total = sum(r['revenue'] for r in qs if r['revenue'])
        return Response([{
            'category':   r['product__category__name'] or 'Uncategorized',
            'revenue':    r['revenue'],
            'units':      r['units'],
            'percentage': round((r['revenue'] / total) * 100, 1) if total else 0,
        } for r in qs])
