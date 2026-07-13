from django.db import models
from django.conf import settings
from django.utils import timezone
from .providers.registry import AVAILABLE_PROVIDERS


SERVICES = (
    ('mtn', 'MTN'),
    ('glo', 'GLO'),
    ('airtel', 'AIRTEL'),
    ('9mobile', '9MOBILE'),
)

class PurchaseBeneficiary(models.Model):
    PURCHASE_TYPES = [
        ('airtime', 'Airtime'),
        ('data', 'Data'),
        ('electricity', 'Electricity'),
        ('tv', 'TV Subscription'),
        ('education', 'Education'),
        ('internet', 'Internet Subscription'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchase_beneficiaries")
    service_type = models.CharField(max_length=20, choices=PURCHASE_TYPES)
    identifier = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Purchase Beneficiary"
        verbose_name_plural = "Purchase Beneficiaries"
        unique_together = ('user', 'service_type', 'identifier')

    def __str__(self):
        return f"{self.nickname or self.identifier} ({self.get_service_type_display()})"


PLAN_TYPES = [
    ('sme', 'SME'),
    ('corporate', 'Corporate'),
    ('gifting', 'Gifting'),
    ('direct', 'Direct'),
    ('general', 'General'),
]

class RestrictedSyncManager(models.Manager):
    def update_or_create(self, defaults=None, **kwargs):
        defaults = defaults or {}
        try:
            obj = self.get(**kwargs)
            name_field = 'service_name' if self.model.__name__ == 'AirtimeNetwork' else 'name'
            filtered_defaults = {}
            if name_field in defaults:
                filtered_defaults[name_field] = defaults[name_field]
            if 'cost_price' in defaults:
                filtered_defaults['cost_price'] = defaults['cost_price']
            
            for k, v in filtered_defaults.items():
                setattr(obj, k, v)
            obj.save(using=self._db)
            return obj, False
        except self.model.DoesNotExist:
            params = {k: v for k, v in defaults.items()}
            params.update(kwargs)
            obj = self.model(**params)
            obj.save(force_insert=True, using=self._db)
            return obj, True

class DataService(models.Model):
    service_name=models.CharField(max_length=100)
    service_id= models.CharField(max_length=100)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='data_services')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_name

class AirtimeNetwork(models.Model):
    objects = RestrictedSyncManager()
    service_name = models.CharField(max_length=200)
    service_id = models.CharField(max_length=100)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='airtime_networks')
    min_amount = models.CharField(max_length=10, default="50")
    max_amount = models.CharField(max_length=10, default="200000")
    discount = models.CharField(max_length=10, default="0")
    agent_discount = models.CharField(max_length=10, default="0")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    agent_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    developer_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='networks/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_name
    
class ElectricityService(models.Model):
    service_name=models.CharField(max_length=100)
    service_id= models.CharField(max_length=100)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='electricity_services')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_name
    
    class Meta:
        verbose_name = "Electricity Service"
        verbose_name_plural = "Electricity Services"

class ElectricityVariation(models.Model):
    objects = RestrictedSyncManager()
    name = models.CharField(max_length=255)   
    service = models.ForeignKey(ElectricityService, on_delete=models.CASCADE, related_name="variations", null=True)
    variation_id = models.CharField(max_length=100)
    
    min_amount = models.CharField(max_length=10, default="1000")
    max_amount = models.CharField(max_length=10, default="200000")
    discount = models.CharField(max_length=10, default="0")
    agent_discount = models.CharField(max_length=10, default="0")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount the provider charges the platform")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    developer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='general')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Electricity Variation"
        verbose_name_plural = "Electricity Variations"

    def __str__(self):
        return f"{self.service.service_name} - {self.name}"

class TVService(models.Model):
    service_name=models.CharField(max_length=100)
    service_id= models.CharField(max_length=100)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='tv_services')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_name
    
    class Meta:
        verbose_name = "TV Service"
        verbose_name_plural = "TV Services"

class TVVariation(models.Model):
    objects = RestrictedSyncManager()
    name = models.CharField(max_length=255)   
    service = models.ForeignKey(TVService, on_delete=models.CASCADE, related_name="variations", null=True)
    variation_id = models.CharField(max_length=100)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount the provider charges the platform")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    developer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='general')
    package_bouquet = models.CharField(max_length=255, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TV Variation"
        verbose_name_plural = "TV Variations"


    def __str__(self):
        return self.name

class InternetService(models.Model):
    service_name = models.CharField(max_length=100, default="Internet Subscription")
    service_id = models.CharField(max_length=100)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='internet_services')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_name

class InternetVariation(models.Model):
    objects = RestrictedSyncManager()
    name = models.CharField(max_length=255)   
    service = models.ForeignKey(InternetService, on_delete=models.CASCADE, related_name="variations", null=True)
    variation_id = models.CharField(max_length=100)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    developer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='general')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Internet Variation"
        verbose_name_plural = "Internet Variations"

    def __str__(self):
        return self.name

