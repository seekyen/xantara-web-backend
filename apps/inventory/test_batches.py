from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from apps.accounts.models import Staff
from apps.inventory.models import Product, Branch, ProductStock, InventoryBatch, InventoryBatchBalance, InventoryBatchMovement, StockMovement
from apps.inventory.workspace import save_document, save_definition, document, distribute_stock
from apps.inventory.batches import receive_stock, write_off, stock_summary


class BatchInventoryTests(TestCase):
    def setUp(self):
        Branch.objects.get_or_create(code='MAIN', defaults={'name': 'Main'})
        Branch.objects.create(code='DEST', name='Destination')
        self.product = Product.objects.get(pk=save_document({'reason': 'New product', 'data': {'name': 'Milk', 'quantity': 0}}, 'admin')['id'])
        self.today = timezone.localdate()

    def receive(self, number='LOT-A', quantity=30, days=5, **overrides):
        return receive_stock(self.product.pk, {'number': number, 'quantity': quantity,
            'received_date': str(self.today), 'expiry_date': str(self.today + timedelta(days=days)),
            'unit_cost': '12.50', 'reason': 'Delivery', **overrides}, 'admin')

    def test_receiving_adds_batches_and_keeps_full_movement_history(self):
        self.receive()
        result = self.receive('LOT-B', 50, 10)
        self.assertEqual(result['stock']['on_hand'], 80)
        self.assertEqual(result['stock']['sellable'], 80)
        self.assertEqual(result['stock']['last_restocked'], str(self.today))
        self.assertEqual(InventoryBatch.objects.count(), 2)
        self.assertEqual(InventoryBatch.objects.first().unit_cost_centavos, 1250)
        self.assertEqual(InventoryBatchMovement.objects.count(), 2)
        self.assertEqual(list(StockMovement.objects.order_by('pk').values_list('qty_before','qty_after')), [(0,30),(30,80)])

    def test_expiry_changes_availability_without_deleting_stock_or_rewriting_history(self):
        self.receive(days=0)
        self.receive('LOT-B', 50, 10)
        self.assertEqual(document(self.product, 'MAIN')['stock']['sellable'], 80)
        with patch('apps.inventory.batches.timezone.localdate', return_value=self.today + timedelta(days=1)):
            summary = document(self.product, 'MAIN')['stock']
            self.assertEqual((summary['on_hand'], summary['sellable'], summary['expired']), (80,50,30))
            self.assertEqual(InventoryBatchMovement.objects.count(), 2)
            with self.assertRaises(ValidationError):
                distribute_stock(self.product.pk, {'branch':'DEST','quantity':60,'expected_quantity':80,'reason':'Delivery'}, 'admin')

    def test_fefo_distribution_preserves_expiry_and_balances(self):
        self.receive('LATE', 30, 10)
        self.receive('EARLY', 50, 2)
        result = distribute_stock(self.product.pk, {'branch':'DEST','quantity':55,'expected_quantity':80,'reason':'Delivery'}, 'admin')
        self.assertEqual(result['main']['stock']['on_hand'], 25)
        self.assertEqual(result['branch']['stock']['on_hand'], 55)
        destination = InventoryBatchBalance.objects.filter(stock__branch_code='DEST')
        self.assertEqual(destination.get(batch__number='EARLY').quantity, 50)
        self.assertEqual(destination.get(batch__number='LATE').quantity, 5)
        self.assertEqual(destination.get(batch__number='EARLY').batch.expiry_date, self.today + timedelta(days=2))
        self.assertEqual(sum(InventoryBatchBalance.objects.values_list('quantity', flat=True)), 80)

    def test_writeoff_decreases_physical_expired_stock_with_reason(self):
        self.receive(days=0)
        with patch('apps.inventory.batches.timezone.localdate', return_value=self.today + timedelta(days=1)):
            balance = InventoryBatchBalance.objects.get()
            result = write_off(self.product.pk, {'branch':'MAIN','balance_id':balance.pk,'quantity':30,'expected_quantity':30,'reason':'Expired disposal'}, 'admin')
            self.assertEqual((result['stock']['on_hand'],result['stock']['expired']), (0,0))
            self.assertEqual(InventoryBatchMovement.objects.first().kind, 'write_off')
            self.assertEqual(StockMovement.objects.first().qty_after, 0)
            with self.assertRaises(ValidationError):
                write_off(self.product.pk, {'branch':'MAIN','balance_id':balance.pk,'quantity':30,'expected_quantity':30,'reason':'Retry'}, 'admin')

    def test_duplicate_receipt_does_not_add_stock_twice(self):
        self.receive()
        with self.assertRaises(ValidationError):
            self.receive()
        self.assertEqual(document(self.product, 'MAIN')['data']['quantity'], 30)

    def test_product_editor_rejects_operational_overwrites(self):
        self.receive()
        current = document(self.product, 'MAIN')
        with self.assertRaises(ValidationError):
            save_definition({**current,'reason':'Edit','data':{**current['data'],'quantity':90}}, 'admin', self.product)
        with self.assertRaises(ValidationError):
            save_definition({**current,'reason':'Edit','data':{**current['data'],'expiry_date':'2030-01-01'}}, 'admin', self.product)
        result = save_definition({**current,'reason':'Rename','data':{**current['data'],'name':'Fresh Milk'}}, 'admin', self.product)
        self.assertEqual(result['data']['quantity'], 30)

    def test_opening_receipt_and_product_are_atomic(self):
        count = Product.objects.count()
        with self.assertRaises(ValidationError):
            save_definition({'reason':'Opening','data':{'name':'New'},'opening_stock':{'number':'INVALID'}}, 'admin')
        self.assertEqual(Product.objects.count(), count)

    def test_invalid_receipt_is_rejected(self):
        for change in [{'quantity':-1},{'quantity':1.5},{'received_date':str(self.today+timedelta(days=1))},
                       {'expiry_date':str(self.today-timedelta(days=1))},{'unit_cost':'1.001'},{'reason':''}]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                self.receive(**change)
        self.assertEqual(InventoryBatch.objects.count(), 0)

    def test_undated_stock_is_preserved_and_reserved_is_excluded(self):
        self.receive(expiry_date=None)
        stock = ProductStock.objects.get(itemcode=self.product.itemcode)
        stock.stock_reserved = 5
        stock.save()
        self.assertEqual(stock_summary(stock)['sellable'], 25)

    def test_receiving_rolls_back_if_audit_fails(self):
        with patch('apps.inventory.batches.InventoryRevision.objects.create', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                self.receive()
        self.assertEqual(InventoryBatch.objects.count(), 0)
        self.assertEqual(document(self.product, 'MAIN')['data']['quantity'], 0)

    def test_receive_api_requires_manager_and_batch_history_is_branch_scoped(self):
        client=APIClient()
        user=Staff.objects.create_user('batch@example.test', role='cashier')
        client.force_authenticate(user)
        self.assertEqual(client.post(f'/api/v1/inventory-items/{self.product.pk}/receive/',{}).status_code,403)
        user.role='admin'; user.save()
        self.receive()
        result=client.get(f'/api/v1/inventory-items/{self.product.pk}/batches/?branch=DEST')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.data['batches'],[])
        self.assertEqual(result.data['history'],[])
    def test_online_stock_deduction_excludes_expired_batches(self):
        from django.db import transaction
        from django.core.exceptions import ValidationError as DjangoValidationError
        self.receive(days=0)
        self.receive('VALID', 10, 20)
        stock = ProductStock.objects.get(itemcode=self.product.itemcode)
        with patch('apps.inventory.batches.timezone.localdate', return_value=self.today + timedelta(days=1)):
            self.assertEqual(stock.available_stock, 10)
            with self.assertRaises(DjangoValidationError), transaction.atomic():
                stock.deduct(15)
            with transaction.atomic():
                stock.deduct(5)
            self.assertEqual(InventoryBatchBalance.objects.get(batch__number='VALID').quantity, 5)
            self.assertEqual(InventoryBatchBalance.objects.get(batch__number='LOT-A').quantity, 30)
            self.assertEqual(stock.total_stock, 35)

    def test_opening_migration_is_repeat_safe_and_preserves_unknown_dates(self):
        import importlib
        from django.apps import apps
        from django.db import connection
        from types import SimpleNamespace
        stock=ProductStock.objects.get(itemcode=self.product.itemcode)
        stock.stock_sa, stock.stock_sr=12,3
        stock.save()
        migration=importlib.import_module('apps.inventory.migrations.0009_preserve_existing_batches')
        for _ in range(2):
            migration.preserve_existing_batches(apps,SimpleNamespace(connection=connection))
        self.assertEqual(sum(InventoryBatchBalance.objects.values_list('quantity',flat=True)),15)
        self.assertEqual(InventoryBatch.objects.count(),1)
        self.assertIsNone(InventoryBatch.objects.get().expiry_date)
        self.assertEqual(InventoryBatchMovement.objects.count(),2)
        stock.refresh_from_db()
        self.assertEqual(stock.total_stock,15)

    def test_product_creation_records_optional_opening_batch(self):
        result=save_definition({'reason':'New product','data':{'name':'Opening item'},'opening_stock':{
            'number':'OPEN-NEW','quantity':8,'received_date':str(self.today),'expiry_date':None,
            'unit_cost':'3.25','reason':'Opening count'}},'admin')
        self.assertEqual(result['stock']['on_hand'],8)
        self.assertEqual(InventoryBatch.objects.get(product_id=result['id']).unit_cost_centavos,325)

    def test_backdated_receipt_does_not_replace_latest_cost_or_receipt_date(self):
        self.receive(unit_cost='20.00')
        result=self.receive('BACKDATED',10,20,received_date=str(self.today-timedelta(days=3)),unit_cost='10.00')
        self.assertEqual(result['stock']['last_restocked'],str(self.today))
        self.assertEqual(result['data']['cost_price'],'20.00')

    def test_stock_api_deduction_history_uses_actual_before_balance(self):
        self.receive()
        client=APIClient()
        user=Staff.objects.create_user('deduct@example.test',role='admin')
        client.force_authenticate(user)
        result=client.post('/api/v1/stock/deduct/', {'itemcode':self.product.itemcode,'branch_code':'MAIN','qty':5}, format='json')
        self.assertEqual(result.status_code,200)
        movement=StockMovement.objects.get(movement_type='sale')
        self.assertEqual((movement.qty_before,movement.qty_after),(30,25))


    def test_bulk_receipt_persists_conversion_costs_and_selling_price(self):
        result = self.receive(quantity=36, base_uom='pc', purchase_uom='box',
            package_quantity=3, units_per_package=12, package_cost='120.00',
            pricing_factors=[{'type': 'Freight', 'amount': '1.00'}],
            markup_percent='20.00', vat_percent='12.00', selling_price='14.78')
        batch = InventoryBatch.objects.get()
        self.assertEqual((batch.package_quantity, batch.units_per_package), (3, 12))
        self.assertEqual((batch.package_cost_centavos, batch.unit_cost_centavos, batch.selling_price_centavos), (12000, 1000, 1478))
        self.assertEqual(result['stock']['on_hand'], 36)
        self.assertEqual(result['data']['selling_price'], '14.78')
        self.assertEqual(result['data']['units'], [{'unit': 'box', 'factor': '12'}])
        self.assertEqual(result['data']['landed_costs'], [{'type': 'Freight', 'amount': '1.00'}])

    def test_inconsistent_bulk_quantity_is_rejected_without_stock_change(self):
        with self.assertRaises(ValidationError):
            self.receive(quantity=35, package_quantity=3, units_per_package=12, package_cost='120.00')
        self.assertFalse(InventoryBatch.objects.exists())
        self.assertFalse(InventoryBatchMovement.objects.exists())
