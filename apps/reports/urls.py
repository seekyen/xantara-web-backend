from django.urls import path
from .views import (
    DashboardStatsView, WeeklySalesView, MonthlySalesView,
    TopProductsView, PaymentBreakdownView, CategoryRevenueView,
)

urlpatterns = [
    path('reports/dashboard/',         DashboardStatsView.as_view()),
    path('reports/sales/weekly/',      WeeklySalesView.as_view()),
    path('reports/sales/monthly/',     MonthlySalesView.as_view()),
    path('reports/top-products/',      TopProductsView.as_view()),
    path('reports/payment-breakdown/', PaymentBreakdownView.as_view()),
    path('reports/category-revenue/',  CategoryRevenueView.as_view()),
]
