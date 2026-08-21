from django.urls import path

from .views import SyncEventUploadView


urlpatterns = [
    path('sync/events/', SyncEventUploadView.as_view(), name='sync-event-upload'),
]
