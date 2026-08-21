from django.apps import AppConfig


class SyncingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.syncing'
    verbose_name = 'Premium synchronization'
