from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet, SupplierAddressViewSet, SupplierContactViewSet,
    SupplierBankDetailViewSet, SupplierProductCategoryViewSet,
    PurchaseOrderViewSet,
)

router = DefaultRouter()
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('supplier-addresses', SupplierAddressViewSet, basename='supplier-address')
router.register('supplier-contacts', SupplierContactViewSet, basename='supplier-contact')
router.register('supplier-bank-details', SupplierBankDetailViewSet, basename='supplier-bank-detail')
router.register('supplier-product-categories', SupplierProductCategoryViewSet, basename='supplier-product-category')
router.register('purchase-orders', PurchaseOrderViewSet, basename='purchase-order')

urlpatterns = [path('', include(router.urls))]
