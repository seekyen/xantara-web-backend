from django.db import migrations
from datetime import date


def preserve_existing_batches(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    Stock = apps.get_model('inventory', 'ProductStock')
    Profile = apps.get_model('inventory', 'InventoryProfile')
    Batch = apps.get_model('inventory', 'InventoryBatch')
    Balance = apps.get_model('inventory', 'InventoryBatchBalance')
    Movement = apps.get_model('inventory', 'InventoryBatchMovement')
    alias = schema_editor.connection.alias
    def parsed(value):
        try:
            return date.fromisoformat(value) if value else None
        except (TypeError, ValueError):
            return None
    for stock in Stock.objects.using(alias).all().iterator():
        product = Product.objects.using(alias).filter(itemcode=stock.itemcode).first()
        if not product or Balance.objects.using(alias).filter(stock=stock).exists():
            continue
        profile = Profile.objects.using(alias).filter(product=product).first()
        details = profile.branch_data.get(stock.branch_code, {}) if profile else {}
        remaining = {'sa': max(0, stock.stock_sa), 'sr': max(0, stock.stock_sr)}
        rows = list(details.get('batches', [])) + [{'lot': 'Opening stock', 'quantity': sum(remaining.values()), 'expiry': details.get('expiry_date')}]
        for index, row in enumerate(rows):
            amount = min(float(row.get('quantity', 0)), sum(remaining.values()))
            if amount <= 0:
                continue
            batch = Batch.objects.using(alias).create(product=product, number=f"OPEN-{stock.pk}-{index + 1}: {row.get('lot', '')}"[:80],
                received_date=parsed(details.get('last_restocked')), expiry_date=parsed(row.get('expiry') or row.get('expiry_date')),
                unit_cost_centavos=max(0, round(float(product.unitcost or 0) * 100)))
            for location in ('sa', 'sr'):
                moved = min(amount, remaining[location])
                if moved:
                    Balance.objects.using(alias).create(batch=batch, stock=stock, location=location, quantity=moved)
                    Movement.objects.using(alias).create(batch=batch, branch_code=stock.branch_code, kind='opening',
                        quantity=moved, quantity_before=0, quantity_after=moved, reason='Preserved existing balance; missing dates remain unknown.',
                        reference='BATCH-OPENING', actor='migration')
                    remaining[location] -= moved
                    amount -= moved


class Migration(migrations.Migration):
    dependencies = [('inventory', '0008_inventorybatch_inventorybatchbalance_and_more')]
    operations = [migrations.RunPython(preserve_existing_batches, migrations.RunPython.noop)]
