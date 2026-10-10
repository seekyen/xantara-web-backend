from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Staff
from apps.inventory.batches import receive_stock, write_off
from apps.inventory.models import Branch, InventoryBatchBalance, InventoryRevision, Product
from apps.inventory.workspace import save_document


class ArchiveProductTests(TestCase):
    def setUp(self):
        Branch.objects.get_or_create(code='MAIN', defaults={'name': 'Main'})
        self.product = Product.objects.get(pk=save_document({'reason': 'New product', 'data': {'name': 'Milk', 'quantity': 0}}, 'admin')['id'])
        self.client = APIClient()
        self.client.force_authenticate(Staff.objects.create_user('arch@example.test', role='manager', name='M'))
        self.url = f'/api/v1/inventory-items/{self.product.pk}/archive/'

    def stock_in(self, quantity=3):
        receive_stock(self.product.pk, {'number': 'L1', 'quantity': quantity, 'received_date': str(timezone.localdate()), 'unit_cost': '5.00', 'reason': 'Delivery'}, 'admin')

    def test_blocked_while_stock_remains_then_allowed_after_write_off(self):
        self.stock_in()
        blocked = self.client.post(self.url, {'reason': 'Discontinued'}, format='json')
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('Stock is still on hand', str(blocked.data['stock']))
        self.product.refresh_from_db()
        self.assertTrue(self.product.active)
        balance = InventoryBatchBalance.objects.get()
        write_off(self.product.pk, {'branch': 'MAIN', 'balance_id': balance.pk, 'quantity': 3, 'expected_quantity': 3, 'reason': 'Disposed'}, 'admin')
        done = self.client.post(self.url, {'reason': 'Discontinued'}, format='json')
        self.assertEqual((done.status_code, done.data['archived']), (200, True))
        self.product.refresh_from_db()
        self.assertFalse(self.product.active)
        self.assertTrue(InventoryRevision.objects.filter(product=self.product, reason='Archived: Discontinued').exists())
        listed = self.client.get('/api/v1/inventory-items/', {'branch': 'MAIN'})
        self.assertNotIn(self.product.pk, [row['id'] for row in (listed.data['results'] if isinstance(listed.data, dict) else listed.data)])
        self.assertEqual(self.client.post(self.url, {'reason': 'again'}, format='json').status_code, 404)

    def test_reason_required_and_history_is_kept(self):
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'reason': '  '}, format='json').status_code, 400)
        self.stock_in(0 + 2)
        self.client.post(self.url, {'reason': 'x'}, format='json')
        self.assertEqual(InventoryBatchBalance.objects.count(), 1)

    def test_products_api_delete_uses_the_same_guard(self):
        self.stock_in()
        self.assertEqual(self.client.delete(f'/api/v1/products/{self.product.pk}/').status_code, 400)
        self.product.refresh_from_db()
        self.assertTrue(self.product.active)

    def test_cashier_cannot_archive(self):
        self.client.force_authenticate(Staff.objects.create_user('c3@example.test', role='cashier', name='C'))
        self.assertEqual(self.client.post(self.url, {'reason': 'x'}, format='json').status_code, 403)
