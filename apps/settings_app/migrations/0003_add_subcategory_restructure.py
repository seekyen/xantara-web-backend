import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0002_add_category_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='category',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RemoveField(
            model_name='category',
            name='sub_category',
        ),
        migrations.RemoveField(
            model_name='category',
            name='is_active',
        ),
        migrations.CreateModel(
            name='SubCategory',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code',       models.CharField(max_length=4, unique=True)),
                ('name',       models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category',   models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='subcategories',
                    to='settings_app.category',
                )),
            ],
            options={
                'verbose_name_plural': 'sub categories',
                'ordering': ['code'],
            },
        ),
    ]
