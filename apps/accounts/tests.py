from django.test import TestCase
from rest_framework.test import APIClient

from .models import Staff


class StaffPasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Staff.objects.create_user(
            email='admin@example.com',
            password='AdminPassword#2026',
            name='Admin User',
            role='admin',
        )
        self.cashier = Staff.objects.create_user(
            email='cashier@example.com',
            password='OriginalPassword#2026',
            name='Cashier User',
            role='cashier',
        )

    def test_admin_can_reset_staff_password_without_old_password(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f'/api/v1/staff/{self.cashier.pk}/reset_password/',
            {
                'new_password': 'ReplacementPassword#2026',
                'confirm_password': 'ReplacementPassword#2026',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.cashier.refresh_from_db()
        self.assertTrue(self.cashier.check_password('ReplacementPassword#2026'))
        self.assertFalse(self.cashier.check_password('OriginalPassword#2026'))

    def test_non_admin_cannot_reset_staff_password(self):
        self.client.force_authenticate(self.cashier)

        response = self.client.post(
            f'/api/v1/staff/{self.admin.pk}/reset_password/',
            {
                'new_password': 'ReplacementPassword#2026',
                'confirm_password': 'ReplacementPassword#2026',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('AdminPassword#2026'))

    def test_password_confirmation_must_match(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f'/api/v1/staff/{self.cashier.pk}/reset_password/',
            {
                'new_password': 'ReplacementPassword#2026',
                'confirm_password': 'DifferentPassword#2026',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['confirm_password'][0],
            'Passwords do not match.',
        )
