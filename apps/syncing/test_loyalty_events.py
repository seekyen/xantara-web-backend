from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Staff
from apps.customers.models import Customer, LoyaltyEntry, LoyaltyPromo
from apps.inventory.models import Branch, Product, ProductStock

from .models import CloudSyncEvent, SyncInstallation


class PosLoyaltyEventTests(APITestCase):
    """Points for invoices that a POS device syncs (server-authoritative; the device only estimates)."""

    def setUp(self):
        self.staff = Staff.objects.create_user(email='owner@example.com', password='x', name='Owner', role='admin', is_active=True)
        self.branch = Branch.objects.get_or_create(code='MAIN', defaults={'name': 'Main Branch'})[0]
        SyncInstallation.objects.create(
            business_id='business-1', installation_id='installation-1', terminal_id='terminal-1',
            local_branch_id='branch-main', branch=self.branch, authorized_staff=self.staff, sync_enabled=True)
        Product.objects.create(itemcode='product-1', descshort='Sample')
        ProductStock.objects.create(itemcode='product-1', branch_code='MAIN', stock_sa=10, stock_book_sa=10)
        self.customer = Customer.objects.create(name='Maria Santos')
        self.client.force_authenticate(self.staff)
        self.url = reverse('sync-event-upload')
        self.today = timezone.localdate()
        self.now = timezone.now().isoformat()   # fixed, so a replay is byte-identical

    def promo(self, spend='20', **values):
        data = {'name': 'Payday Points', 'start_date': self.today, 'end_date': self.today, 'spend_per_point': Decimal(spend)}
        return LoyaltyPromo.objects.create(**{**data, **values})

    def send(self, event_type, invoice_id, payload, key):
        body = {'schemaVersion': 1, 'localEventId': key, 'businessId': 'business-1', 'branchId': 'branch-main',
                'aggregateType': 'invoice', 'aggregateId': invoice_id, 'eventType': event_type,
                'idempotencyKey': key, 'payload': payload, 'createdAt': self.now}
        return self.client.post(self.url, body, format='json', HTTP_IDEMPOTENCY_KEY=key,
                                HTTP_X_XANTARA_INSTALLATION_ID='installation-1', HTTP_X_XANTARA_TERMINAL_ID='terminal-1')

    def issue(self, invoice_id='inv-1', customer='self', total=11200, vat=1200, issued_at=None, **extra):
        payload = {'branchId': 'branch-main', 'lines': [{'productId': 'product-1', 'quantity': 1}],
                   'totalCentavos': total, 'taxSummary': {'vatAmountCentavos': vat},
                   'invoiceNumber': 'INV-0001', 'issuedAt': issued_at or self.now, **extra}
        if customer == 'self':
            payload['customerId'] = str(self.customer.pk)
        elif customer is not None:
            payload['customerId'] = customer
        return self.send('invoice.issued', invoice_id, payload, f'invoice.issued:{invoice_id}')

    def void(self, invoice_id='inv-1'):
        return self.send('invoice.voided', invoice_id, {'branchId': 'branch-main'}, f'invoice.voided:{invoice_id}')

    def refreshed(self):
        self.customer.refresh_from_db()
        return self.customer

    def test_points_use_the_net_of_vat_and_customer_totals_are_updated(self):
        self.promo('20')
        self.assertEqual(self.issue().status_code, 202)
        customer = self.refreshed()
        # P112.00 total less P12.00 VAT = P100.00 net -> 5 points at P20 per point.
        self.assertEqual((customer.loyalty_points, customer.total_spent, customer.total_orders, customer.last_visit),
                         (5, Decimal('112.00'), 1, self.today))
        entry = LoyaltyEntry.objects.get()
        self.assertEqual((entry.kind, entry.points, entry.net_amount, entry.promo_name, entry.transaction_id),
                         ('earn', 5, Decimal('100.00'), 'Payday Points', None))
        self.assertEqual(entry.sync_event.aggregate_id, 'inv-1')
        # The customer's points history shows the POS invoice number as its reference.
        rows = self.client.get(f'/api/v1/customers/{self.customer.pk}/loyalty/').data
        self.assertEqual([(r['kind'], r['points'], r['txn_no']) for r in rows], [('earn', 5, 'INV-0001')])
        self.assertEqual(ProductStock.objects.get().stock_sa, 9)

    def test_replaying_the_same_event_never_doubles_points(self):
        self.promo('20')
        self.assertEqual(self.issue().status_code, 202)
        self.assertEqual(self.issue().status_code, 200)
        customer = self.refreshed()
        self.assertEqual((customer.loyalty_points, customer.total_orders, LoyaltyEntry.objects.count()), (5, 1, 1))
        self.assertEqual(ProductStock.objects.get().stock_sa, 9)

    def test_no_promo_means_no_points_but_the_sale_still_counts(self):
        self.assertEqual(self.issue().status_code, 202)
        customer = self.refreshed()
        self.assertEqual((customer.loyalty_points, customer.total_orders, LoyaltyEntry.objects.count()), (0, 1, 0))

    def test_unknown_or_invalid_customer_never_blocks_the_inventory_sync(self):
        self.promo('20')
        for index, bad in enumerate(['999999', 'abc', '', None, '1.5']):
            self.assertEqual(self.issue(f'inv-bad-{index}', customer=bad).status_code, 202, bad)
        self.assertEqual(LoyaltyEntry.objects.count(), 0)
        self.assertEqual(ProductStock.objects.get().stock_sa, 5)

    def test_unusable_money_earns_nothing(self):
        self.promo('20')
        for index, (total, vat) in enumerate([(-5, 0), (1000, 2000), ('1000', 0), (True, 0), (None, 0)]):
            self.assertEqual(self.issue(f'inv-money-{index}', total=total, vat=vat).status_code, 202)
        self.assertEqual((LoyaltyEntry.objects.count(), self.refreshed().total_orders), (0, 0))

    def test_the_promo_is_chosen_by_the_invoice_date_in_manila_time(self):
        # 2026-09-20T17:00Z is already 21 Sep 01:00 in Manila.
        day = date(2026, 9, 21)
        self.promo('50', name='On the 21st', start_date=day, end_date=day)
        self.promo('10', name='On the 20th', start_date=day - timedelta(days=1), end_date=day - timedelta(days=1))
        self.assertEqual(self.issue(issued_at='2026-09-20T17:00:00Z', total=11200, vat=1200).status_code, 202)
        entry = LoyaltyEntry.objects.get()
        self.assertEqual((entry.promo_name, entry.points), ('On the 21st', 2))
        self.assertEqual(self.refreshed().last_visit, day)

    def test_voiding_the_invoice_takes_points_and_totals_back_once(self):
        self.promo('20')
        self.issue()
        self.assertEqual(self.void().status_code, 202)
        customer = self.refreshed()
        self.assertEqual((customer.loyalty_points, customer.total_spent, customer.total_orders), (0, Decimal('0.00'), 0))
        self.assertEqual(sorted(LoyaltyEntry.objects.values_list('kind', 'points')), [('earn', 5), ('reversal', -5)])
        self.assertEqual(self.void().status_code, 200)   # same key: replay, no second reversal
        self.assertEqual(self.refreshed().loyalty_points, 0)
        self.assertEqual(ProductStock.objects.get().stock_sa, 10)

    def test_voiding_an_invoice_without_a_customer_is_unaffected(self):
        self.assertEqual(self.issue(customer=None).status_code, 202)
        self.assertEqual(self.void().status_code, 202)
        self.assertEqual(CloudSyncEvent.objects.count(), 2)

    def test_pos_download_lists_active_customers_and_live_promos_only(self):
        Customer.objects.create(name='Inactive Ian', status='inactive')
        Customer.objects.filter(pk=self.customer.pk).update(loyalty_points=12, phone='0917')
        running = self.promo('20', name='Running')
        upcoming = self.promo('30', name='Upcoming', start_date=self.today + timedelta(days=2), end_date=self.today + timedelta(days=4))
        self.promo('40', name='Ended', start_date=self.today - timedelta(days=4), end_date=self.today - timedelta(days=1))
        self.promo('50', name='Paused', is_active=False)
        response = self.client.get('/api/v1/loyalty/pos-sync/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['name'] for c in response.data['customers']], ['Maria Santos'])
        self.assertEqual((response.data['customers'][0]['loyalty_points'], response.data['customers'][0]['phone']), (12, '0917'))
        self.assertEqual([p['name'] for p in response.data['promos']], ['Running', 'Upcoming'])
        self.assertEqual(response.data['promos'][0]['id'], running.pk)
        self.assertEqual(response.data['promos'][1]['id'], upcoming.pk)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/loyalty/pos-sync/').status_code, 401)
