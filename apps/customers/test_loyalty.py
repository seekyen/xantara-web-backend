from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Staff
from apps.customers.loyalty import award_points, best_promo, points_for, reverse_points
from apps.customers.models import Customer, LoyaltyEntry, LoyaltyPromo
from apps.inventory.models import Product
from apps.sales.models import Transaction


class PointsMathTests(SimpleTestCase):
    def test_whole_steps_only(self):
        self.assertEqual(points_for(Decimal('250.00'), Decimal('100')), 2)
        self.assertEqual(points_for(Decimal('99.99'), Decimal('100')), 0)
        self.assertEqual(points_for(Decimal('250.00'), Decimal('50')), 5)
        self.assertEqual(points_for(Decimal('250.00'), Decimal('0')), 0)
        self.assertEqual(points_for(Decimal('-10.00'), Decimal('100')), 0)


class LoyaltyTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.customer = Customer.objects.create(name='Maria Santos')
        self.product = Product.objects.create(itemcode='P1', descshort='Item', sell_price_rp=95, stock_sa=20)
        self.manager = Staff.objects.create_user('mgr@example.test', role='manager', name='Manager')
        self.cashier = Staff.objects.create_user('csh@example.test', role='cashier', name='Cashier')
        self.client = APIClient()

    def promo(self, **values):
        data = {'name': 'Double Days', 'start_date': self.today, 'end_date': self.today, 'spend_per_point': Decimal('20')}
        return LoyaltyPromo.objects.create(**{**data, **values})

    def sell(self, qty=2):
        """2 x P95 = P190 net, P22.80 VAT, P212.80 total."""
        self.client.force_authenticate(self.cashier)
        response = self.client.post('/api/v1/transactions/', {
            'customer': self.customer.pk, 'pay_method': 'cash',
            'items': [{'product_id': self.product.pk, 'qty': qty}]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return Transaction.objects.get(pk=response.data['id'])

    def balance(self):
        self.customer.refresh_from_db()
        return self.customer.loyalty_points

    def test_points_use_the_amount_less_vat_at_the_promos_rate(self):
        self.promo(spend_per_point=Decimal('20'))
        txn = self.sell()
        self.assertEqual((txn.total - txn.tax, txn.total), (Decimal('190.00'), Decimal('212.80')))
        # 190 / 20 = 9 whole steps (the VAT-inclusive 212.80 would have given 10).
        self.assertEqual(self.balance(), 9)
        entry = LoyaltyEntry.objects.get()
        self.assertEqual((entry.kind, entry.points, entry.net_amount, entry.spend_per_point, entry.promo_name),
                         ('earn', 9, Decimal('190.00'), Decimal('20.00'), 'Double Days'))

    def test_each_promo_has_its_own_rate(self):
        self.promo(name='Low', spend_per_point=Decimal('50'), start_date=self.today - timedelta(days=9), end_date=self.today - timedelta(days=5))
        self.promo(name='Now', spend_per_point=Decimal('40'))
        self.sell()
        self.assertEqual(self.balance(), 4)   # 190 // 40, not 190 // 50

    def test_nothing_is_earned_outside_a_promo_or_without_a_customer(self):
        self.sell()
        self.assertEqual((self.balance(), LoyaltyEntry.objects.count()), (0, 0))
        past = self.promo(start_date=self.today - timedelta(days=5), end_date=self.today - timedelta(days=1))
        future = self.promo(start_date=self.today + timedelta(days=1), end_date=self.today + timedelta(days=3))
        paused = self.promo(is_active=False)
        self.sell()
        self.assertEqual((self.balance(), LoyaltyEntry.objects.count()), (0, 0))
        paused.delete(); past.delete(); future.delete()
        self.promo()
        self.client.force_authenticate(self.cashier)
        self.client.post('/api/v1/transactions/', {'pay_method': 'cash', 'items': [{'product_id': self.product.pk, 'qty': 1}]}, format='json')
        self.assertEqual(LoyaltyEntry.objects.count(), 0)

    def test_promo_dates_are_inclusive_and_overlaps_use_the_best_for_the_customer(self):
        net = Decimal('190.00')
        self.assertEqual(best_promo(self.today, net), (None, 0))
        one_day = self.promo(name='One day', spend_per_point=Decimal('100'))
        self.assertEqual(best_promo(self.today, net), (one_day, 1))
        self.assertEqual(best_promo(self.today + timedelta(days=1), net), (None, 0))
        self.assertEqual(best_promo(self.today - timedelta(days=1), net), (None, 0))
        rich = self.promo(name='Rich', spend_per_point=Decimal('10'))
        self.promo(name='Paused', spend_per_point=Decimal('1'), is_active=False)
        self.assertEqual(best_promo(self.today, net), (rich, 19))
        self.assertEqual(best_promo(self.today, Decimal('5.00')), (None, 0))

    def test_awarding_twice_never_doubles_points(self):
        self.promo()
        txn = self.sell()
        self.assertIsNone(award_points(txn))
        self.assertEqual((self.balance(), LoyaltyEntry.objects.count()), (9, 1))

    def test_refund_takes_the_points_back_once(self):
        self.promo()
        txn = self.sell()
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f'/api/v1/transactions/{txn.pk}/refund/').status_code, 200)
        self.assertEqual(self.balance(), 0)
        self.assertEqual(sorted(LoyaltyEntry.objects.values_list('kind', 'points')), [('earn', 9), ('reversal', -9)])
        self.assertIsNone(reverse_points(txn))
        self.assertEqual(self.balance(), 0)

    def test_promo_api_validates_and_reports_status(self):
        self.client.force_authenticate(self.manager)
        body = {'name': 'Payday', 'start_date': str(self.today), 'end_date': str(self.today + timedelta(days=2)), 'spend_per_point': '50'}
        created = self.client.post('/api/v1/loyalty/promos/', body, format='json')
        self.assertEqual((created.status_code, created.data['status'], created.data['spend_per_point']), (201, 'running', '50.00'))
        for bad in [{'end_date': str(self.today - timedelta(days=1))}, {'spend_per_point': '0'}, {'spend_per_point': '-5'},
                    {'spend_per_point': '0.001'}, {'spend_per_point': 'abc'}, {'name': '  '}]:
            self.assertEqual(self.client.post('/api/v1/loyalty/promos/', {**body, **bad}, format='json').status_code, 400, bad)
        future = {**body, 'name': 'Later', 'start_date': str(self.today + timedelta(days=3)), 'end_date': str(self.today + timedelta(days=4))}
        self.assertEqual(self.client.post('/api/v1/loyalty/promos/', future, format='json').data['status'], 'upcoming')
        paused = self.client.patch(f"/api/v1/loyalty/promos/{created.data['id']}/", {'is_active': False}, format='json')
        self.assertEqual(paused.data['status'], 'paused')

    def test_only_managers_can_change_promos(self):
        promo = self.promo()
        body = {'name': 'Nope', 'start_date': str(self.today), 'end_date': str(self.today), 'spend_per_point': '10'}
        self.client.force_authenticate(self.cashier)
        self.assertEqual(self.client.get('/api/v1/loyalty/promos/').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/loyalty/promos/', body, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/loyalty/promos/{promo.pk}/').status_code, 403)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.delete(f'/api/v1/loyalty/promos/{promo.pk}/').status_code, 204)

    def test_deleting_a_promo_keeps_earned_points_and_history(self):
        promo = self.promo()
        self.sell()
        self.client.force_authenticate(self.manager)
        self.client.delete(f'/api/v1/loyalty/promos/{promo.pk}/')
        self.assertEqual(self.balance(), 9)
        self.assertEqual(LoyaltyEntry.objects.get().promo_name, 'Double Days')

    def test_customer_ledger_endpoint(self):
        self.promo()
        self.sell()
        self.client.force_authenticate(self.manager)
        rows = self.client.get(f'/api/v1/customers/{self.customer.pk}/loyalty/').data
        self.assertEqual([(r['kind'], r['points'], r['promo_name']) for r in rows], [('earn', 9, 'Double Days')])
        self.assertTrue(rows[0]['txn_no'])
