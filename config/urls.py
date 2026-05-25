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
