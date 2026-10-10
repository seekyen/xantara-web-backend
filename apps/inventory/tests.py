from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Branch, Product, ProductStock


class PublicBranchCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch, _ = Branch.objects.update_or_create(code='MAIN', defaults={'name': 'Main Branch', 'address': '123 Sample Street'})

    def create_product(self, itemcode, **overrides):
        values = {
            'descshort': f'Product {itemcode}',
            'desclong': f'Description {itemcode}',
            'categorycode': 'MEALS',
            'sell_uom': 'PC',
            'sell_price_rp': 125.5,
            'trackinventory': True,
        }
        values.update(overrides)
        return Product.objects.create(itemcode=itemcode, **values)

    def create_stock(self, product, **overrides):
        values = {
            'branch_code': self.branch.code,
            'stock_sa': 10,
            'stock_sr': 0,
            'stock_reserved': 0,
            'stock_rop': 2,
        }
        values.update(overrides)
        return ProductStock.objects.create(itemcode=product.itemcode, **values)

    def catalog_url(self, code='MAIN'):
        return reverse('public-branch-catalog', kwargs={'branch_code': code})

    def test_catalog_is_public_and_hides_exact_inventory(self):
        product = self.create_product('MEAL-001')
        self.create_stock(product)

        response = self.client.get(self.catalog_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['branch']['code'], 'MAIN')
        self.assertEqual(response.data['count'], 1)
        item = response.data['results'][0]
        self.assertEqual(item['sku'], 'MEAL-001')
        self.assertEqual(item['price'], '125.50')
        self.assertEqual(item['availability'], 'available')
        self.assertNotIn('stock_sa', item)
        self.assertNotIn('stock_sr', item)
        self.assertNotIn('available_stock', item)
        self.assertNotIn('unitcost', item)
        self.assertNotIn('suppliercode', item)

    def test_catalog_returns_only_active_products_assigned_to_branch(self):
        visible = self.create_product('VISIBLE')
        self.create_stock(visible)

        inactive = self.create_product('INACTIVE', active=False)
        self.create_stock(inactive)

        unassigned = self.create_product('OTHER')
        ProductStock.objects.create(
            itemcode=unassigned.itemcode,
            branch_code='OTHER',
            stock_sa=5,
        )

        response = self.client.get(self.catalog_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['sku'] for item in response.data['results']], ['VISIBLE'])

    def test_catalog_exposes_safe_availability_labels(self):
        available = self.create_product('AVAILABLE')
        self.create_stock(available, stock_sa=10, stock_rop=2)

        low = self.create_product('LOW')
        self.create_stock(low, stock_sa=2, stock_rop=2)

        unavailable = self.create_product('NONE')
        self.create_stock(unavailable, stock_sa=1, stock_reserved=1)

        response = self.client.get(self.catalog_url())

        statuses = {
            item['sku']: item['availability']
            for item in response.data['results']
        }
        self.assertEqual(statuses['AVAILABLE'], 'available')
        self.assertEqual(statuses['LOW'], 'low_stock')
        self.assertEqual(statuses['NONE'], 'unavailable')

    def test_catalog_supports_search_and_category_filters(self):
        meal = self.create_product(
            'BURGER',
            descshort='Classic Burger',
            categorycode='MEALS',
        )
        drink = self.create_product(
            'COLA',
            descshort='Cold Cola',
            categorycode='DRINKS',
        )
        self.create_stock(meal)
        self.create_stock(drink)

        response = self.client.get(
            self.catalog_url(),
            {'search': 'burger', 'category': 'meals'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['sku'], 'BURGER')

    def test_inactive_or_unknown_branch_is_not_public(self):
        self.branch.active = False
        self.branch.save(update_fields=['active'])

        self.assertEqual(self.client.get(self.catalog_url()).status_code, 404)
        self.assertEqual(self.client.get(self.catalog_url('UNKNOWN')).status_code, 404)
