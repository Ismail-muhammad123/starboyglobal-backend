import json
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

    def test_revenue_chart_data_endpoint(self):
        self.client.login(username='08000000000', password='superuserpass')
        response = self.client.get(reverse('portal:chart_revenue'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('labels', data)
        self.assertIn('datasets', data)
        self.assertEqual(len(data['datasets']), 3)
        self.assertEqual(data['datasets'][0]['label'], 'Revenue (₦)')
        self.assertEqual(data['datasets'][1]['label'], 'Cost (₦)')
        self.assertEqual(data['datasets'][2]['label'], 'Profit / Loss (₦)')

    def test_bulk_variation_actions(self):
        from orders.models import DataService, DataVariation
        self.client.login(username='08000000000', password='superuserpass')

        svc = DataService.objects.create(service_name='MTN Test', service_id='mtn-test')
        v1 = DataVariation.objects.create(service=svc, name='1GB', variation_id='v1', is_active=True)
        v2 = DataVariation.objects.create(service=svc, name='2GB', variation_id='v2', is_active=True)

        # Deactivate bulk action
        resp = self.client.post(
            reverse('portal:bulk_variation_action'),
            data=json.dumps({'item_type': 'data_variation', 'action': 'deactivate', 'ids': [v1.pk, v2.pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertFalse(v1.is_active)
        self.assertFalse(v2.is_active)

        # Activate bulk action
        resp = self.client.post(
            reverse('portal:bulk_variation_action'),
            data=json.dumps({'item_type': 'data_variation', 'action': 'activate', 'ids': [v1.pk, v2.pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        v1.refresh_from_db()
        self.assertTrue(v1.is_active)

        # Delete bulk action
        resp = self.client.post(
            reverse('portal:bulk_variation_action'),
            data=json.dumps({'item_type': 'data_variation', 'action': 'delete', 'ids': [v1.pk, v2.pk]}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(DataVariation.objects.filter(pk__in=[v1.pk, v2.pk]).exists())

    def test_deactivate_unreturned_items_on_sync(self):
        from orders.models import VTUProviderConfig, DataService, DataVariation
        from orders.utils.sync_runner import deactivate_unreturned_items

        prov = VTUProviderConfig.objects.create(name='flowpay', api_key='testkey', is_active=True)
        svc = DataService.objects.create(service_name='FlowPay MTN', service_id='mtn', provider=prov)
        
        v1 = DataVariation.objects.create(service=svc, name='1GB', variation_id='fp1', is_active=True)
        v2 = DataVariation.objects.create(service=svc, name='Old Obsolete 500MB', variation_id='fp_old', is_active=True)

        # Assume provider sync response only returned v1 (fp1)
        count = deactivate_unreturned_items(prov, 'data', synced_pks=[v1.pk])
        self.assertEqual(count, 1)

        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertTrue(v1.is_active)
        self.assertFalse(v2.is_active)

    def test_transaction_charges_portal_view(self):
        from wallet.models import TransactionCharge
        self.client.login(username='08000000000', password='superuserpass')

        # GET page
        res = self.client.get(reverse('portal:transaction_charges'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Transaction Charges Configuration")

        # POST create
        create_res = self.client.post(reverse('portal:transaction_charges'), {
            'name': 'Portal Test Charge',
            'transaction_type': 'transfer_p2p',
            'charge_type': 'percentage',
            'amount': '1.5',
            'cap': '100.00',
            'min_transaction_amount': '200.00',
            'max_transaction_amount': '10000.00',
            'block_if_insufficient': 'on',
            'is_active': 'on'
        })
        self.assertEqual(create_res.status_code, 200)
        self.assertEqual(create_res.json()['status'], 'success')
        
        charge = TransactionCharge.objects.get(name='Portal Test Charge')
        self.assertEqual(charge.transaction_type, 'transfer_p2p')
        self.assertEqual(charge.amount, 1.5)
        self.assertTrue(charge.block_if_insufficient)

        # POST delete
        del_res = self.client.post(reverse('portal:transaction_charges'), {
            '_delete': '1',
            'charge_id': str(charge.pk)
        })
        self.assertEqual(del_res.status_code, 200)
        self.assertFalse(TransactionCharge.objects.filter(pk=charge.pk).exists())
