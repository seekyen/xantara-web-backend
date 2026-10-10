import uuid

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import StoreSettings, Category, SubCategory, Department, Class, Size, Color, Unit, Form, ItemType
from .serializers import (
    StoreSettingsSerializer, InitialSetupSerializer, CategorySerializer,
    SubCategorySerializer, DepartmentSerializer,
    ClassSerializer, SizeSerializer, ColorSerializer,
    UnitSerializer, FormSerializer, ItemTypeSerializer,
)
from apps.accounts.models import Staff
from apps.branches.models import Branch as ManagedBranch
from apps.branches.serializers import BranchSerializer
from apps.inventory.models import Branch as InventoryBranch
from apps.syncing.models import SyncInstallation
from apps.accounts.serializers import StaffMeSerializer
from utils.permissions import IsAdminOrManager


def _setup_status(settings):
    company = None
    if settings.setup_completed:
        company = {
            'name': settings.store_name,
            'address': settings.address,
            'email': settings.contact_email,
            'phone': settings.contact_phone,
        }
    return {
        'setup_required': not settings.setup_completed,
        'setup_completed': settings.setup_completed,
        'business_id': settings.business_id if settings.setup_completed else '',
        'company': company,
    }


class InitialSetupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, _request):
        return Response(_setup_status(StoreSettings.get_settings()))

    def post(self, request):
        if StoreSettings.get_settings().setup_completed:
            return Response(
                {'detail': 'Initial setup has already been completed.'},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = InitialSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            StoreSettings.objects.get_or_create(pk=1)
            settings = StoreSettings.objects.select_for_update().get(pk=1)
            if settings.setup_completed:
                return Response(
                    {'detail': 'Initial setup has already been completed.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if Staff.objects.exists() or ManagedBranch.objects.exists():
                return Response(
                    {'detail': 'Existing staff or branches must be migrated before setup can continue.'},
                    status=status.HTTP_409_CONFLICT,
                )

            business_base = slugify(data['company_name']) or 'company'
            business_id = f'{business_base[:48]}-{uuid.uuid4().hex[:8]}'

            inventory_branch, _ = InventoryBranch.objects.get_or_create(
                code='MAIN',
                defaults={
                    'name': data['branch_name'],
                    'address': data.get('branch_address', '')[:255],
                    'active': True,
                },
            )
            inventory_branch.name = data['branch_name']
            inventory_branch.address = data.get('branch_address', '')[:255]
            inventory_branch.active = True
            inventory_branch.save(update_fields=['name', 'address', 'active', 'updated_at'])

            branch = ManagedBranch.objects.create(
                inventory_branch=inventory_branch,
                name=data['branch_name'],
                address=data.get('branch_address', ''),
                email=data.get('branch_email', ''),
                phone=data.get('branch_phone', ''),
            )
            admin = Staff.objects.create_user(
                email=data['admin_email'].lower(),
                password=data['admin_password'],
                name=data['admin_name'],
                role='admin',
                status='active',
                branch=branch,
                is_staff=True,
                avatar=''.join(
                    part[0].upper() for part in data['admin_name'].split()[:2]
                ),
            )

            SyncInstallation.objects.create(
                business_id=business_id,
                installation_id='xantara-web-main',
                terminal_id='branch-main-pos01',
                local_branch_id='branch-main',
                branch=inventory_branch,
                authorized_staff=admin,
                is_active=True,
                sync_enabled=True,
            )

            settings.business_id = business_id
            settings.store_name = data['company_name']
            settings.address = data.get('company_address', '')
            settings.contact_email = data.get('company_email', '')
            settings.contact_phone = data.get('company_phone', '')
            settings.setup_completed = True
            settings.setup_completed_at = timezone.now()
            settings.save(update_fields=[
                'business_id', 'store_name', 'address', 'contact_email',
                'contact_phone', 'setup_completed', 'setup_completed_at',
                'updated_at',
            ])

        return Response(
            {
                **_setup_status(settings),
                'branch': BranchSerializer(branch).data,
                'administrator': StaffMeSerializer(admin).data,
            },
            status=status.HTTP_201_CREATED,
        )


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
