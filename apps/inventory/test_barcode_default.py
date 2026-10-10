from django.test import TestCase
from apps.inventory.models import Branch, Product
from apps.inventory.workspace import save_document


class BarcodeDefaultTests(TestCase):
    def setUp(self):
        Branch.objects.get_or_create(code='MAIN', defaults={'name': 'Main'})

    def make(self, **data):
        return Product.objects.get(pk=save_document({'reason': 'New product', 'data': {'name': 'Milk', 'quantity': 0, **data}}, 'admin')['id'])

    def test_generated_sku_becomes_the_initial_barcode(self):
        product = self.make()
        self.assertTrue(product.itemcode.startswith('ITM'))
        self.assertEqual(product.itemcode2, product.itemcode)

    def test_typed_sku_becomes_the_initial_barcode(self):
        product = self.make(sku='12345678')
        self.assertEqual((product.itemcode, product.itemcode2), ('12345678', '12345678'))

    def test_explicit_barcode_is_kept(self):
        product = self.make(sku='LOCAL-1', barcode='8901764111105')
        self.assertEqual((product.itemcode, product.itemcode2), ('LOCAL-1', '8901764111105'))
