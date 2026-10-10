from .workspace import InventoryWorkspaceViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BranchViewSet,
    CategoryViewSet,
    ProductViewSet,
    ProductStockViewSet,
    StockMovementViewSet,
    PublicBranchCatalogView,
)

router = DefaultRouter()
router.register('inventory-items', InventoryWorkspaceViewSet, basename='inventory-item')
router.register('inventory-branches', BranchViewSet, basename='inventory-branch')
router.register('product-categories', CategoryViewSet,     basename='product-category')
router.register('products',           ProductViewSet,      basename='product')
router.register('stock',              ProductStockViewSet, basename='stock')
router.register('stock-movements',    StockMovementViewSet, basename='stock-movement')

urlpatterns = [
    path(
        'public/branches/<str:branch_code>/catalog/',
        PublicBranchCatalogView.as_view(),
        name='public-branch-catalog',
    ),
    path('', include(router.urls)),
]
