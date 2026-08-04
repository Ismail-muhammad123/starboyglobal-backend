from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.models import VTUProviderConfig, ServiceRouting, ProviderServiceConfig, DataService, DataVariation
from summary.models import SiteConfig
from orders.utils.pricing import apply_margin, get_provider_service_config, resolve_margin_for_role
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

    def test_sync_provider_plans_dry_run(self):
        call_command('sync_provider_plans', '--dry-run')
        self.site_config.refresh_from_db()
        self.assertIsNone(self.site_config.auto_sync_last_run)
