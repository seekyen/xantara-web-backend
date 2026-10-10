from django.db import migrations


def carry_unallocated_stock(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    ProductStock = apps.get_model('inventory', 'ProductStock')
    Movement = apps.get_model('inventory', 'StockMovement')
    alias = schema_editor.connection.alias
    for product in Product.objects.using(alias).all().iterator():
        # Existing location balances are authoritative. Never copy an aggregate
        # into MAIN when this product already has any location allocation.
        if ProductStock.objects.using(alias).filter(itemcode=product.itemcode).exists():
            continue
        if not product.stock_sa and not product.stock_sr:
            continue
        ProductStock.objects.using(alias).create(itemcode=product.itemcode, branch_code='MAIN',
            stock_sa=product.stock_sa, stock_sr=product.stock_sr, stock_rop=product.stock_rop,
            stock_reserved=product.stock_reserved)
        for location, quantity in [('sa', product.stock_sa), ('sr', product.stock_sr)]:
            if quantity:
                Movement.objects.using(alias).create(itemcode=product.itemcode, branch_code='MAIN',
                    movement_type='adjustment', location=location, qty=quantity, qty_before=0,
                    qty_after=quantity, ref_no='MAIN-OPENING',
                    remarks='Preserved existing unallocated product balance in central inventory.', created_by='migration')


class Migration(migrations.Migration):
    dependencies = [('inventory', '0006_inventoryprofile_inventoryrevision'), ('branches', '0002_inventory_branch')]
    operations = [migrations.RunPython(carry_unallocated_stock, migrations.RunPython.noop)]
