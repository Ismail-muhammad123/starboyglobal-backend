from django.core.management.base import BaseCommand
from custom_admin.permissions import seed_permissions_if_empty


class Command(BaseCommand):
    help = "Seeds initial PortalPermissions and default PortalGroups for custom_admin"

    def handle(self, *args, **options):
        seed_permissions_if_empty()
        self.stdout.write(self.style.SUCCESS("Successfully seeded portal permissions and default groups."))
