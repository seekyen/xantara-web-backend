from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, LoyaltyPosSyncView, LoyaltyPromoViewSet

router = DefaultRouter()
router.register('customers', CustomerViewSet, basename='customer')
router.register('loyalty/promos', LoyaltyPromoViewSet, basename='loyalty-promo')
urlpatterns = [
    path('loyalty/pos-sync/', LoyaltyPosSyncView.as_view(), name='loyalty-pos-sync'),
    path('', include(router.urls)),
]