class DataVariation(models.Model):
    objects = RestrictedSyncManager()
    name = models.CharField(max_length=255)   
    service = models.ForeignKey(DataService, on_delete=models.CASCADE, related_name="variations", null=True)
    variation_id = models.CharField(max_length=100)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)   
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    developer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='general')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Data Variation"
        verbose_name_plural = "Data Variations"


    def __str__(self):
        return f"{self.name} - {self.service.provider}"

class EducationService(models.Model):
    service_name = models.CharField(max_length=100)
    service_id = models.CharField(max_length=100, unique=True)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='education_services')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_name

class EducationVariation(models.Model):
    objects = RestrictedSyncManager()
    service = models.ForeignKey(EducationService, on_delete=models.CASCADE, related_name='variations')
    name = models.CharField(max_length=255)
    variation_id = models.CharField(max_length=100)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agent_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    developer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service.service_name} - {self.name}"

class Purchase(models.Model):
    PURCHASE_TYPES = (
        ('data', 'Data'),
        ('airtime', 'Airtime'),
        ('electricity', 'Electricity'),
        ('tv', 'TV Subscription'),
        ('internet', 'Internet Subscription'),
        ('education', 'Education'),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )
    INITIATOR_CHOICES = [
        ("self", "Self"),
        ("admin", "Admin"),
    ]

    purchase_type = models.CharField(max_length=50, choices=PURCHASE_TYPES)  # 'data' or 'airtime'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    # airtime_network = models.CharField(max_length=100, null=True, blank=True, choices=AIRTIME_NETWORKS)
    airtime_service = models.ForeignKey(AirtimeNetwork, on_delete=models.SET_NULL, null=True, related_name="sales")
    data_variation = models.ForeignKey(DataVariation, on_delete=models.SET_NULL, null=True, related_name="sales")
    electricity_service = models.ForeignKey(ElectricityService, on_delete=models.SET_NULL, null=True, related_name="sales")
    electricity_variation = models.ForeignKey(ElectricityVariation, on_delete=models.SET_NULL, null=True, related_name="sales")
    tv_variation = models.ForeignKey(TVVariation, on_delete=models.SET_NULL, null=True, related_name="sales")
    internet_variation = models.ForeignKey(InternetVariation, on_delete=models.SET_NULL, null=True, related_name="sales")
    education_variation = models.ForeignKey(EducationVariation, on_delete=models.SET_NULL, null=True, related_name="sales")
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    beneficiary = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    initiator = models.CharField(max_length=10, choices=INITIATOR_CHOICES, default="self")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="initiated_purchases")
    
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_purchases')
    remarks = models.TextField(blank=True, null=True)
    
    provider_response = models.JSONField(default=dict, blank=True, null=True)
    provider = models.ForeignKey('VTUProviderConfig', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    token = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    time = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.purchase_type} purchase to {self.beneficiary}"


