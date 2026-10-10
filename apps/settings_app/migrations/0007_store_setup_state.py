from django.db import migrations, models
from django.utils import timezone


def initialize_setup_state(apps, schema_editor):
    StoreSettings = apps.get_model('settings_app', 'StoreSettings')
    Staff = apps.get_model('accounts', 'Staff')
    Branch = apps.get_model('branches', 'Branch')

    has_existing_installation = Staff.objects.exists() or Branch.objects.exists()
    settings, _ = StoreSettings.objects.get_or_create(pk=1)
    if has_existing_installation:
        settings.business_id = settings.business_id or 'xantara'
        settings.setup_completed = True
        settings.setup_completed_at = settings.setup_completed_at or timezone.now()
        settings.save(update_fields=[
            'business_id', 'setup_completed', 'setup_completed_at', 'updated_at',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_pin_biometric'),
        ('branches', '0002_inventory_branch'),
        ('settings_app', '0006_class_color_form_itemtype_size_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='storesettings',
            name='business_id',
            field=models.CharField(blank=True, max_length=64, unique=True),
        ),
        migrations.AddField(
            model_name='storesettings',
            name='setup_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='storesettings',
            name='setup_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(initialize_setup_state, migrations.RunPython.noop),
    ]
