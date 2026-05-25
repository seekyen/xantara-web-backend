# Django Backend Prompt — BeloPOS System
# Paste this entire file into Claude Code CLI

I have a Next.js + Tailwind frontend POS admin system already built with mock data.
Now build the Django + Django REST Framework backend. The API must match the exact
data shapes the frontend mock data already uses.

---

## STEP 1 — SCAN FIRST

Before writing any code, scan the project and output:
- Python version available
- Whether a Django project already exists or starting fresh
- Whether a virtual environment exists
- Any existing requirements.txt or pyproject.toml
- Database preference (default PostgreSQL, fallback SQLite for local dev)

List every file you will create, then wait for my confirmation.

---

## STEP 2 — PROJECT SETUP

```bash
pip install django
pip install djangorestframework
pip install django-cors-headers
pip install djangorestframework-simplejwt
pip install django-filter
pip install python-dotenv
pip install psycopg2-binary
pip install pillow
pip install django-extensions
```

Create requirements.txt with pinned versions after install.

Project structure:
```
backend/
  manage.py
  config/
    __init__.py
    settings/
      __init__.py
      base.py
      local.py
      production.py
    urls.py
    wsgi.py
    asgi.py
  apps/
    accounts/
    inventory/
    sales/
    customers/
    reports/
    branches/
    settings_app/
  utils/
    __init__.py
    pagination.py
    permissions.py
    responses.py
  .env
  .env.example
```

---

## STEP 3 — SETTINGS

### config/settings/base.py
```python
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()
BASE_DIR   = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'change-me-in-production')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'apps.accounts',
    'apps.inventory',
    'apps.sales',
    'apps.customers',
    'apps.reports',
    'apps.branches',
    'apps.settings_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF    = 'config.urls'
AUTH_USER_MODEL = 'accounts.Staff'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.StandardPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES':        ('Bearer',),
}

CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS','http://localhost:3000').split(',')
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Manila'
USE_I18N      = True
USE_TZ        = True
STATIC_URL    = '/static/'
STATIC_ROOT   = BASE_DIR / 'staticfiles'
MEDIA_URL     = '/media/'
MEDIA_ROOT    = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### config/settings/local.py
```python
from .base import *
DEBUG         = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
    }
}
CORS_ALLOW_ALL_ORIGINS = True
```

### config/settings/production.py
```python
from .base import *
DEBUG         = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.getenv('DB_NAME'),
        'USER':     os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST':     os.getenv('DB_HOST'),
        'PORT':     os.getenv('DB_PORT', '5432'),
    }
}
CORS_ALLOWED_ORIGINS        = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
SECURE_BROWSER_XSS_FILTER   = True
X_FRAME_OPTIONS             = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### .env.example
```
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.local
DB_NAME=belopos_db
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## STEP 4 — UTILS

### utils/pagination.py
```python
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class StandardPagination(PageNumberPagination):
    page_size             = 10
    page_size_query_param = 'page_size'
    max_page_size         = 100

    def get_paginated_response(self, data):
        return Response({
            'count':        self.page.paginator.count,
            'total_pages':  self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size':    self.get_page_size(self.request),
            'next':         self.get_next_link(),
            'previous':     self.get_previous_link(),
            'results':      data,
        })
```

### utils/permissions.py
```python
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('admin','manager')

class IsAdminOrManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ('GET','HEAD','OPTIONS'):
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role in ('admin','manager')
```

### utils/responses.py
```python
from rest_framework.response import Response
from rest_framework import status

def success_response(data=None, message='Success', status_code=status.HTTP_200_OK):
    return Response({'success':True,'message':message,'data':data}, status=status_code)

