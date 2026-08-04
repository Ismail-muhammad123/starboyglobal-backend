from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from orders.models import VTUProviderConfig
from summary.models import SiteConfig
from orders.router import ProviderRouter
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically fetch and sync plans, networks, and variations for active providers.'

    def add_arguments(self, parser):
        parser.add_argument('--provider', type=str, help='Sync specific provider by name/id')
        parser.add_argument('--service', type=str, help='Sync specific service type (airtime, data, tv, electricity, internet, education)')
        parser.add_argument('--dry-run', action='store_true', help='Perform fetch without writing to database')

    def handle(self, *args, **options):
        config = SiteConfig.objects.first()
        provider_name = options.get('provider')
        service_type = options.get('service')
        dry_run = options.get('dry_run')

        if not options.get('provider') and not options.get('service') and config and not config.auto_sync_enabled:
            self.stdout.write(self.style.WARNING("Auto-sync is disabled in SiteConfig. Run with --provider or enable auto_sync_enabled."))
            return

        self.stdout.write(f"Starting Provider Plans Sync at {timezone.now()}")

        active_providers = VTUProviderConfig.objects.filter(is_active=True)
        if provider_name:
            active_providers = active_providers.filter(name__iexact=provider_name)

        if not active_providers.exists():
            self.stdout.write(self.style.WARNING("No matching active providers found."))
            return

        service_methods = {
            'airtime': 'sync_airtime',
            'data': 'sync_data',
            'tv': 'sync_cable',
            'electricity': 'sync_electricity',
            'internet': 'sync_internet',
            'education': 'sync_education',
        }

        if service_type:
            if service_type in service_methods:
                service_methods = {service_type: service_methods[service_type]}
            else:
                self.stdout.write(self.style.ERROR(f"Invalid service type: {service_type}"))
                return

        total_synced = 0
        for provider in active_providers:
            impl = ProviderRouter.get_provider_implementation(provider.name)
            if not impl:
                self.stdout.write(self.style.WARNING(f"Provider implementation not found for {provider.name}"))
                continue

            self.stdout.write(f"Syncing provider: {provider.get_name_display()} ({provider.name})")

            for s_type, method_name in service_methods.items():
                if dry_run:
                    fetch_method = getattr(impl, f"fetch_{s_type}_live", None)
                    if fetch_method:
                        items = fetch_method()
                        self.stdout.write(f"  [DRY-RUN] {s_type}: Fetched {len(items)} items")
                    continue

                sync_func = getattr(impl, method_name, None)
                if sync_func:
                    try:
                        count = sync_func()
                        total_synced += count
                        self.stdout.write(self.style.SUCCESS(f"  - {s_type}: Synced {count} items"))
                    except Exception as e:
                        logger.error(f"Error syncing {s_type} for {provider.name}: {e}")
                        self.stdout.write(self.style.ERROR(f"  - {s_type} error: {e}"))

        if config and not dry_run:
            now = timezone.now()
            config.auto_sync_last_run = now
            config.auto_sync_next_run = now + timedelta(hours=config.auto_sync_frequency)
            config.save(update_fields=['auto_sync_last_run', 'auto_sync_next_run'])

        self.stdout.write(self.style.SUCCESS(f"Sync Completed. Total items synced: {total_synced}"))
