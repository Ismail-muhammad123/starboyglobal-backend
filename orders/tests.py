from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.models import VTUProviderConfig, ServiceRouting, ProviderServiceConfig, DataService, DataVariation
from summary.models import SiteConfig
from orders.utils.pricing import apply_margin, get_provider_service_config, resolve_margin_for_role
from orders.router import ProviderRouter
from django.core.management import call_command

User = get_user_model()



class CatalogueAndSyncTestCase(TestCase):
    def setUp(self):
        self.site_config = SiteConfig.objects.create(
            data_margin=Decimal('50.00'),
            auto_sync_enabled=True,
            auto_sync_frequency=12
        )
        self.provider = VTUProviderConfig.objects.create(
            name='vtpass',
            is_active=True,
            api_key='test_key'
        )
        self.routing = ServiceRouting.objects.create(
            service='data',
            primary_provider=self.provider
        )

    def test_apply_margin_flat(self):
        cost = Decimal('500.00')
        # Flat margin of 50
        selling = apply_margin(cost, Decimal('50.00'), 'flat')
        self.assertEqual(selling, Decimal('550.00'))

        # Flat margin of 0
        selling_zero = apply_margin(cost, Decimal('0.00'), 'flat')
        self.assertEqual(selling_zero, Decimal('500.00'))

    def test_apply_margin_percentage(self):
        cost = Decimal('1000.00')
        # 10% margin
        selling = apply_margin(cost, Decimal('10.00'), 'percentage')
        self.assertEqual(selling, Decimal('1100.00'))

        # 5.5% margin
        selling_perc = apply_margin(cost, Decimal('5.50'), 'percentage')
        self.assertEqual(selling_perc, Decimal('1055.00'))

    def test_provider_service_config_margins_per_role(self):
        ps_config = ProviderServiceConfig.objects.create(
            provider=self.provider,
            service_type='data',
            catalogue_source='live',
            customer_margin_type='flat',
            customer_margin_value=Decimal('50.00'),
            agent_margin_type='percentage',
            agent_margin_value=Decimal('3.00'),
            developer_margin_type='flat',
            developer_margin_value=Decimal('10.00'),
        )

        resolved = get_provider_service_config(self.provider, 'data')
        self.assertEqual(resolved['catalogue_source'], 'live')

        cust_type, cust_val = resolve_margin_for_role(resolved, 'customer')
        self.assertEqual(cust_type, 'flat')
        self.assertEqual(cust_val, Decimal('50.00'))

        agent_type, agent_val = resolve_margin_for_role(resolved, 'agent')
        self.assertEqual(agent_type, 'percentage')
        self.assertEqual(agent_val, Decimal('3.00'))

        dev_type, dev_val = resolve_margin_for_role(resolved, 'developer')
        self.assertEqual(dev_type, 'flat')
        self.assertEqual(dev_val, Decimal('10.00'))

    def test_inline_provider_service_config_uniqueness_and_serializer(self):
        from django.db.utils import IntegrityError
        from admin_api.serializers.vtu import VTUProviderConfigSerializer

        # 1. Verify DB uniqueness per provider per service
        from django.db import transaction
        ProviderServiceConfig.objects.create(
            provider=self.provider,
            service_type='data',
            catalogue_source='live'
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProviderServiceConfig.objects.create(
                    provider=self.provider,
                    service_type='data',
                    catalogue_source='db'
                )


        # 2. Verify serializer inline creation & update
        provider2 = VTUProviderConfig.objects.create(name='flowpay', is_active=True)
        serializer_data = {
            "name": "flowpay",
            "is_active": True,
            "service_configs": [
                {
                    "service_type": "airtime",
                    "catalogue_source": "live",
                    "customer_margin_type": "flat",
                    "customer_margin_value": "20.00"
                },
                {
                    "service_type": "data",
                    "catalogue_source": "db",
                    "customer_margin_type": "percentage",
                    "customer_margin_value": "5.00"
                }
            ]
        }
        serializer = VTUProviderConfigSerializer(provider2, data=serializer_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        configs = provider2.service_configs.all()
        self.assertEqual(configs.count(), 2)
        airtime_cfg = configs.get(service_type='airtime')
        self.assertEqual(airtime_cfg.catalogue_source, 'live')
        self.assertEqual(airtime_cfg.customer_margin_value, Decimal('20.00'))

        # 3. Verify duplicate service_type validation error in inline serializer
        invalid_data = {
            "service_configs": [
                {"service_type": "data", "catalogue_source": "db"},
                {"service_type": "data", "catalogue_source": "live"}
            ]
        }
        inv_serializer = VTUProviderConfigSerializer(provider2, data=invalid_data, partial=True)
        self.assertFalse(inv_serializer.is_valid())
        self.assertIn('service_configs', inv_serializer.errors)

        provider2.delete()


    @patch.object(ProviderRouter, 'get_provider_implementation')

    def test_sync_provider_plans_dry_run(self, mock_get_impl):

        mock_impl = MagicMock()
        mock_impl.fetch_data_live.return_value = [{'id': 1, 'name': '1GB', 'cost_price': 200}]
        mock_get_impl.return_value = mock_impl

        call_command('sync_provider_plans', '--dry-run')
        self.site_config.refresh_from_db()
        self.assertIsNone(self.site_config.auto_sync_last_run)

    @patch.object(ProviderRouter, 'get_provider_implementation')
    def test_auto_sync_schedule_and_execution_logging(self, mock_get_impl):
        mock_impl = MagicMock()
        mock_impl.sync_data.return_value = 5
        mock_get_impl.return_value = mock_impl



        from orders.models import AutoSyncSchedule, AutoSyncLog
        from orders.utils.sync_runner import execute_sync_schedule

        schedule = AutoSyncSchedule.objects.create(
            name="Daily Data Sync for VTPass",
            provider=self.provider,
            service_type="data",
            frequency="daily",
            is_active=True
        )
        self.assertTrue(schedule.is_active)

        # Execute schedule
        execute_sync_schedule(schedule.id)

        # Verify schedule updated last_run and next_run
        schedule.refresh_from_db()
        self.assertIsNotNone(schedule.last_run)
        self.assertIsNotNone(schedule.next_run)

        # Verify immutable log entry was created
        log = AutoSyncLog.objects.filter(schedule=schedule).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.schedule_name, "Daily Data Sync for VTPass")
        self.assertEqual(log.provider_name, "VTPass")
        self.assertEqual(log.items_synced, 5)

        # Test log immutability - updates should fail
        log.items_synced = 999
        with self.assertRaises(ValueError):
            log.save()

        # Test log immutability - deletes without force should fail
        with self.assertRaises(ValueError):
            log.delete()


class UnlinkedProviderFilteringTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='08012345678',
            password='testpassword',
            transaction_pin='1234'
        )
        from wallet.models import Wallet
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('1000.00'))

        self.vtpass_provider = VTUProviderConfig.objects.create(name='vtpass', is_active=True)
        self.ck_provider = VTUProviderConfig.objects.create(name='clubkonnect', is_active=True)
        
        self.routing = ServiceRouting.objects.create(
            service='data',
            primary_provider=self.vtpass_provider
        )

        # Services
        self.svc_vtpass = DataService.objects.create(service_name='MTN (VTPass)', service_id='1', provider=self.vtpass_provider, is_active=True)
        self.svc_ck = DataService.objects.create(service_name='MTN (ClubKonnect)', service_id='1', provider=self.ck_provider, is_active=True)
        self.svc_unlinked = DataService.objects.create(service_name='MTN (Unlinked)', service_id='1', provider=None, is_active=True)

        # Variations
        self.var_vtpass = DataVariation.objects.create(service=self.svc_vtpass, name='1GB VTPass', variation_id='v_vt', selling_price=Decimal('100.00'), cost_price=Decimal('80.00'), is_active=True)
        self.var_ck = DataVariation.objects.create(service=self.svc_ck, name='1GB CK', variation_id='v_ck', selling_price=Decimal('100.00'), cost_price=Decimal('80.00'), is_active=True)
        self.var_unlinked = DataVariation.objects.create(service=self.svc_unlinked, name='1GB Unlinked', variation_id='v_un', selling_price=Decimal('100.00'), cost_price=Decimal('80.00'), is_active=True)

    def test_unlinked_services_and_variations_excluded_from_api_list(self):
        from orders.views.list_views import _active_services_with_routing_fallback, _get_variations_queryset
        
        # Test active services query: only returns services for primary routed provider (vtpass), unlinked service is excluded
        services = list(_active_services_with_routing_fallback(DataService, 'data'))
        self.assertIn(self.svc_vtpass, services)
        self.assertNotIn(self.svc_unlinked, services)
        self.assertNotIn(self.svc_ck, services)

        # Test variations query without param: only returns variations for primary routed provider
        variations = list(_get_variations_queryset(DataVariation, 'data'))
        self.assertIn(self.var_vtpass, variations)
        self.assertNotIn(self.var_unlinked, variations)
        self.assertNotIn(self.var_ck, variations)

    def test_variations_filtered_by_selected_service_provider(self):
        from orders.views.list_views import _get_variations_queryset

        # Query specifically for vtpass service PK
        vtpass_vars = list(_get_variations_queryset(DataVariation, 'data', service_param=self.svc_vtpass.id))
        self.assertEqual(vtpass_vars, [self.var_vtpass])

        # Query specifically for unlinked service PK -> should return empty list
        unlinked_vars = list(_get_variations_queryset(DataVariation, 'data', service_param=self.svc_unlinked.id))
        self.assertEqual(unlinked_vars, [])

    def test_purchase_fails_if_unlinked_provider_without_debiting_wallet(self):
        from orders.utils.purchase_logic import purchase_data

        res = purchase_data(
            user=self.user,
            plan=self.var_unlinked,
            phone='08012345678',
            reference='TEST_REF_UNLINKED'
        )

        self.assertEqual(res['status'], 'failed')
        self.assertIn('No active provider linked', res['error'])

        # Verify wallet was NOT debited
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('1000.00'))



