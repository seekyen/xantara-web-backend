from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreSettingsView, CategoryViewSet, SubCategoryViewSet, DepartmentViewSet

router = DefaultRouter()
router.register('categories',    CategoryViewSet,    basename='category')
router.register('sub-categories', SubCategoryViewSet, basename='sub-category')
router.register('departments',   DepartmentViewSet,  basename='department')

urlpatterns = [
    path('settings/', StoreSettingsView.as_view()),
    path('', include(router.urls)),
]
