from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StoreSettingsView, CategoryViewSet, SubCategoryViewSet, DepartmentViewSet,
    ClassViewSet, SizeViewSet, ColorViewSet, UnitViewSet, FormViewSet, ItemTypeViewSet,
)

router = DefaultRouter()
router.register('categories',    CategoryViewSet,    basename='category')
router.register('sub-categories', SubCategoryViewSet, basename='sub-category')
router.register('departments',   DepartmentViewSet,  basename='department')
router.register('classes',       ClassViewSet,       basename='class')
router.register('sizes',         SizeViewSet,        basename='size')
router.register('colors',        ColorViewSet,       basename='color')
router.register('units',         UnitViewSet,        basename='unit')
router.register('forms',         FormViewSet,        basename='form')
router.register('types',         ItemTypeViewSet,    basename='type')

urlpatterns = [
    path('settings/', StoreSettingsView.as_view()),
    path('', include(router.urls)),
]
