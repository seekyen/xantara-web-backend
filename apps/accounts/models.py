from django.contrib.auth.hashers import make_password, check_password as check_hashed
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
    pin_code          = models.CharField(max_length=128, blank=True)
    biometric_token   = models.TextField(blank=True)
    biometric_enabled = models.BooleanField(default=False)
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

    @property
    def has_pin(self):
        return bool(self.pin_code)

    def set_pin(self, raw_pin):
        self.pin_code = make_password(str(raw_pin))

    def check_pin(self, raw_pin):
        return bool(self.pin_code) and check_hashed(str(raw_pin), self.pin_code)

    def set_biometric(self, token):
        self.biometric_token   = make_password(token)
        self.biometric_enabled = True

    def check_biometric(self, token):
        return (
            self.biometric_enabled
            and bool(self.biometric_token)
            and check_hashed(token, self.biometric_token)
        )

    def clear_biometric(self):
        self.biometric_token   = ''
        self.biometric_enabled = False
