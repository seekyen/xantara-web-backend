from django.db import migrations, models
import django.db.models.deletion


def link_locations(apps, schema_editor):
    Branch = apps.get_model('branches', 'Branch')
    StockBranch = apps.get_model('inventory', 'Branch')
    alias = schema_editor.connection.alias
    StockBranch.objects.using(alias).get_or_create(code='MAIN', defaults={'name': 'Head Office / Warehouse / Commissary', 'active': True})
    linked = set()
    for branch in Branch.objects.using(alias).order_by('pk'):
        candidates = list(StockBranch.objects.using(alias).filter(name__iexact=branch.name).exclude(code='MAIN').exclude(pk__in=linked))
        if len(candidates) == 1:
            location = candidates[0]
        else:
            code = f'BR{branch.pk:06d}'
            suffix = 0
            while StockBranch.objects.using(alias).filter(code=code).exists():
                suffix += 1
                code = f'B{branch.pk:05d}{suffix:04d}'
            location = StockBranch.objects.using(alias).create(code=code, name=branch.name, address=branch.address[:255], active=branch.is_active)
        linked.add(location.pk)
        Branch.objects.using(alias).filter(pk=branch.pk).update(inventory_branch_id=location.pk)


class Migration(migrations.Migration):
    dependencies = [('branches', '0001_initial'), ('inventory', '0006_inventoryprofile_inventoryrevision')]
    operations = [
        migrations.AddField(model_name='branch', name='inventory_branch', field=models.OneToOneField(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='managed_branch', to='inventory.branch')),
        migrations.RunPython(link_locations, migrations.RunPython.noop),
    ]
