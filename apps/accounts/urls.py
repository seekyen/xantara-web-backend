from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, MeView, StaffViewSet, PinLoginView, BiometricLoginView

router = DefaultRouter()
router.register('staff', StaffViewSet, basename='staff')

urlpatterns = [
    path('auth/login/',              LoginView.as_view()),
    path('auth/login/pin/',          PinLoginView.as_view()),
    path('auth/login/biometric/',    BiometricLoginView.as_view()),
    path('auth/logout/',             LogoutView.as_view()),
    path('auth/refresh/',            TokenRefreshView.as_view()),
    path('auth/me/',                 MeView.as_view()),
    path('', include(router.urls)),
]