def error_response(message='Error', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success':False,'message':message,'errors':errors}, status=status_code)
```

---

## STEP 5 — BRANCHES APP

### apps/branches/models.py
```python
from django.db import models

class Branch(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    address    = models.TextField(blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
```

### apps/branches/serializers.py
```python
from rest_framework import serializers
from .models import Branch

class BranchSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model  = Branch
        fields = ['id','name','address','phone','email','is_active','staff_count','created_at']

    def get_staff_count(self, obj):
        return obj.staff_set.filter(status='active').count()
```

### apps/branches/views.py
```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Branch
from .serializers import BranchSerializer
from utils.permissions import IsAdminOrManager

class BranchViewSet(viewsets.ModelViewSet):
    queryset           = Branch.objects.all()
    serializer_class   = BranchSerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['name','address']
    ordering           = ['name']

    def get_permissions(self):
        if self.action in ('create','update','partial_update','destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]
```

### apps/branches/urls.py
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BranchViewSet

router = DefaultRouter()
router.register('branches', BranchViewSet, basename='branch')
urlpatterns = [path('', include(router.urls))]
```

---

## STEP 6 — ACCOUNTS APP

### apps/accounts/models.py
```python
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Staff(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin','Admin'), ('manager','Manager'),
        ('cashier','Cashier'), ('stock_clerk','Stock Clerk'),
    ]
    STATUS_CHOICES = [
        ('active','Active'), ('inactive','Inactive'), ('on_leave','On Leave'),
    ]

    email         = models.EmailField(unique=True)
    name          = models.CharField(max_length=150)
    phone         = models.CharField(max_length=20, blank=True)
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    branch        = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    avatar        = models.CharField(max_length=5, blank=True)
    sales_count   = models.PositiveIntegerField(default=0)
    last_login_at = models.DateTimeField(null=True, blank=True)
    joined_at     = models.DateField(null=True, blank=True)
    is_staff      = models.BooleanField(default=False)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    objects         = StaffManager()
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.role})'

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0].upper() for p in parts[:2])
```

### apps/accounts/serializers.py
```python
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Staff
from apps.branches.serializers import BranchSerializer

class StaffSerializer(serializers.ModelSerializer):
    branch_detail  = BranchSerializer(source='branch', read_only=True)
    role_display   = serializers.CharField(source='get_role_display',   read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    initials       = serializers.ReadOnlyField()

    class Meta:
        model  = Staff
        fields = [
            'id','name','email','phone','role','role_display',
            'branch','branch_detail','status','status_display',
            'avatar','initials','sales_count','last_login_at','joined_at','created_at',
        ]
        read_only_fields = ['sales_count','last_login_at','created_at']

class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = Staff
        fields = ['name','email','phone','role','branch','status','password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        staff    = Staff(**validated_data)
        staff.set_password(password)
        staff.avatar = ''.join(p[0].upper() for p in validated_data['name'].split()[:2])
        staff.save()
        return staff

class StaffMeSerializer(serializers.ModelSerializer):
    branch_detail = BranchSerializer(source='branch', read_only=True)

    class Meta:
        model  = Staff
        fields = ['id','name','email','phone','role','branch','branch_detail','status','initials']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
```

### apps/accounts/views.py
```python
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Staff
from .serializers import StaffSerializer, StaffCreateSerializer, ChangePasswordSerializer, StaffMeSerializer
from utils.permissions import IsAdmin, IsAdminOrManager

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = Staff.objects.filter(email=request.data.get('email')).first()
            if user:
                user.last_login_at = timezone.now()
                user.save(update_fields=['last_login_at'])
                response.data['user'] = StaffMeSerializer(user).data
        return response

class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data.get('refresh')).blacklist()
            return Response({'message': 'Logged out'})
        except Exception:
            return Response({'message': 'Token already invalid'}, status=400)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class   = StaffMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class StaffViewSet(viewsets.ModelViewSet):
    queryset           = Staff.objects.select_related('branch').all()
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['role','status','branch']
    search_fields      = ['name','email','phone']
    ordering_fields    = ['name','joined_at','sales_count']
    ordering           = ['name']

    def get_serializer_class(self):
        return StaffCreateSerializer if self.action == 'create' else StaffSerializer

    def get_permissions(self):
        if self.action in ('create','destroy'):
            return [IsAdmin()]
        if self.action in ('update','partial_update'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def change_password(self, request, pk=None):
        staff = self.get_object()
        s     = ChangePasswordSerializer(data=request.data)
        if s.is_valid():
            if not staff.check_password(s.data['old_password']):
                return Response({'error': 'Wrong password'}, status=400)
            staff.set_password(s.data['new_password'])
            staff.save()
            return Response({'message': 'Password updated'})
        return Response(s.errors, status=400)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def toggle_status(self, request, pk=None):
        staff           = self.get_object()
        new_status      = request.data.get('status', 'active')
        staff.status    = new_status
        staff.is_active = new_status == 'active'
        staff.save(update_fields=['status','is_active'])
        return Response({'status': staff.status})
```

### apps/accounts/urls.py
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, MeView, StaffViewSet

router = DefaultRouter()
router.register('staff', StaffViewSet, basename='staff')

urlpatterns = [
    path('auth/login/',   LoginView.as_view()),
    path('auth/logout/',  LogoutView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('auth/me/',      MeView.as_view()),
    path('', include(router.urls)),
]
```

---

## STEP 7 — INVENTORY APP

### apps/inventory/models.py
```python
from django.db import models

class Category(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = [
        ('in_stock','In Stock'), ('low_stock','Low Stock'), ('out_of_stock','Out of Stock'),
    ]

    name       = models.CharField(max_length=200)
    sku        = models.CharField(max_length=50, unique=True)
    category   = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                   null=True, related_name='products')
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    cost       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock      = models.PositiveIntegerField(default=0)
    max_stock  = models.PositiveIntegerField(default=50)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock')
    sold       = models.PositiveIntegerField(default=0)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'

    def save(self, *args, **kwargs):
        # Auto-compute status — never set manually
        if self.stock == 0:
            self.status = 'out_of_stock'
        elif self.stock <= 10:
            self.status = 'low_stock'
        else:
            self.status = 'in_stock'
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        return self.price * self.stock

    @property
    def profit_margin(self):
        if self.price == 0:
            return 0
        return round(((self.price - self.cost) / self.price) * 100, 1)
```

### apps/inventory/serializers.py
```python
from rest_framework import serializers
from .models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id','name','product_count','created_at']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

class ProductSerializer(serializers.ModelSerializer):
    category_name  = serializers.CharField(source='category.name', read_only=True)
    total_value    = serializers.ReadOnlyField()
    profit_margin  = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stock_percent  = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id','name','sku','category','category_name','price','cost',
            'stock','max_stock','status','status_display','sold',
            'total_value','profit_margin','stock_percent','is_active',
            'created_at','updated_at',
        ]
        read_only_fields = ['status','sold','created_at','updated_at']

    def get_stock_percent(self, obj):
        if obj.max_stock == 0:
            return 0
        return round((obj.stock / obj.max_stock) * 100)

class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Product
        fields = ['name','sku','category','price','cost','stock','max_stock','is_active']

class StockAdjustSerializer(serializers.Serializer):
    adjustment = serializers.IntegerField()
    reason     = serializers.CharField(max_length=255, required=False)
```

### apps/inventory/views.py
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Product, Category
from .serializers import ProductSerializer, ProductWriteSerializer, CategorySerializer, StockAdjustSerializer
from utils.permissions import IsAdminOrManager

class CategoryViewSet(viewsets.ModelViewSet):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['name']
    ordering           = ['name']

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['category','status','is_active']
    search_fields      = ['name','sku']
    ordering_fields    = ['name','price','stock','sold','created_at']
    ordering           = ['name']

    def get_queryset(self):
        return Product.objects.select_related('category').filter(is_active=True)

    def get_serializer_class(self):
        if self.action in ('create','update','partial_update'):
            return ProductWriteSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ('create','update','partial_update','destroy'):
            return [IsAdminOrManager()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        # Soft delete only
        product           = self.get_object()
        product.is_active = False
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def adjust_stock(self, request, pk=None):
        product    = self.get_object()
        serializer = StockAdjustSerializer(data=request.data)
        if serializer.is_valid():
            new_stock = product.stock + serializer.validated_data['adjustment']
            if new_stock < 0:
                return Response({'error': 'Stock cannot be negative'}, status=400)
            product.stock = new_stock
            product.save()
            return Response(ProductSerializer(product).data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs          = Product.objects.filter(is_active=True)
        total_value = sum(p.price * p.stock for p in qs)
        return Response({
            'total_products':        qs.count(),
            'in_stock':              qs.filter(status='in_stock').count(),
            'low_stock':             qs.filter(status='low_stock').count(),
            'out_of_stock':          qs.filter(status='out_of_stock').count(),
            'total_inventory_value': total_value,
        })

    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        qs = Product.objects.filter(
            status__in=['low_stock','out_of_stock'], is_active=True
        ).select_related('category')
        return Response(ProductSerializer(qs, many=True).data)
```

### apps/inventory/urls.py
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet

router = DefaultRouter()
router.register('products',   ProductViewSet,  basename='product')
router.register('categories', CategoryViewSet, basename='category')
urlpatterns = [path('', include(router.urls))]
```

---

## STEP 8 — CUSTOMERS APP

### apps/customers/models.py
```python
from django.db import models

class Customer(models.Model):
    STATUS_CHOICES = [('active','Active'),('inactive','Inactive')]

    name           = models.CharField(max_length=150)
    email          = models.EmailField(unique=True, blank=True, null=True)
    phone          = models.CharField(max_length=20, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_spent    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orders   = models.PositiveIntegerField(default=0)
    loyalty_points = models.PositiveIntegerField(default=0)
    last_visit     = models.DateField(null=True, blank=True)
    joined_at      = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0].upper() for p in parts[:2])
```

### apps/customers/serializers.py
```python
from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    initials       = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Customer
        fields = [
            'id','name','email','phone','status','status_display',
            'total_spent','total_orders','loyalty_points',
            'last_visit','joined_at','initials',
        ]
        read_only_fields = ['total_spent','total_orders','loyalty_points',
                            'last_visit','joined_at']
```

### apps/customers/views.py
```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Customer
from .serializers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset           = Customer.objects.all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['status']
    search_fields      = ['name','email','phone']
    ordering_fields    = ['name','total_spent','total_orders','last_visit','joined_at']
    ordering           = ['name']

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        customer = self.get_object()
        from apps.sales.models import Transaction
        from apps.sales.serializers import TransactionSerializer
        txns = Transaction.objects.filter(customer=customer).order_by('-created_at')[:20]
        return Response(TransactionSerializer(txns, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs         = Customer.objects.all()
        this_month = timezone.now().replace(day=1).date()
        agg        = qs.filter(total_spent__gt=0).aggregate(s=Sum('total_spent'), c=Count('id'))
        avg        = (agg['s'] / agg['c']) if agg['c'] else 0
        return Response({
            'total':              qs.count(),
            'active':             qs.filter(status='active').count(),
            'inactive':           qs.filter(status='inactive').count(),
            'new_this_month':     qs.filter(joined_at__date__gte=this_month).count(),
            'avg_lifetime_value': round(avg, 2),
        })
```

### apps/customers/urls.py
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet

router = DefaultRouter()
router.register('customers', CustomerViewSet, basename='customer')
urlpatterns = [path('', include(router.urls))]
```

---

## STEP 9 — SALES APP

### apps/sales/models.py
```python
from django.db import models
from apps.inventory.models import Product
from apps.customers.models import Customer
from apps.accounts.models import Staff
from apps.branches.models import Branch

class Transaction(models.Model):
    STATUS_CHOICES     = [('completed','Completed'),('refunded','Refunded'),
                          ('voided','Voided'),('pending','Pending')]
    PAY_METHOD_CHOICES = [('cash','Cash'),('card','Card'),
                          ('gcash','GCash'),('maya','Maya')]

    txn_no     = models.CharField(max_length=30, unique=True, editable=False)
    customer   = models.ForeignKey(Customer, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='transactions')
    cashier    = models.ForeignKey(Staff,    on_delete=models.SET_NULL,
                                   null=True, related_name='transactions')
    branch     = models.ForeignKey(Branch,   on_delete=models.SET_NULL,
                                   null=True, related_name='transactions')
    subtotal   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pay_method = models.CharField(max_length=10, choices=PAY_METHOD_CHOICES, default='cash')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.txn_no

    def save(self, *args, **kwargs):
        if not self.txn_no:
            from django.utils import timezone
            year       = timezone.now().year
            count      = Transaction.objects.filter(created_at__year=year).count() + 1
            self.txn_no = f'TXN-{year}-{count:05d}'
        super().save(*args, **kwargs)

class TransactionItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    product     = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name        = models.CharField(max_length=200)   # price snapshot
    sku         = models.CharField(max_length=50)    # price snapshot
    qty         = models.PositiveIntegerField(default=1)
    price       = models.DecimalField(max_digits=10, decimal_places=2)  # price snapshot
    line_total  = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_total = self.qty * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} x{self.qty}'
```

### apps/sales/serializers.py
```python
from rest_framework import serializers
from django.db import transaction as db_transaction
from .models import Transaction, TransactionItem
from apps.inventory.models import Product

class TransactionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model        = TransactionItem
        fields       = ['id','product','name','sku','qty','price','line_total']
        read_only_fields = ['line_total','name','sku']

class TransactionSerializer(serializers.ModelSerializer):
    items          = TransactionItemSerializer(many=True, read_only=True)
    cashier_name   = serializers.CharField(source='cashier.name',           read_only=True)
    customer_name  = serializers.CharField(source='customer.name',          read_only=True)
    branch_name    = serializers.CharField(source='branch.name',            read_only=True)
    status_display = serializers.CharField(source='get_status_display',     read_only=True)
    pay_display    = serializers.CharField(source='get_pay_method_display', read_only=True)

    class Meta:
        model  = Transaction
        fields = [
            'id','txn_no','customer','customer_name','cashier','cashier_name',
            'branch','branch_name','items','subtotal','discount','tax','total',
            'pay_method','pay_display','status','status_display','notes','created_at',
        ]
        read_only_fields = ['txn_no','subtotal','tax','total','created_at']

class TransactionItemWriteSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True), source='product'
    )
    qty = serializers.IntegerField(min_value=1)

class TransactionCreateSerializer(serializers.Serializer):
    from apps.customers.models import Customer as C
    customer   = serializers.PrimaryKeyRelatedField(queryset=C.objects.all(),
                                                    required=False, allow_null=True)
    items      = TransactionItemWriteSerializer(many=True)
    discount   = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    pay_method = serializers.ChoiceField(choices=['cash','card','gcash','maya'])
    notes      = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('At least one item required')
        return items

    @db_transaction.atomic
    def create(self, validated_data):
        from django.utils import timezone
        items_data = validated_data.pop('items')
        request    = self.context['request']
        TAX_RATE   = 0.12

        # Validate stock availability first
        for item_data in items_data:
            product = item_data['product']
            if product.stock < item_data['qty']:
                raise serializers.ValidationError(
                    f'Insufficient stock for {product.name}'
                )

        txn = Transaction.objects.create(
            cashier    = request.user,
            branch     = request.user.branch,
            discount   = validated_data.get('discount', 0),
            pay_method = validated_data['pay_method'],
            customer   = validated_data.get('customer'),
            notes      = validated_data.get('notes', ''),
        )

        subtotal = 0
        for item_data in items_data:
            product = item_data['product']
            qty     = item_data['qty']
            TransactionItem.objects.create(
                transaction=txn, product=product,
                name=product.name, sku=product.sku,
                qty=qty, price=product.price,
            )
            subtotal      += product.price * qty
            product.stock -= qty
            product.sold  += qty
            product.save()

        taxable      = subtotal - txn.discount
        txn.subtotal = subtotal
        txn.tax      = round(taxable * TAX_RATE, 2)
        txn.total    = taxable + txn.tax
        txn.status   = 'completed'
        txn.save()

        # Update customer totals and loyalty
        if txn.customer:
            c = txn.customer
            c.total_spent    += txn.total
            c.total_orders   += 1
            c.loyalty_points += int(txn.total // 100)
            c.last_visit      = timezone.now().date()
            c.save()

        # Update cashier sales count
        request.user.sales_count += 1
        request.user.save(update_fields=['sales_count'])

        return txn
```

### apps/sales/views.py
```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Avg
from django.utils import timezone
from .models import Transaction
from .serializers import TransactionSerializer, TransactionCreateSerializer
from utils.permissions import IsAdminOrManager

class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['status','pay_method','cashier','branch']
    search_fields      = ['txn_no','cashier__name','customer__name']
    ordering_fields    = ['created_at','total']
    ordering           = ['-created_at']

    def get_queryset(self):
        return Transaction.objects.select_related(
            'cashier','customer','branch'
        ).prefetch_related('items__product')

    def get_serializer_class(self):
        return TransactionCreateSerializer if self.action == 'create' else TransactionSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        txn = s.save()
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def refund(self, request, pk=None):
        txn = self.get_object()
        if txn.status != 'completed':
            return Response({'error': 'Only completed transactions can be refunded'}, status=400)
        txn.status = 'refunded'
        txn.save()
        for item in txn.items.all():
            if item.product:
                item.product.stock += item.qty
                item.product.sold  -= item.qty
                item.product.save()
        return Response(TransactionSerializer(txn).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def void(self, request, pk=None):
        txn = self.get_object()
        if txn.status != 'pending':
            return Response({'error': 'Only pending transactions can be voided'}, status=400)
        txn.status = 'voided'
        txn.save()
        return Response(TransactionSerializer(txn).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        today = timezone.now().date()
        qs    = Transaction.objects.filter(created_at__date=today, status='completed')
        return Response({
            'today_revenue':   qs.aggregate(t=Sum('total'))['t'] or 0,
            'today_txn_count': qs.count(),
            'today_avg_order': qs.aggregate(a=Avg('total'))['a'] or 0,
            'today_refunds':   Transaction.objects.filter(
                created_at__date=today, status='refunded').count(),
        })
```

### apps/sales/urls.py
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet

router = DefaultRouter()
router.register('transactions', TransactionViewSet, basename='transaction')
urlpatterns = [path('', include(router.urls))]
```

---

## STEP 10 — REPORTS APP

### apps/reports/views.py
```python
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
```

### apps/reports/urls.py
```python
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
```

---

## STEP 11 — SETTINGS APP

### apps/settings_app/models.py
```python
from django.db import models

class StoreSettings(models.Model):
    store_name          = models.CharField(max_length=200, default='BeloPOS')
    address             = models.TextField(blank=True)
    contact_email       = models.EmailField(blank=True)
    contact_phone       = models.CharField(max_length=20, blank=True)
    currency            = models.CharField(max_length=10, default='PHP')
    currency_symbol     = models.CharField(max_length=5, default='P')
    timezone            = models.CharField(max_length=50, default='Asia/Manila')
    vat_rate            = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    vat_inclusive       = models.BooleanField(default=False)
    show_vat_receipt    = models.BooleanField(default=True)
    receipt_header      = models.TextField(blank=True)
    receipt_footer      = models.TextField(blank=True)
    print_auto          = models.BooleanField(default=True)
    email_receipt       = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    pay_cash            = models.BooleanField(default=True)
    pay_card            = models.BooleanField(default=True)
    pay_gcash           = models.BooleanField(default=True)
    pay_maya            = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Store Settings'

    def __str__(self):
        return self.store_name

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

### apps/settings_app/views.py
```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from .models import StoreSettings

class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model   = StoreSettings
        exclude = ['id']

class StoreSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
```

### apps/settings_app/urls.py
```python
from django.urls import path
from .views import StoreSettingsView

urlpatterns = [path('settings/', StoreSettingsView.as_view())]
```

---

## STEP 12 — MAIN URLS

### config/urls.py
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

API = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),
    path(API, include('apps.accounts.urls')),
    path(API, include('apps.branches.urls')),
    path(API, include('apps.inventory.urls')),
    path(API, include('apps.customers.urls')),
    path(API, include('apps.sales.urls')),
    path(API, include('apps.reports.urls')),
    path(API, include('apps.settings_app.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## STEP 13 — SEED DATA COMMAND

### apps/accounts/management/commands/seed_data.py
```python
from django.core.management.base import BaseCommand
from apps.branches.models import Branch
from apps.accounts.models import Staff
from apps.inventory.models import Category, Product
from apps.customers.models import Customer

class Command(BaseCommand):
    help = 'Seed database with mock POS data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding branches...')
        branches = {}
        for name, addr in [
            ('Makati','Ayala Ave, Makati City'),
            ('BGC',   'BGC High Street, Taguig'),
            ('Quezon','Timog Ave, Quezon City'),
        ]:
            b, _ = Branch.objects.get_or_create(name=name, defaults={'address': addr})
            branches[name] = b

        self.stdout.write('Seeding staff...')
        for s in [
            {'email':'ck@belomed.com',   'name':'Clouie Caagbay','role':'admin',    'branch':'Makati','password':'admin123'},
            {'email':'ana@belomed.com',  'name':'Ana Reyes',     'role':'cashier',  'branch':'Makati','password':'staff123'},
            {'email':'rico@belomed.com', 'name':'Rico Santos',   'role':'cashier',  'branch':'Makati','password':'staff123'},
            {'email':'maya@belomed.com', 'name':'Maya Cruz',     'role':'manager',  'branch':'BGC',   'password':'staff123'},
        ]:
            branch = branches[s.pop('branch')]
            pwd    = s.pop('password')
            staff, created = Staff.objects.get_or_create(
                email=s['email'],
                defaults={**s, 'branch': branch, 'status': 'active'}
            )
            if created:
                staff.set_password(pwd)
                staff.avatar = ''.join(p[0].upper() for p in staff.name.split()[:2])
                staff.save()

        self.stdout.write('Seeding categories + products...')
        cats = {}
        for name in ['Footwear','Tops','Bottoms','Accessories','Bags']:
            c, _ = Category.objects.get_or_create(name=name)
            cats[name] = c

        for name, sku, cat, price, cost, stock, maxs in [
            ('Air Force 1',      'AF1-WHT-42', 'Footwear',    4250, 2100, 12, 50),
            ('Slim Fit Tee',     'SFT-BLK-M',  'Tops',         890,  380, 34,100),
            ('Cargo Shorts',     'CGS-KHK-L',  'Bottoms',     1650,  720,  3, 40),
            ('Snapback Cap',     'SBC-RED-OS',  'Accessories',  750,  280,  0, 30),
            ('Sling Bag',        'SLB-BLK-OS',  'Bags',        1290,  550,  5, 20),
            ('Sunglasses',       'SGL-BLK-OS',  'Accessories', 2100,  900, 21, 40),
            ('Polo Shirt',       'PS-WHT-L',    'Tops',        1350,  580, 45, 80),
            ('Canvas Shoes',     'CS-BLK-41',   'Footwear',    2800, 1200,  0, 30),
            ('Wrist Watch',      'WW-SLV-OS',   'Accessories', 5500, 2400,  7, 15),
            ('Jogger Pants',     'JP-BLK-M',    'Bottoms',     1750,  760, 22, 50),
        ]:
            Product.objects.get_or_create(sku=sku, defaults={
                'name':name,'category':cats[cat],
                'price':price,'cost':cost,'stock':stock,'max_stock':maxs,
            })

        self.stdout.write('Seeding customers...')
        for name, email, phone in [
            ('Maria Santos',  'maria@email.com',  '09171234567'),
            ('Jose Reyes',    'jose@email.com',   '09281234567'),
            ('Ana Cruz',      'anacruz@email.com','09391234567'),
            ('Carlo Mendoza', 'carlo@email.com',  '09451234567'),
        ]:
            Customer.objects.get_or_create(
                email=email, defaults={'name': name, 'phone': phone}
            )

        self.stdout.write(self.style.SUCCESS('Seed complete!'))
        self.stdout.write('Login: ck@belomed.com / admin123')
```

---

## STEP 14 — API REFERENCE

```
AUTH
POST   /api/v1/auth/login/                  returns access + refresh + user
POST   /api/v1/auth/logout/
POST   /api/v1/auth/refresh/
GET    /api/v1/auth/me/
PATCH  /api/v1/auth/me/

STAFF
GET    /api/v1/staff/                        filter: role, status, branch
POST   /api/v1/staff/
GET    /api/v1/staff/{id}/
PATCH  /api/v1/staff/{id}/
DELETE /api/v1/staff/{id}/
POST   /api/v1/staff/{id}/toggle_status/
POST   /api/v1/staff/{id}/change_password/

BRANCHES
GET    /api/v1/branches/
POST   /api/v1/branches/
PATCH  /api/v1/branches/{id}/

INVENTORY
GET    /api/v1/products/                     filter: category, status, search
POST   /api/v1/products/
GET    /api/v1/products/{id}/
PATCH  /api/v1/products/{id}/
DELETE /api/v1/products/{id}/                soft delete only
POST   /api/v1/products/{id}/adjust_stock/   body: { adjustment: N, reason: '' }
GET    /api/v1/products/stats/
GET    /api/v1/products/low_stock_alerts/
GET    /api/v1/categories/
POST   /api/v1/categories/

CUSTOMERS
GET    /api/v1/customers/                    filter: status, search
POST   /api/v1/customers/
GET    /api/v1/customers/{id}/
PATCH  /api/v1/customers/{id}/
DELETE /api/v1/customers/{id}/
GET    /api/v1/customers/{id}/transactions/
GET    /api/v1/customers/stats/

SALES
GET    /api/v1/transactions/                 filter: status, pay_method, cashier
POST   /api/v1/transactions/                 auto deducts stock, updates customer
GET    /api/v1/transactions/{id}/
POST   /api/v1/transactions/{id}/refund/
POST   /api/v1/transactions/{id}/void/
GET    /api/v1/transactions/stats/

REPORTS
GET    /api/v1/reports/dashboard/
GET    /api/v1/reports/sales/weekly/
GET    /api/v1/reports/sales/monthly/
GET    /api/v1/reports/top-products/         ?limit=5&period=today|week|all
GET    /api/v1/reports/payment-breakdown/    ?period=today|week|all
GET    /api/v1/reports/category-revenue/

SETTINGS
GET    /api/v1/settings/
PATCH  /api/v1/settings/
```

---

## STEP 15 — IMPLEMENTATION ORDER

Execute in this exact sequence:

1.  Scaffold project + virtual environment
2.  pip install all packages + freeze requirements.txt
3.  config/ settings + .env
4.  utils/ (pagination, permissions, responses)
5.  apps/branches/ (model, serializer, view, urls, admin)
6.  apps/accounts/ (custom user model, serializer, JWT views, urls, admin)
7.  python manage.py makemigrations accounts branches
8.  apps/inventory/ (models, serializers, views, urls, admin)
9.  apps/customers/ (models, serializers, views, urls, admin)
10. apps/sales/ (models, serializers, views, urls, admin)
11. python manage.py makemigrations inventory customers sales settings_app
12. python manage.py migrate
13. apps/reports/ (views + urls only, no models needed)
14. apps/settings_app/ (singleton model, view, urls)
15. config/urls.py wire all apps
16. Create seed_data management command
17. python manage.py seed_data
18. python manage.py runserver
19. Test every endpoint before finishing

---

## GLOBAL RULES

- All decimal/money fields: max_digits=10, decimal_places=2 — never float
- All list endpoints: pagination + search + filter required
- Stock deduction + transaction creation: always inside db_transaction.atomic()
- Product status: auto-computed in model.save() — never set from view directly
- Soft delete only for products (is_active=False) — never hard delete
- Every model: __str__, Meta.ordering, created_at, updated_at
- JWT: access=8h (one shift), refresh=7d
- Timezone: Asia/Manila
- Currency: Philippine Peso
- CORS: allow localhost:3000 dev, restrict to deployed domain in production
- Permissions: Admin=full, Manager=read+write, Cashier=read+create sales, Stock Clerk=read inventory
- No hardcoded secrets — all from .env
