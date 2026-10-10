from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Staff
from apps.inventory import product_lookup as lookup

IMG = 'https://images.openfoodfacts.org/images/products/544/900/000/0996/front_en.1129.400.jpg'


def product(code='5449000000996', name='Coca-Cola', **extra):
    return {'code': code, 'product_name': name, 'brands': 'Coca-Cola', 'quantity': '330 ml', 'image_front_url': IMG, 'image_front_small_url': IMG, **extra}


class LookupLogicTests(SimpleTestCase):
    def test_barcode_hit_searches_every_source_and_dedupes(self):
        with patch.object(lookup, 'fetch_json', return_value={'status': 1, 'product': product()}) as fetch:
            result = lookup.lookup(barcode='5449000000996')
        self.assertEqual(fetch.call_count, len(lookup.SOURCES))
        self.assertEqual((result['matched_by'], len(result['results']), result['unavailable']), ('barcode', 1, []))
        self.assertEqual((result['results'][0]['image_url'], result['results'][0]['match']), (IMG, 'barcode'))

    def test_generic_name_is_offered_as_the_description(self):
        with patch.object(lookup, 'fetch_json', return_value={'status': 1, 'product': product(generic_name='  Instant coffee ')}) as fetch:
            result = lookup.lookup(barcode='5449000000996')
        self.assertIn('generic_name', fetch.call_args.args[0])
        self.assertEqual(result['results'][0]['description'], 'Instant coffee')
        with patch.object(lookup, 'fetch_json', return_value={'status': 1, 'product': product()}):
            self.assertEqual(lookup.lookup(barcode='5449000000996')['results'][0]['description'], '')

    def test_barcode_match_still_shows_name_matches_without_duplicates(self):
        def fake(url):
            if '/api/v2/product/' in url:
                return {'status': 1, 'product': product('12345678', 'dsdsds')} if 'openfoodfacts' in url else {'status': 0}
            return {'products': [product('12345678', 'dsdsds'), product('54491069', 'Sprite 500ml')] if 'openfoodfacts' in url else []}
        with patch.object(lookup, 'fetch_json', side_effect=fake):
            result = lookup.lookup(barcode='12345678', name='Sprite 500ML')
        self.assertEqual([(r['barcode'], r['match']) for r in result['results']], [('12345678', 'barcode'), ('54491069', 'name')])
        self.assertEqual(result['matched_by'], 'barcode')

    def test_unknown_barcode_falls_back_to_name_and_reports_failed_sources(self):
        def fake(url):
            if '/api/v2/product/' in url:
                return {'status': 0}
            if 'openbeautyfacts' in url:
                return None
            return {'products': [product('111111', 'Sprite 500ml')] if 'openfoodfacts' in url else []}
        with patch.object(lookup, 'fetch_json', side_effect=fake):
            result = lookup.lookup(barcode='12345678', name='Sprite 500ML')
        self.assertEqual((result['matched_by'], result['results'][0]['name']), ('name', 'Sprite 500ml'))
        self.assertEqual(result['unavailable'], ['Open Beauty Facts'])

    def test_bad_records_and_foreign_image_hosts_are_dropped(self):
        rows = [product('abc', 'Bad code'), product('222222', ''), product('333333', 'Evil', image_front_url='http://169.254.169.254/x.jpg', image_front_small_url='')]
        with patch.object(lookup, 'fetch_json', return_value={'products': rows}):
            result = lookup.lookup(name='thing')
        self.assertEqual([r['barcode'] for r in result['results']], ['333333'])
        self.assertEqual(result['results'][0]['image_url'], '')

    def test_image_urls_are_restricted_to_source_hosts(self):
        for bad in ['http://images.openfoodfacts.org/a.jpg', 'https://evil.example/a.jpg', 'https://images.openfoodfacts.org.evil.example/a.jpg',
                    'https://user@images.openfoodfacts.org/a.jpg', 'file:///etc/passwd', '']:
            with self.assertRaises(ValueError):
                lookup.fetch_image(bad)
        self.assertTrue(lookup.allowed_image_url(IMG))


class LookupApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(Staff.objects.create_user('look@example.test', role='manager', name='M'))

    def test_validation_and_results(self):
        self.assertEqual(self.client.get('/api/v1/inventory-items/lookup/').status_code, 400)
        self.assertEqual(self.client.get('/api/v1/inventory-items/lookup/', {'name': 'a'}).status_code, 400)
        with patch.object(lookup, 'fetch_json', return_value={'products': [product()]}):
            response = self.client.get('/api/v1/inventory-items/lookup/', {'name': 'Coca-Cola'})
        self.assertEqual((response.status_code, response.data['matched_by']), (200, 'name'))

    def test_all_sources_down_is_503(self):
        with patch.object(lookup, 'fetch_json', return_value=None):
            self.assertEqual(self.client.get('/api/v1/inventory-items/lookup/', {'name': 'Sprite'}).status_code, 503)

    def test_image_proxy_and_permissions(self):
        with patch.object(lookup, 'fetch_image', return_value=(b'\xff\xd8data', 'image/jpeg')):
            ok = self.client.get('/api/v1/inventory-items/lookup-image/', {'url': IMG})
        self.assertEqual((ok.status_code, ok['Content-Type']), (200, 'image/jpeg'))
        self.assertEqual(self.client.get('/api/v1/inventory-items/lookup-image/', {'url': 'https://evil.example/a.jpg'}).status_code, 400)
        self.client.force_authenticate(Staff.objects.create_user('cash2@example.test', role='cashier', name='C'))
        self.assertEqual(self.client.get('/api/v1/inventory-items/lookup/', {'name': 'Sprite'}).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/inventory-items/lookup-image/', {'url': IMG}).status_code, 403)
