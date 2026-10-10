from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Staff
from apps.branches.models import Branch as ManagedBranch
from apps.inventory.models import Branch as InventoryBranch
from apps.syncing.models import SyncInstallation

from .models import StoreSettings


class InitialSetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/setup/status/'
        self.initial_inventory_branch_count = InventoryBranch.objects.count()
        self.payload = {
            'company_name': 'North Star Retail Inc.',
            'company_address': '100 Market Street',
            'company_email': 'hello@northstar.example',
            'company_phone': '09171234567',
            'branch_name': 'North Star Main',
            'branch_address': '100 Market Street',
            'branch_email': 'main@northstar.example',
            'branch_phone': '09171234567',
            'admin_name': 'Initial Administrator',
            'admin_email': 'admin@northstar.example',
            'admin_password': 'Secure-Setup-4821!',
            'confirm_password': 'Secure-Setup-4821!',
        }

    def test_setup_creates_company_branch_admin_and_sync_mapping_atomically(self):
        before = self.client.get(self.url)
        self.assertEqual(before.status_code, 200)
        self.assertTrue(before.data['setup_required'])

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 201)
        settings = StoreSettings.objects.get(pk=1)
        branch = ManagedBranch.objects.get(name='North Star Main')
        admin = Staff.objects.get(email='admin@northstar.example')
        installation = SyncInstallation.objects.get(
            installation_id='xantara-web-main',
        )
        self.assertTrue(settings.setup_completed)
        self.assertEqual(settings.store_name, 'North Star Retail Inc.')
        self.assertTrue(settings.business_id.startswith('north-star-retail-inc-'))
        self.assertEqual(branch.inventory_branch.code, 'MAIN')
        self.assertEqual(admin.branch, branch)
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.check_password('Secure-Setup-4821!'))
        self.assertEqual(installation.business_id, settings.business_id)
        self.assertEqual(installation.authorized_staff, admin)
        self.assertTrue(installation.sync_enabled)

    def test_setup_cannot_run_twice(self):
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 201)
        retry = {**self.payload, 'company_name': 'Replacement Company'}

        response = self.client.post(self.url, retry, format='json')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(StoreSettings.objects.get(pk=1).store_name, 'North Star Retail Inc.')
        self.assertEqual(Staff.objects.count(), 1)
        self.assertEqual(ManagedBranch.objects.count(), 1)

    def test_setup_rejects_mismatched_passwords_without_partial_records(self):
        payload = {**self.payload, 'confirm_password': 'Different-Password-4821!'}

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('confirm_password', response.data)
        self.assertFalse(Staff.objects.exists())
        self.assertFalse(ManagedBranch.objects.exists())
        self.assertEqual(
            InventoryBranch.objects.count(),
            self.initial_inventory_branch_count,
        )
        self.assertFalse(StoreSettings.objects.get(pk=1).setup_completed)
