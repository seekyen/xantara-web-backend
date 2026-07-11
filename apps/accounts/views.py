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
from .serializers import (
    StaffSerializer, StaffCreateSerializer, StaffMeSerializer,
    ChangePasswordSerializer,
    SetPinSerializer, PinLoginSerializer,
    SetBiometricSerializer, BiometricLoginSerializer,
)
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
    def change_password(self, request, _pk=None):
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
    def toggle_status(self, request, _pk=None):
        staff           = self.get_object()
        new_status      = request.data.get('status', 'active')
        staff.status    = new_status
        staff.is_active = new_status == 'active'
        staff.save(update_fields=['status','is_active'])
        return Response({'status': staff.status})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_pin(self, request, _pk=None):
        staff = self.get_object()
        s     = SetPinSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=400)
        staff.set_pin(s.validated_data['pin'])
        staff.save(update_fields=['pin_code'])
        return Response({'message': 'PIN set successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remove_pin(self, request, _pk=None):
        staff          = self.get_object()
        staff.pin_code = ''
        staff.save(update_fields=['pin_code'])
        return Response({'message': 'PIN removed'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_biometric(self, request, _pk=None):
        staff = self.get_object()
        s     = SetBiometricSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=400)
        staff.set_biometric(s.validated_data['token'])
        staff.save(update_fields=['biometric_token', 'biometric_enabled'])
        return Response({'message': 'Biometric registered'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remove_biometric(self, request, _pk=None):
        staff = self.get_object()
        staff.clear_biometric()
        staff.save(update_fields=['biometric_token', 'biometric_enabled'])
        return Response({'message': 'Biometric removed'})


class PinLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = PinLoginSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=400)
        try:
            user = Staff.objects.get(email=s.validated_data['email'], is_active=True)
        except Staff.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=400)
        if not user.check_pin(s.validated_data['pin']):
            return Response({'error': 'Invalid PIN'}, status=400)
        refresh            = RefreshToken.for_user(user)
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        return Response({
            'refresh': str(refresh),
            'access':  str(refresh.access_token),
            'user':    StaffMeSerializer(user).data,
        })


class BiometricLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = BiometricLoginSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=400)
        try:
            user = Staff.objects.get(email=s.validated_data['email'], is_active=True)
        except Staff.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=400)
        if not user.check_biometric(s.validated_data['token']):
            return Response({'error': 'Biometric verification failed'}, status=400)
        refresh            = RefreshToken.for_user(user)
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        return Response({
            'refresh': str(refresh),
            'access':  str(refresh.access_token),
            'user':    StaffMeSerializer(user).data,
        })
