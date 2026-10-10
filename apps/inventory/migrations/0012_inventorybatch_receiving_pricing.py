from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_inventoryprofile_last_purchase_supplier_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventorybatch',
            name='base_uom',
            field=models.CharField(default='pc', max_length=10),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='purchase_uom',
            field=models.CharField(default='pc', max_length=10),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='package_quantity',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='units_per_package',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='package_cost_centavos',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='pricing_factors',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='markup_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='vat_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='inventorybatch',
            name='selling_price_centavos',
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
