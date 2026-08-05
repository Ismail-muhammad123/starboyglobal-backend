from django.db import models
from django.conf import settings


class PortalPermission(models.Model):
    """
    Granular CRUD permission for a specific portal resource/model.
    e.g. resource='users.User', action='change'
    """
    ACTIONS = [
        ('view', 'View (Read)'),
        ('add', 'Add (Create)'),
        ('change', 'Change (Update)'),
        ('delete', 'Delete'),
    ]
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=10, choices=ACTIONS)
    label = models.CharField(max_length=200)

    class Meta:
        unique_together = ('resource', 'action')
        ordering = ['resource', 'action']

    def __str__(self):
        return f"{self.label} ({self.resource} - {self.action})"


class PortalGroup(models.Model):
    """
    Named permission group (e.g. 'Finance Team', 'VTU Manager').
    Assigned to staff users. Superusers bypass all group checks.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(PortalPermission, blank=True, related_name="groups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PortalGroupMembership(models.Model):
    """Links a staff User to one or more PortalGroups."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portal_group_memberships')
    group = models.ForeignKey(PortalGroup, on_delete=models.CASCADE, related_name='memberships')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user} in {self.group.name}"


RESOURCES_LIST = [
    ('users.User', 'Users'),
    ('users.KYC', 'KYC Verification'),
    ('orders.Purchase', 'Purchases / Orders'),
    ('orders.AirtimeNetwork', 'Airtime Networks'),
    ('orders.DataService', 'Data Services'),
    ('orders.DataVariation', 'Data Variations / Plans'),
    ('orders.TVService', 'TV Services'),
    ('orders.TVVariation', 'TV Variations / Plans'),
    ('orders.ElectricityService', 'Electricity Services'),
    ('orders.ElectricityVariation', 'Electricity Variations / Plans'),
    ('orders.InternetService', 'Internet Services'),
    ('orders.InternetVariation', 'Internet Variations / Plans'),
    ('orders.EducationService', 'Education Services'),
    ('orders.EducationVariation', 'Education Variations / Plans'),
    ('orders.VTUProviderConfig', 'VTU Providers'),
    ('orders.ProviderServiceConfig', 'Provider Service Margins'),
    ('orders.ServiceRouting', 'Service Routing'),
    ('orders.AutoSyncSchedule', 'Auto Sync Schedules'),
    ('orders.AutoSyncLog', 'Auto Sync Logs'),
    ('wallet.Wallet', 'User Wallets'),
    ('wallet.WalletTransaction', 'Wallet Transactions'),
    ('payments.Deposit', 'Deposits'),
    ('payments.Withdrawal', 'Withdrawals'),
    ('payments.AdminTransfer', 'Admin Transfers'),
    ('payments.AdminTransferBeneficiary', 'Transfer Beneficiaries'),
    ('payments.PaystackConfig', 'Paystack Gateway Config'),
    ('summary.SiteConfig', 'Site Configuration'),
    ('summary.ServiceCashback', 'Service Cashback'),
    ('wallet.BonusConfig', 'Bonus Configuration'),
    ('users.ReferralConfig', 'Referral Configuration'),
    ('users.RoleUpgradeConfig', 'Role Upgrade Configuration'),
    ('orders.PromoCode', 'Promo Codes'),
    ('support.SupportTicket', 'Support Tickets'),
]


DEFAULT_GROUPS = {
    'User Manager': [
        ('users.User', ['view', 'add', 'change', 'delete']),
        ('users.KYC', ['view', 'change']),
    ],
    'VTU Manager': [
        ('orders.Purchase', ['view', 'change', 'delete']),
        ('orders.AirtimeNetwork', ['view', 'add', 'change', 'delete']),
        ('orders.DataService', ['view', 'add', 'change', 'delete']),
        ('orders.DataVariation', ['view', 'add', 'change', 'delete']),
        ('orders.TVService', ['view', 'add', 'change', 'delete']),
        ('orders.TVVariation', ['view', 'add', 'change', 'delete']),
        ('orders.ElectricityService', ['view', 'add', 'change', 'delete']),
        ('orders.ElectricityVariation', ['view', 'add', 'change', 'delete']),
        ('orders.InternetService', ['view', 'add', 'change', 'delete']),
        ('orders.InternetVariation', ['view', 'add', 'change', 'delete']),
        ('orders.EducationService', ['view', 'add', 'change', 'delete']),
        ('orders.EducationVariation', ['view', 'add', 'change', 'delete']),
        ('orders.VTUProviderConfig', ['view', 'add', 'change', 'delete']),
        ('orders.ProviderServiceConfig', ['view', 'change']),
        ('orders.ServiceRouting', ['view', 'change']),
        ('orders.AutoSyncSchedule', ['view', 'add', 'change', 'delete']),
        ('orders.AutoSyncLog', ['view']),
        ('orders.PromoCode', ['view', 'add', 'change', 'delete']),
    ],
    'Finance Team': [
        ('wallet.Wallet', ['view', 'change']),
        ('wallet.WalletTransaction', ['view', 'add']),
        ('payments.Deposit', ['view', 'change', 'delete']),
        ('payments.Withdrawal', ['view', 'change', 'delete']),
        ('payments.AdminTransfer', ['view', 'add']),
        ('payments.AdminTransferBeneficiary', ['view', 'add', 'delete']),
        ('payments.PaystackConfig', ['view', 'change']),
    ],
    'Support Agent': [
        ('users.User', ['view']),
        ('orders.Purchase', ['view']),
        ('support.SupportTicket', ['view', 'change', 'delete']),
    ],
    'Admin': [
        ('summary.SiteConfig', ['view', 'change']),
        ('summary.ServiceCashback', ['view', 'add', 'change', 'delete']),
        ('wallet.BonusConfig', ['view', 'add', 'change', 'delete']),
        ('users.ReferralConfig', ['view', 'change']),
        ('users.RoleUpgradeConfig', ['view', 'change']),
    ],
}


def seed_permissions_if_empty():
    """Seeds all PortalPermissions and DEFAULT_GROUPS if not present."""
    action_labels = {
        'view': 'Can view',
        'add': 'Can add',
        'change': 'Can edit',
        'delete': 'Can delete',
    }

    # 1. Create permissions
    for res_code, res_title in RESOURCES_LIST:
        for act_code, act_title in PortalPermission.ACTIONS:
            label = f"{action_labels.get(act_code, act_code)} {res_title}"
            PortalPermission.objects.get_or_create(
                resource=res_code,
                action=act_code,
                defaults={'label': label}
            )

    # 2. Create default groups and assign permissions
    for grp_name, perms_spec in DEFAULT_GROUPS.items():
        group, _ = PortalGroup.objects.get_or_create(
            name=grp_name,
            defaults={'description': f"Default group for {grp_name}"}
        )
        for res_code, actions in perms_spec:
            for act_code in actions:
                try:
                    perm = PortalPermission.objects.get(resource=res_code, action=act_code)
                    group.permissions.add(perm)
                except PortalPermission.DoesNotExist:
                    pass
