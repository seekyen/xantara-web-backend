from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import StoreSettings, Category, SubCategory, Department, Class, Size, Color, Unit, Form, ItemType
from .serializers import (
    StoreSettingsSerializer, CategorySerializer,
    SubCategorySerializer, DepartmentSerializer,
    ClassSerializer, SizeSerializer, ColorSerializer,
    UnitSerializer, FormSerializer, ItemTypeSerializer,
)
from utils.permissions import IsAdminOrManager


class StoreSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, _request):
        return Response(StoreSettingsSerializer(StoreSettings.get_settings()).data)

    def patch(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=403)
        s = StoreSettingsSerializer(
            StoreSettings.get_settings(), data=request.data, partial=True
        )
        if s.is_valid():
            s.save()
            return Response(s.data)
        return Response(s.errors, status=400)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name', 'created_at']
    ordering         = ['code']

    def get_queryset(self):
        return Category.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        category           = self.get_object()
        category.is_active = not category.is_active
        category.save(update_fields=['is_active'])
        return Response(CategorySerializer(category).data)


class SubCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = SubCategorySerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category_code', 'is_active']
    search_fields    = ['code', 'name', 'category_code']
    ordering_fields  = ['code', 'name', 'created_at']
    ordering         = ['code']

    def get_queryset(self):
        return SubCategory.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        subcategory           = self.get_object()
        subcategory.is_active = not subcategory.is_active
        subcategory.save(update_fields=['is_active'])
        return Response(SubCategorySerializer(subcategory).data)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name', 'class_name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return Department.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        department           = self.get_object()
        department.is_active = not department.is_active
        department.save(update_fields=['is_active'])
        return Response(DepartmentSerializer(department).data)


class ClassViewSet(viewsets.ModelViewSet):
    serializer_class = ClassSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return Class.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        obj           = self.get_object()
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response(ClassSerializer(obj).data)


class SizeViewSet(viewsets.ModelViewSet):
    serializer_class = SizeSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return Size.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        obj           = self.get_object()
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response(SizeSerializer(obj).data)


class ColorViewSet(viewsets.ModelViewSet):
    serializer_class = ColorSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return Color.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        obj           = self.get_object()
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response(ColorSerializer(obj).data)


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return Unit.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        obj           = self.get_object()
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response(UnitSerializer(obj).data)


class FormViewSet(viewsets.ModelViewSet):
    serializer_class = FormSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return Form.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        obj           = self.get_object()
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response(FormSerializer(obj).data)


class ItemTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ItemTypeSerializer
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields    = ['code', 'name']
    ordering_fields  = ['code', 'name']
    ordering         = ['code']

    def get_queryset(self):
        return ItemType.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, _request, *_args, **_kwargs):
        obj           = self.get_object()
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response(ItemTypeSerializer(obj).data)