import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Staff
from apps.inventory.models import Branch
from apps.syncing.models import SyncInstallation
from .models import StoreSettings
from .fiscal_models import FiscalCompany, FiscalBranch, FiscalTerminal, FiscalAudit


class FiscalRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Staff.objects.create_user(email='admin@test.example', password='Valid password 123!', name='Admin', role='admin')
        self.client.force_authenticate(self.admin)
        StoreSettings.objects.update_or_create(pk=1, defaults={'setup_completed': True, 'business_id': 'company-a'})
        self.stock = Branch.objects.create(code='SHOP01', name='Shop One', active=True)
        self.url = '/api/v1/settings/fiscal/'
        self.company = {'registered_name': 'Acme Retail', 'tin': '123456789', 'address': 'Head Office', 'tax_type': 'vat'}

    def save(self, kind, data, id=None):
        return self.client.post(self.url, {'kind': kind, 'data': data, 'id': id}, format='json')

    def prepare(self):
        self.assertEqual(self.save('company', self.company).status_code, 200)
        b = self.save('branch', {'branch': self.stock.pk, 'branch_code': '00001', 'rdo': '039', 'registered_address': 'Shop address'})
        self.assertEqual(b.status_code, 200, b.data)
        self.branch_id = b.data['id']
        self.terminal_data = {'branch': self.branch_id, 'terminal_code': 'POS01', 'machine_serial': 'SERIAL-01', 'min': 'MIN-01', 'ptu': 'PTU-01', 'ptu_issued_on': '2026-01-01', 'starting_serial': 42}
        t = self.save('terminal', self.terminal_data)
        self.assertEqual(t.status_code, 200, t.data)
        self.terminal_id = t.data['id']

    def activate(self):
        r = self.client.post(f'{self.url}terminals/{self.terminal_id}/activate/', {'password': 'Valid password 123!', 'reviewed': True}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        return r.data['enrollment_code']

    def claim(self, code, **overrides):
        self.claim_data = getattr(self, 'claim_data', {'terminal_id': self.terminal_id, 'installation_id': str(uuid.uuid4()), 'local_terminal_id': str(uuid.uuid4()), 'enrollment_code': code})
        return self.client.post(self.url + 'enroll/', {**self.claim_data, **overrides}, format='json')

    def test_admin_only_including_inactive_and_manager(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, [401, 403])
        for role, status in [('manager', 'active'), ('admin', 'inactive')]:
            self.admin.role, self.admin.status = role, status
            self.admin.save()
            self.client.force_authenticate(self.admin)
            self.assertEqual(self.save('company', self.company).status_code, 403)

    def test_validation_leaves_no_partial_registration(self):
        for tin in ['000000000', '123', '12345678x']:
            self.assertEqual(self.save('company', {**self.company, 'tin': tin}).status_code, 400)
        self.assertFalse(FiscalCompany.objects.exists())
        self.assertFalse(FiscalAudit.objects.exists())

    def test_unique_codes_and_invalid_series(self):
        self.prepare()
        self.assertEqual(self.save('terminal', self.terminal_data).status_code, 400)
        for serial in [0, 100000000]:
            self.assertEqual(self.save('terminal', {**self.terminal_data, 'starting_serial': serial}, self.terminal_id).status_code, 400)
        self.assertEqual(FiscalTerminal.objects.get().starting_serial, 42)

    def test_draft_corrections_are_audited(self):
        self.prepare()
        r = self.save('terminal', {**self.terminal_data, 'terminal_code': 'POS02'}, self.terminal_id)
        self.assertEqual(r.status_code, 200)
        a = FiscalAudit.objects.latest('id')
        self.assertEqual(a.before['terminal_code'], 'POS01')
        self.assertEqual(a.after['terminal_code'], 'POS02')

    def test_activation_requires_password_and_review(self):
        self.prepare()
        for payload, code in [({'password': 'wrong', 'reviewed': True}, 403), ({'password': 'Valid password 123!', 'reviewed': False}, 400)]:
            self.assertEqual(self.client.post(f'{self.url}terminals/{self.terminal_id}/activate/', payload, format='json').status_code, code)
        self.assertIsNone(FiscalTerminal.objects.get().activated_at)

    def test_activation_locks_all_identity_and_hides_secret(self):
        self.prepare()
        code = self.activate()
        self.assertEqual(self.save('company', self.company).status_code, 400)
        self.assertEqual(self.save('terminal', self.terminal_data, self.terminal_id).status_code, 400)
        self.assertEqual(self.save('branch', {}, self.branch_id).status_code, 400)
        self.assertNotIn(code, str(self.client.get(self.url).data))
        self.assertNotEqual(FiscalTerminal.objects.get().enrollment_hash, code)

    def test_enrollment_snapshot_mapping_and_idempotent_retry(self):
        self.prepare()
        code = self.activate()
        r = self.claim(code)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['address'], 'Shop address')
        self.assertEqual(r.data['cloudBranchCode'], 'SHOP01')
        self.assertEqual(r.data['startingSerial'], 42)
        i = SyncInstallation.objects.get(installation_id=self.claim_data['installation_id'])
        self.assertEqual(i.branch, self.stock)
        self.assertEqual(i.local_branch_id, 'branch-main')
        self.assertEqual(i.authorized_staff, self.admin)
        again = self.claim(code)
        self.assertEqual(again.data, r.data)
        self.assertEqual(FiscalAudit.objects.filter(action='terminal.enrolled').count(), 1)

    def test_second_installation_and_wrong_secret_rejected(self):
        self.prepare()
        code = self.activate()
        self.assertEqual(self.claim(code, enrollment_code='wrong').status_code, 403)
        self.assertFalse(FiscalTerminal.objects.get().installation_id)
        self.assertEqual(self.claim(code).status_code, 200)
        self.assertEqual(self.claim(code, installation_id=str(uuid.uuid4())).status_code, 403)

    def test_unactivated_and_disabled_branches_cannot_enroll(self):
        self.prepare()
        self.assertEqual(self.claim('wrong').status_code, 403)
        code = self.activate()
        self.stock.active = False
        self.stock.save()
        self.assertEqual(self.claim(code, enrollment_code=code).status_code, 403)

    def test_legacy_general_settings_do_not_change_fiscal_identity(self):
        self.prepare()
        self.activate()
        self.client.patch('/api/v1/settings/', {'store_name': 'Display name'}, format='json')
        self.assertEqual(FiscalCompany.objects.get().registered_name, 'Acme Retail')

    def test_code_rotation_only_before_enrollment_and_invalidates_old_code(self):
        self.prepare()
        old = self.activate()
        new = self.activate()
        self.assertNotEqual(old, new)
        self.assertEqual(self.claim(old).status_code, 403)
        self.assertEqual(self.claim(new, enrollment_code=new).status_code, 200)
        self.assertEqual(self.client.post(f'{self.url}terminals/{self.terminal_id}/activate/', {'password': 'Valid password 123!', 'reviewed': True}, format='json').status_code, 400)
        self.assertEqual(FiscalAudit.objects.filter(action='terminal.enrollment_code_rotated').count(), 1)
