from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BranchViewSet,
    CategoryViewSet,
    ProductViewSet,
    ProductStockViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register('branches',           BranchViewSet,       basename='branch')
router.register('product-categories', CategoryViewSet,     basename='product-category')
router.register('products',           ProductViewSet,      basename='product')
router.register('stock',              ProductStockViewSet, basename='stock')
router.register('stock-movements',    StockMovementViewSet, basename='stock-movement')

urlpatterns = [path('', include(router.urls))]