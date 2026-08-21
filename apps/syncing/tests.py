from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Staff
from apps.inventory.models import Branch, Product, ProductStock

from .models import CloudSyncEvent, SyncInstallation


class SyncEventUploadTests(APITestCase):
    def setUp(self):
        self.staff = Staff.objects.create_user(
            email='owner@example.com',
            password='not-used-in-tests',
            name='Owner',
            role='admin',
            is_active=True,
        )
        self.other_staff = Staff.objects.create_user(
            email='other@example.com',
            password='not-used-in-tests',
            name='Other Owner',
            role='admin',
            is_active=True,
        )
        self.branch = Branch.objects.create(code='MAIN', name='Main Branch')
        self.installation = SyncInstallation.objects.create(
            business_id='business-1',
            installation_id='installation-1',
            terminal_id='terminal-1',
            local_branch_id='branch-main',
            branch=self.branch,
            authorized_staff=self.staff,
            sync_enabled=True,
        )
        Product.objects.create(itemcode='product-1', descshort='Sample')
        ProductStock.objects.create(
            itemcode='product-1',
            branch_code=self.branch.code,
            stock_sa=10,
            stock_book_sa=10,
        )
        self.client.force_authenticate(self.staff)
        self.url = reverse('sync-event-upload')

    def payload(self, **overrides):
        values = {
            'schemaVersion': 1,
            'localEventId': 'event-1',
            'businessId': 'business-1',
            'branchId': 'branch-main',
            'aggregateType': 'inventory',
            'aggregateId': 'product-1',
            'eventType': 'inventory.adjusted',
            'idempotencyKey': 'inventory.adjusted:event-1',
            'payload': {'productId': 'product-1', 'quantityDelta': -2},
            'createdAt': '2026-08-21T10:30:00Z',
        }
        values.update(overrides)
        return values

    def post_event(self, payload=None, **headers):
        request_headers = {
            'HTTP_IDEMPOTENCY_KEY': 'inventory.adjusted:event-1',
            'HTTP_X_XANTARA_INSTALLATION_ID': 'installation-1',
            'HTTP_X_XANTARA_TERMINAL_ID': 'terminal-1',
        }
        request_headers.update(headers)
        return self.client.post(
            self.url,
            payload or self.payload(),
            format='json',
            **request_headers,
        )

    def test_accepts_registered_installation_event_append_only(self):
        response = self.post_event()

        self.assertEqual(response.status_code, 202)
        event = CloudSyncEvent.objects.get()
        self.assertEqual(response.data['serverEventId'], str(event.pk))
        self.assertEqual(event.installation, self.installation)
        self.assertEqual(event.branch, self.branch)
        self.assertEqual(event.payload['quantityDelta'], -2)
        self.assertEqual(
            event.device_created_at,
            timezone.datetime(2026, 8, 21, 10, 30, tzinfo=timezone.UTC),
        )

    def test_duplicate_returns_original_acknowledgement_once(self):
        first = self.post_event()
        second = self.post_event()

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data, first.data)
        self.assertEqual(CloudSyncEvent.objects.count(), 1)

    def test_reused_idempotency_key_with_different_payload_conflicts(self):
        self.post_event()
        conflict = self.post_event(
            self.payload(payload={'productId': 'product-1', 'quantityDelta': -3}),
        )

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(CloudSyncEvent.objects.count(), 1)

    def test_rejects_staff_not_assigned_to_installation(self):
        self.client.force_authenticate(self.other_staff)

        response = self.post_event()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CloudSyncEvent.objects.count(), 0)

    def test_rejects_disabled_sync_and_identity_mismatches(self):
        cases = (
            {'HTTP_X_XANTARA_INSTALLATION_ID': 'wrong-installation'},
            {'HTTP_X_XANTARA_TERMINAL_ID': 'wrong-terminal'},
        )
        for headers in cases:
            with self.subTest(headers=headers):
                response = self.post_event(**headers)
                self.assertEqual(response.status_code, 403)

        self.installation.sync_enabled = False
        self.installation.save(update_fields=['sync_enabled'])
        response = self.post_event()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CloudSyncEvent.objects.count(), 0)

    def test_requires_matching_idempotency_header(self):
        response = self.post_event(HTTP_IDEMPOTENCY_KEY='different-event')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudSyncEvent.objects.count(), 0)

    def test_invoice_issue_projects_stock_once(self):
        payload = self.payload(
            aggregateType='invoice',
            aggregateId='invoice-1',
            eventType='invoice.issued',
            idempotencyKey='invoice.issued:invoice-1',
            payload={
                'branchId': 'branch-main',
                'lines': [{'productId': 'product-1', 'quantity': 2}],
            },
        )
        first = self.post_event(
            payload,
            HTTP_IDEMPOTENCY_KEY='invoice.issued:invoice-1',
        )
        second = self.post_event(
            payload,
            HTTP_IDEMPOTENCY_KEY='invoice.issued:invoice-1',
        )

        self.assertEqual(first.status_code, 202)
        self.assertTrue(first.data['inventoryProjected'])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ProductStock.objects.get().stock_sa, 8)

    def test_failed_projection_rolls_back_event(self):
        response = self.post_event(
            self.payload(
                aggregateType='invoice',
                aggregateId='invoice-2',
                eventType='invoice.issued',
                idempotencyKey='invoice.issued:invoice-2',
                payload={
                    'branchId': 'branch-main',
                    'lines': [{'productId': 'product-1', 'quantity': 11}],
                },
            ),
            HTTP_IDEMPOTENCY_KEY='invoice.issued:invoice-2',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CloudSyncEvent.objects.count(), 0)
        self.assertEqual(ProductStock.objects.get().stock_sa, 10)

    def test_void_restores_original_invoice_stock_once(self):
        issued = self.payload(
            aggregateType='invoice',
            aggregateId='invoice-3',
            eventType='invoice.issued',
            idempotencyKey='invoice.issued:invoice-3',
            payload={
                'branchId': 'branch-main',
                'lines': [{'productId': 'product-1', 'quantity': 3}],
            },
        )
        self.post_event(issued, HTTP_IDEMPOTENCY_KEY='invoice.issued:invoice-3')
        voided = self.payload(
            localEventId='event-void-3',
            aggregateType='invoice',
            aggregateId='invoice-3',
            eventType='invoice.voided',
            idempotencyKey='invoice.voided:invoice-3',
            payload={'branchId': 'branch-main'},
        )
        response = self.post_event(
            voided,
            HTTP_IDEMPOTENCY_KEY='invoice.voided:invoice-3',
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(ProductStock.objects.get().stock_sa, 10)

    def test_transfer_projects_each_mapped_branch(self):
        destination = Branch.objects.create(code='BGC', name='BGC')
        SyncInstallation.objects.create(
            business_id='business-1',
            installation_id='installation-2',
            terminal_id='terminal-2',
            local_branch_id='branch-bgc',
            branch=destination,
            authorized_staff=self.staff,
            sync_enabled=True,
        )
        ProductStock.objects.create(
            itemcode='product-1', branch_code='BGC', stock_sa=4, stock_book_sa=4,
        )
        dispatched = self.payload(
            aggregateType='inventory_transfer',
            aggregateId='transfer-1',
            eventType='inventory.transfer_dispatched',
            idempotencyKey='inventory.transfer_dispatched:transfer-1',
            payload={
                'productId': 'product-1',
                'sourceBranchId': 'branch-main',
                'destinationBranchId': 'branch-bgc',
                'quantity': 2,
            },
        )
        self.post_event(
            dispatched,
            HTTP_IDEMPOTENCY_KEY='inventory.transfer_dispatched:transfer-1',
        )
        received = self.payload(
            localEventId='event-received-1',
            branchId='branch-bgc',
            aggregateType='inventory_transfer',
            aggregateId='transfer-1',
            eventType='inventory.transfer_received',
            idempotencyKey='inventory.transfer_received:transfer-1',
            payload={
                'productId': 'product-1',
                'sourceBranchId': 'branch-main',
                'destinationBranchId': 'branch-bgc',
                'quantity': 2,
            },
        )
        response = self.post_event(
            received,
            HTTP_IDEMPOTENCY_KEY='inventory.transfer_received:transfer-1',
            HTTP_X_XANTARA_INSTALLATION_ID='installation-2',
            HTTP_X_XANTARA_TERMINAL_ID='terminal-2',
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(ProductStock.objects.get(branch_code='MAIN').stock_sa, 8)
        self.assertEqual(ProductStock.objects.get(branch_code='BGC').stock_sa, 6)