class VTUProviderConfig(models.Model):
    """Configuration for each VTU API provider."""
    
    PROVIDER_CHOICES = AVAILABLE_PROVIDERS

    name = models.CharField(max_length=20, choices=PROVIDER_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    
    # Standard Credentials
    api_key = models.CharField(max_length=500, blank=True, null=True)
    user_id = models.CharField(max_length=255, blank=True, null=True)
    session_id = models.CharField(max_length=500, blank=True, null=True)
    secret_key = models.TextField(blank=True, null=True)
    public_key = models.TextField(blank=True, null=True)
    base_url = models.URLField(blank=True, null=True)
    
    def get_config_dict(self):
        return {
            'api_key': self.api_key,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'secret_key': self.secret_key,
            'public_key': self.public_key,
            'base_url': self.base_url,
        }
    
    # Global fallbacks settings (Defaults)
    max_retries = models.PositiveIntegerField(default=3)
    auto_refund_on_failure = models.BooleanField(default=True)
    
    # Funding Information
    account_name = models.CharField(max_length=255, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_code = models.CharField(max_length=10, blank=True, null=True)
    
    # Auto-funding settings
    min_funding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=5000)
    auto_funding_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()

    @property
    def webhook_url(self):
        """Returns the absolute URL for this provider's webhook."""
        from django.urls import reverse
        try:
            return reverse('vtu-webhook', kwargs={'provider_name': self.name})
        except:
            return f"/api/orders/webhook/{self.name}/"

    @property
    def callback_url(self):
        """Returns the absolute URL for this provider's callback."""
        from django.urls import reverse
        try:
            return reverse('vtu-callback', kwargs={'provider_name': self.name})
        except:
            return f"/api/orders/callback/{self.name}/"



    class Meta:
        verbose_name = "VTU Provider Config"
        verbose_name_plural = "VTU Provider Configs"

    def __str__(self):
        return self.get_name_display()


class ServiceRouting(models.Model):
    SERVICE_CHOICES = [
        ('airtime', 'Airtime'),
        ('data', 'Data'),
        ('electricity', 'Electricity'),
        ('tv', 'Cable TV'),
        ('internet', 'Internet Sub'),
        ('education', 'Education'),
    ]

    service = models.CharField(max_length=20, choices=SERVICE_CHOICES, unique=True)
    primary_provider = models.ForeignKey(VTUProviderConfig, on_delete=models.SET_NULL, null=True, related_name='primary_for_services')
    
    # Automation & Routing
    retry_enabled = models.BooleanField(default=True)
    retry_count = models.PositiveIntegerField(default=2)
    auto_refund_enabled = models.BooleanField(default=True)
    fallback_enabled = models.BooleanField(default=True) # Switch to alternative providers
    
    # Pricing Mode
    pricing_mode = models.CharField(
        max_length=20, 
        choices=[('fixed_margin', 'Fixed Margin'), ('defined', 'Defined Pricing')], 
        default='defined'
    )
    customer_margin = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Fixed amount/percentage to add to cost for users")
    agent_margin = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Fixed amount/percentage to add to cost for agents")
    developer_margin = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Fixed amount/percentage to add to cost for developers")

    # Fallback chain (ordered list of provider IDs or names)
    # We can use a many-to-many relationship with an through model to maintain order
    fallbacks = models.ManyToManyField(VTUProviderConfig, through='ServiceFallback', related_name='fallback_for_services')

    class Meta:
        verbose_name = "Service Routing"
        verbose_name_plural = "Service Routings"

    def __str__(self):
        return f"{self.get_service_display()} Routing"


class ServiceFallback(models.Model):
    service_routing = models.ForeignKey(ServiceRouting, on_delete=models.CASCADE)
    provider = models.ForeignKey(VTUProviderConfig, on_delete=models.CASCADE)
    priority = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['priority']
        unique_together = ('service_routing', 'provider')

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        return self.is_active and self.used_count < self.max_uses and self.expiry_date > timezone.now()

    def __str__(self):
        return self.code

class PurchasePromoUsed(models.Model):
    purchase = models.OneToOneField(Purchase, on_delete=models.CASCADE, related_name="promo_usage")
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Promo {self.promo_code.code} on {self.purchase.reference}"


class DynamicVTUProvider(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    base_url = models.URLField()
    api_key_header = models.CharField(max_length=100, default="Authorization")
    api_key_prefix = models.CharField(max_length=100, default="Token ", blank=True)
    api_key = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    
    # Generic Config
    request_format = models.CharField(max_length=10, choices=[('json', 'JSON'), ('params', 'Query Params')], default='json')
    response_format = models.CharField(max_length=10, choices=[('json', 'JSON')], default='json')
    
    def __str__(self):
        return self.name

class DynamicProviderHeader(models.Model):
    provider = models.ForeignKey(DynamicVTUProvider, on_delete=models.CASCADE, related_name="custom_headers")
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=500, help_text="Can use {api_key}")

    def __str__(self):
        return f"{self.key}: {self.value}"

class DynamicOperationConfig(models.Model):
    OPERATIONS = [
        ('get_networks', 'Get Networks'),
        ('get_variations', 'Get Variations/Packages'),
        ('purchase', 'Purchase Service'),
        ('verify', 'Verify Status'),
        ('balance', 'Check Balance'),
        ('verify_customer', 'Verify Customer/Meter'),
    ]
    provider = models.ForeignKey(DynamicVTUProvider, on_delete=models.CASCADE, related_name="operations")
    operation_type = models.CharField(max_length=50, choices=OPERATIONS)
    endpoint_path = models.CharField(max_length=255, help_text="e.g. /api/data/")
    method = models.CharField(max_length=10, choices=[('GET', 'GET'), ('POST', 'POST')], default='POST')
    
    # Mapping fields (JSON)
    # Params mapping: {"network_id": "network", "amount": "amount"}
    request_params = models.JSONField(default=dict, blank=True, help_text="Mapping from our internal names to theirs")
    static_params = models.JSONField(default=dict, blank=True, help_text="Always sent with request")
    
    # Response mapping
    success_mapping = models.JSONField(default=dict, blank=True, help_text="e.g. {'status': 'success', 'code': 200}")
    failure_mapping = models.JSONField(default=dict, blank=True, help_text="e.g. {'status': 'fail'}")
    
    # Data extraction mapping: maps provider field to our internal field
    # e.g. {'provider_reference': 'order_id', 'token': 'pin_code'}
    response_data_mapping = models.JSONField(default=dict, blank=True, help_text="Map provider fields to internal fields")

    def __str__(self):
        return f"{self.provider.name} - {self.get_operation_type_display()}"

class DynamicOperationHeader(models.Model):
    operation = models.ForeignKey(DynamicOperationConfig, on_delete=models.CASCADE, related_name="custom_headers")
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=500, help_text="Can use {api_key}, {phone}, etc.")

class DynamicOperationPayload(models.Model):
    operation = models.ForeignKey(DynamicOperationConfig, on_delete=models.CASCADE, related_name="custom_payload")
    key = models.CharField(max_length=100)
    value = models.CharField(max_length=500, help_text="Can use {phone}, {amount}, etc.")
