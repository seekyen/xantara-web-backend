from copy import deepcopy
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from apps.inventory.models import Branch, Product, ProductStock, InventoryProfile, InventoryRevision, StockMovement
from apps.inventory.workspace import save_document, document, validate_fields, SCHEMA


class InventoryWorkspaceTests(TestCase):
    def setUp(self):
        Branch.objects.get_or_create(code='MAIN', defaults={'name': 'Main'})[0]
        Branch.objects.create(code='BR002', name='Second')

    def payload(self, **changes):
        payload = {'branch': 'MAIN', 'tier': 'basic', 'revision': 0, 'expected_quantity': 0,
                   'reason': 'Opening stock', 'data': {'name': 'Rice', 'quantity': 12,
                   'selling_price': '45.50', 'cost_price': '30.25', 'unit': 'bag'}}
        payload.update(changes)
        return payload

    def test_creation_generates_sku_and_audits_stock_atomically(self):
        result = save_document(self.payload(), 'owner')
        product = Product.objects.get(pk=result['id'])
        self.assertTrue(product.itemcode.startswith('ITM'))
        self.assertEqual(result['data']['quantity'], 12)
        self.assertEqual(InventoryRevision.objects.count(), 1)
        self.assertEqual(StockMovement.objects.get().qty, 12)

    def test_stale_revision_and_concurrent_stock_are_rejected(self):
        result = save_document(self.payload(), 'owner')
        product = Product.objects.get(pk=result['id'])
        with self.assertRaises(ValidationError):
            save_document(self.payload(), 'owner', product)
        update = {**result, 'reason': 'Count', 'expected_quantity': 12, 'data': {**result['data'], 'quantity': 15}}
        ProductStock.objects.filter(itemcode=product.itemcode).update(stock_sa=11)
        with self.assertRaises(ValidationError):
            save_document(update, 'owner', product)
        self.assertEqual(ProductStock.objects.get().stock_sa, 11)
        self.assertEqual(InventoryRevision.objects.count(), 1)

    def test_tier_downgrade_preserves_advanced_details(self):
        payload = self.payload(tier='advanced')
        payload['data'].update({'price_tiers': [{'name': 'Bulk', 'minimum_quantity': 10, 'price': '40.00'}],
                               'units': [{'unit': 'sack', 'factor': '25'}],
                               'landed_costs': [{'name': 'Freight', 'amount': '1.00'}]})
        result = save_document(payload, 'owner')
        product = Product.objects.get(pk=result['id'])
        result.update(tier='basic', expected_quantity=12, reason='Simplify form')
        updated = save_document(result, 'owner', product)
        self.assertEqual(updated['data']['price_tiers'][0]['name'], 'Bulk')
        self.assertEqual(updated['data']['units'][0]['unit'], 'sack')
        self.assertEqual(updated['landed_unit_cost'], '31.25')

    def test_branch_allocations_are_isolated(self):
        payload = self.payload(tier='advanced')
        payload['data']['location'] = 'Shelf A'
        result = save_document(payload, 'owner')
        product = Product.objects.get(pk=result['id'])
        second = document(product, 'BR002')
        self.assertEqual(second['data']['quantity'], 0)
        self.assertNotIn('location', second['data'])
        self.assertEqual(document(product, 'MAIN')['data']['location'], 'Shelf A')

    def test_invalid_records_rollback_product_stock_and_profile(self):
        for bad in [{'quantity': -1}, {'selling_price': 'NaN'}, {'selling_price': '1.001'},
                    {'price_tiers': [{'name': 'Bulk', 'minimum_quantity': 1, 'price': '1.00',
                                      'effective_from': '2026-09-02', 'effective_to': '2026-09-01'}]},
                    {'units': [{'unit': 'Box', 'factor': '2'}, {'unit': 'box', 'factor': '3'}]}]:
            with self.subTest(bad=bad):
                payload = self.payload()
                payload['data'].update(bad)
                with self.assertRaises(ValidationError):
                    save_document(payload, 'owner')
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(InventoryProfile.objects.count(), 0)

    def test_removed_fields_are_rejected_and_stale_values_are_not_returned(self):
        removed = ['suppliers', 'purchases', 'supplier_scores', 'currency', 'exchange_rate',
                   'locations', 'serials', 'traceability', 'integrations', 'variants', 'tags']
        self.assertFalse(set(removed) & {field['key'] for field in SCHEMA['fields']})
        payload = self.payload()
        payload['data']['serials'] = [{'serial': 'A001'}]
        with self.assertRaises(ValidationError):
            save_document(payload, 'owner')
        result = save_document(self.payload(), 'owner')
        product = Product.objects.get(pk=result['id'])
        # Values saved by an older schema stay in storage but never reach the editor,
        # so the next save does not trip over them and then discards them.
        profile = InventoryProfile.objects.get(product=product)
        profile.data = {**profile.data, 'purchases': [{'reference': 'PO1'}], 'currency': 'USD'}
        profile.branch_data = {'MAIN': {'serials': [{'serial': 'A001'}], 'locations': [{'bin': 'A1'}]}}
        profile.save()
        shown = document(product, 'MAIN')
        self.assertFalse(set(removed) & set(shown['data']))
        shown.update(expected_quantity=12, reason='Rename')
        shown['data']['name'] = 'Brown rice'
        updated = save_document(shown, 'owner', product)
        self.assertEqual(updated['data']['name'], 'Brown rice')
        profile.refresh_from_db()
        self.assertFalse(set(removed) & set(profile.data))
        self.assertFalse(set(removed) & set(profile.branch_data['MAIN']))

    def test_legacy_item_is_adapted_without_destroying_stock(self):
        product = Product.objects.create(itemcode='OLD', descshort='Existing', sell_price_rp=10)
        ProductStock.objects.create(itemcode='OLD', branch_code='MAIN', stock_sa=4, stock_sr=3)
        result = document(product, 'MAIN')
        self.assertEqual(result['data']['quantity'], 7)
        self.assertEqual(result['data']['name'], 'Existing')
        result['reason'] = 'Add metadata'
        result['expected_quantity'] = 7
        save_document(result, 'owner', product)
        stock = ProductStock.objects.get()
        self.assertEqual((stock.stock_sa, stock.stock_sr), (4, 3))
        self.assertFalse(StockMovement.objects.exists())


class InventoryRouteTests(TestCase):
    def test_stock_branch_route_is_not_shadowed_by_staff_branches(self):
        from django.urls import resolve
        from apps.inventory.views import BranchViewSet
        self.assertIs(resolve('/api/v1/inventory-branches/').func.cls, BranchViewSet)

    def test_legacy_product_can_load_without_an_inventory_profile(self):
        product = Product.objects.create(itemcode='LEGACY', descshort='Legacy item')
        result = document(product, 'MAIN')
        self.assertEqual(result['data']['name'], 'Legacy item')
        self.assertEqual(result['revision'], 0)
