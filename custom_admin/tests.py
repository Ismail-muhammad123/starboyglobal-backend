from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from custom_admin.permissions import seed_permissions_if_empty, PortalGroup, PortalPermission


class CustomAdminTests(TestCase):
    def setUp(self):
        seed_permissions_if_empty()
        self.client = Client()

        self.superuser = User.objects.create_superuser(
            phone_number='08000000000',
            password='superuserpass',
            first_name='Super',
            last_name='User'
        )

        self.staff_user = User.objects.create_user(
            phone_number='08111111111',
            password='staffuserpass',
            first_name='Staff',
            last_name='User',
            is_staff=True
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse('portal:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard Login")

    def test_login_authentication(self):
        response = self.client.post(reverse('portal:login'), {
            'phone_number': '08000000000',
            'password': 'superuserpass'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('portal:dashboard'))

    def test_dashboard_access_for_superuser(self):
        self.client.login(username='08000000000', password='superuserpass')
        response = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Overview")

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('portal:login')))
