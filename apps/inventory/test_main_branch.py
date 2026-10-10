from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from apps.accounts.models import Staff
from apps.branches.models import Branch as ManagedBranch
from apps.inventory.models import Branch, Product, ProductStock, StockMovement, InventoryProfile
from apps.inventory.workspace import save_document, document, distribute_stock

class MainBranchInventoryTests(TestCase):
    def setUp(self):
        Branch.objects.get_or_create(code='MAIN', defaults={'name': 'Central'})
        self.destination = Branch.objects.create(code='DEST', name='Destination')
        self.other = Branch.objects.create(code='OTHER', name='Other')
        self.master = save_document({'branch': 'MAIN', 'reason': 'Opening stock', 'expected_quantity': 0,
            'data': {'name': 'Rice', 'quantity': 20, 'selling_price': '45.00', 'unit': 'bag'}}, 'admin')
        self.product = Product.objects.get(pk=self.master['id'])
        self.client = APIClient()
        self.admin = Staff.objects.create_user('inventory@example.test', role='admin')
        self.client.force_authenticate(self.admin)

    def distribute(self, **overrides):
        return distribute_stock(self.product.pk, {'branch': 'DEST', 'quantity': 7,
            'expected_quantity': 20, 'reason': 'Replenishment', **overrides}, self.admin.pk)

    def test_distribution_conserves_stock_and_records_real_before_after_balances(self):
        result = self.distribute()
        self.assertEqual(result['main']['data']['quantity'], 13)
        self.assertEqual(result['branch']['data']['quantity'], 7)
        out = StockMovement.objects.get(movement_type='transfer_out')
        incoming = StockMovement.objects.get(movement_type='transfer_in')
        self.assertEqual((out.qty_before, out.qty_after), (20, 13))
        self.assertEqual((incoming.qty_before, incoming.qty_after), (0, 7))
        self.assertEqual(out.ref_no, incoming.ref_no)
        self.assertEqual(Product.objects.count(), 1)

    def test_branch_list_only_contains_allocated_products_and_inherits_changes(self):
        self.assertEqual(self.client.get('/api/v1/inventory-items/?branch=DEST').json(), [])
        self.distribute()
        changed = document(self.product, 'MAIN')
        changed.update(reason='Rename master', expected_quantity=13)
        changed['data'].update(name='Premium Rice', selling_price='50.00')
        save_document(changed, self.admin.pk, self.product)
        response = self.client.get('/api/v1/inventory-items/?branch=DEST')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['data']['name'], 'Premium Rice')
        self.assertEqual(response.json()[0]['data']['selling_price'], '50.00')
        self.assertEqual(response.json()[0]['data']['quantity'], 7)
        self.assertEqual(self.client.get('/api/v1/inventory-items/?branch=OTHER').json(), [])
        stock = ProductStock.objects.get(branch_code='DEST')
        stock.stock_sa = 0
        stock.save()
        self.assertEqual(len(self.client.get('/api/v1/inventory-items/?branch=DEST').json()), 1)

    def test_branch_cannot_overwrite_master_or_create_product(self):
        payload = {**self.master, 'branch': 'DEST', 'reason': 'Unauthorized branch edit'}
        response = self.client.put(f'/api/v1/inventory-items/{self.product.pk}/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post('/api/v1/inventory-items/', payload, format='json').status_code, 400)
        self.assertEqual(Product.objects.count(), 1)

    def test_invalid_distribution_leaves_no_destination_stock_or_movements(self):
        for overrides in [{'quantity': 21}, {'quantity': 0}, {'quantity': -1}, {'quantity': 1.5},
                          {'quantity': 'NaN'}, {'branch': 'MAIN'}, {'branch': 'MISSING'},
                          {'expected_quantity': 19}, {'reason': ''}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self.distribute(**overrides)
        self.assertFalse(ProductStock.objects.filter(branch_code='DEST').exists())
        self.assertFalse(StockMovement.objects.filter(movement_type='transfer_out').exists())
        self.assertEqual(document(self.product, 'MAIN')['data']['quantity'], 20)
    def test_reserved_and_inactive_stock_are_not_distributed(self):
        source = ProductStock.objects.get(branch_code='MAIN')
        source.stock_reserved = 15
        source.save()
        with self.assertRaises(ValidationError):
            self.distribute()
        self.destination.active = False
        self.destination.save()
        with self.assertRaises(ValidationError):
            self.distribute(quantity=1)

    def test_replay_is_rejected_by_expected_balance(self):
        self.distribute()
        with self.assertRaises(ValidationError):
            self.distribute()
        self.assertEqual(document(self.product, 'DEST')['data']['quantity'], 7)

    def test_rollback_if_audit_write_fails(self):
        from unittest.mock import patch
        with patch('apps.inventory.workspace.InventoryRevision.objects.create', side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                self.distribute()
        self.assertEqual(document(self.product, 'MAIN')['data']['quantity'], 20)
        self.assertFalse(ProductStock.objects.filter(branch_code='DEST').exists())
        self.assertFalse(StockMovement.objects.filter(movement_type='transfer_in').exists())

    def test_permissions_are_enforced_for_distribution(self):
        cashier = Staff.objects.create_user('cashier@example.test', role='cashier')
        self.client.force_authenticate(cashier)
        response = self.client.post(f'/api/v1/inventory-items/{self.product.pk}/distribute/',
            {'branch': 'DEST', 'quantity': 1, 'expected_quantity': 20, 'reason': 'Test'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_managed_branch_gets_stable_stock_location(self):
        branch = ManagedBranch.objects.create(name='BGC')
        code = branch.inventory_branch.code
        self.assertNotEqual(code, 'MAIN')
        branch.name = 'BGC Updated'
        branch.save()
        branch.inventory_branch.refresh_from_db()
        self.assertEqual(branch.inventory_branch.name, 'BGC Updated')
        self.assertEqual(branch.inventory_branch.code, code)
        branch.is_active = False
        branch.save()
        branch.inventory_branch.refresh_from_db()
        self.assertFalse(branch.inventory_branch.active)

    def test_distribution_uses_both_warehouse_storage_balances(self):
        source = ProductStock.objects.get(branch_code='MAIN')
        source.stock_sa, source.stock_sr = 3, 17
        source.save()
        self.distribute()
        source.refresh_from_db()
        self.assertEqual((source.stock_sa, source.stock_sr), (0, 13))
        self.product.refresh_from_db()
        self.assertEqual((self.product.stock_sa, self.product.stock_sr), (7, 13))
        self.assertEqual(StockMovement.objects.filter(movement_type='transfer_out').count(), 2)
    def test_opening_migration_preserves_legacy_stock_without_copying_allocated_totals(self):
        import importlib
        from django.apps import apps
        from django.db import connection
        from types import SimpleNamespace
        legacy = Product.objects.create(itemcode='LEGACY-OPEN', descshort='Old stock', stock_sa=12, stock_sr=3)
        migration = importlib.import_module('apps.inventory.migrations.0007_central_opening_stock')
        for _ in range(2):
            migration.carry_unallocated_stock(apps, SimpleNamespace(connection=connection))
        stock = ProductStock.objects.get(itemcode=legacy.itemcode, branch_code='MAIN')
        self.assertEqual((stock.stock_sa, stock.stock_sr), (12, 3))
        self.assertEqual(StockMovement.objects.filter(itemcode=legacy.itemcode).count(), 2)
        self.assertEqual(ProductStock.objects.filter(itemcode=self.product.itemcode).count(), 1)
        self.assertEqual(document(self.product, 'MAIN')['data']['quantity'], 20)
