from decimal import Decimal
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password as django_check_password
from django.db import models
from django.core.exceptions import ValidationError
import uuid
import string
import random


country_phone_codes = {
    "Afghanistan": "+93",
    "Albania": "+355",
    "Algeria": "+213",
    "Andorra": "+376",
    "Angola": "+244",
    "Antigua and Barbuda": "+1-268",
    "Argentina": "+54",
    "Armenia": "+374",
    "Australia": "+61",
    "Austria": "+43",
    "Azerbaijan": "+994",
    "Bahamas": "+1-242",
    "Bahrain": "+973",
    "Bangladesh": "+880",
    "Barbados": "+1-246",
    "Belarus": "+375",
    "Belgium": "+32",
    "Belize": "+501",
    "Benin": "+229",
    "Bhutan": "+975",
    "Bolivia": "+591",
    "Bosnia and Herzegovina": "+387",
    "Botswana": "+267",
    "Brazil": "+55",
    "Brunei": "+673",
    "Bulgaria": "+359",
    "Burkina Faso": "+226",
    "Burundi": "+257",
    "Cambodia": "+855",
    "Cameroon": "+237",
    "Canada": "+1",
    "Cape Verde": "+238",
    "Central African Republic": "+236",
    "Chad": "+235",
    "Chile": "+56",
    "China": "+86",
    "Colombia": "+57",
    "Comoros": "+269",
    "Congo (Brazzaville)": "+242",
    "Congo (Kinshasa)": "+243",
    "Costa Rica": "+506",
    "Croatia": "+385",
    "Cuba": "+53",
    "Cyprus": "+357",
    "Czech Republic": "+420",
    "Denmark": "+45",
    "Djibouti": "+253",
    "Dominica": "+1-767",
    "Dominican Republic": "+1-809",
    "Ecuador": "+593",
    "Egypt": "+20",
    "El Salvador": "+503",
    "Equatorial Guinea": "+240",
    "Eritrea": "+291",
    "Estonia": "+372",
    "Eswatini": "+268",
    "Ethiopia": "+251",
    "Fiji": "+679",
    "Finland": "+358",
    "France": "+33",
    "Gabon": "+241",
    "Gambia": "+220",
    "Georgia": "+995",
    "Germany": "+49",
    "Ghana": "+233",
    "Greece": "+30",
    "Grenada": "+1-473",
    "Guatemala": "+502",
    "Guinea": "+224",
    "Guinea-Bissau": "+245",
    "Guyana": "+592",
    "Haiti": "+509",
    "Honduras": "+504",
    "Hungary": "+36",
    "Iceland": "+354",
    "India": "+91",
    "Indonesia": "+62",
    "Iran": "+98",
    "Iraq": "+964",
    "Ireland": "+353",
    "Israel": "+972",
    "Italy": "+39",
    "Jamaica": "+1-876",
    "Japan": "+81",
    "Jordan": "+962",
    "Kazakhstan": "+7",
    "Kenya": "+254",
    "Kiribati": "+686",
    "Kuwait": "+965",
    "Kyrgyzstan": "+996",
    "Laos": "+856",
    "Latvia": "+371",
    "Lebanon": "+961",
    "Lesotho": "+266",
    "Liberia": "+231",
    "Libya": "+218",
    "Liechtenstein": "+423",
    "Lithuania": "+370",
    "Luxembourg": "+352",
    "Madagascar": "+261",
    "Malawi": "+265",
    "Malaysia": "+60",
    "Maldives": "+960",
    "Mali": "+223",
    "Malta": "+356",
    "Marshall Islands": "+692",
    "Mauritania": "+222",
    "Mauritius": "+230",
    "Mexico": "+52",
    "Micronesia": "+691",
    "Moldova": "+373",
    "Monaco": "+377",
    "Mongolia": "+976",
    "Montenegro": "+382",
    "Morocco": "+212",
    "Mozambique": "+258",
    "Myanmar (Burma)": "+95",
    "Namibia": "+264",
    "Nauru": "+674",
    "Nepal": "+977",
    "Netherlands": "+31",
    "New Zealand": "+64",
    "Nicaragua": "+505",
    "Niger": "+227",
    "Nigeria": "+234",
    "North Korea": "+850",
    "North Macedonia": "+389",
    "Norway": "+47",
    "Oman": "+968",
    "Pakistan": "+92",
    "Palau": "+680",
    "Palestine": "+970",
    "Panama": "+507",
    "Papua New Guinea": "+675",
    "Paraguay": "+595",
    "Peru": "+51",
    "Philippines": "+63",
    "Poland": "+48",
    "Portugal": "+351",
    "Qatar": "+974",
    "Romania": "+40",
    "Russia": "+7",
    "Rwanda": "+250",
    "Saint Kitts and Nevis": "+1-869",
    "Saint Lucia": "+1-758",
    "Saint Vincent and the Grenadines": "+1-784",
    "Samoa": "+685",
    "San Marino": "+378",
    "Sao Tome and Principe": "+239",
    "Saudi Arabia": "+966",
    "Senegal": "+221",
    "Serbia": "+381",
    "Seychelles": "+248",
    "Sierra Leone": "+232",
    "Singapore": "+65",
    "Slovakia": "+421",
    "Slovenia": "+386",
    "Solomon Islands": "+677",
    "Somalia": "+252",
    "South Africa": "+27",
    "South Korea": "+82",
    "South Sudan": "+211",
    "Spain": "+34",
    "Sri Lanka": "+94",
    "Sudan": "+249",
    "Suriname": "+597",
    "Sweden": "+46",
    "Switzerland": "+41",
    "Syria": "+963",
    "Taiwan": "+886",
    "Tajikistan": "+992",
    "Tanzania": "+255",
    "Thailand": "+66",
    "Togo": "+228",
    "Tonga": "+676",
    "Trinidad and Tobago": "+1-868",
    "Tunisia": "+216",
    "Turkey": "+90",
    "Turkmenistan": "+993",
    "Tuvalu": "+688",
    "Uganda": "+256",
    "Ukraine": "+380",
    "United Arab Emirates": "+971",
    "United Kingdom": "+44",
    "United States": "+1",
    "Uruguay": "+598",
    "Uzbekistan": "+998",
    "Vanuatu": "+678",
    "Vatican City": "+379",
    "Venezuela": "+58",
    "Vietnam": "+84",
    "Yemen": "+967",
    "Zambia": "+260",
    "Zimbabwe": "+263",
  }


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)  # using pin as password field
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone_number, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    country_code_choices =  [
        (i[1], f"{i[0]} ({i[1]})") for i in country_phone_codes.items()
    ]

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent/Reseller'),
        ('developer', 'Developer'),
    ]

    first_name=models.CharField(max_length=225, blank=True, null=True)
    last_name=models.CharField(max_length=225, blank=True, null=True)
    middle_name=models.CharField(max_length=225, blank=True, null=True)
    phone_country_code = models.CharField(max_length=10, choices=country_code_choices, default="+234")
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_number_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    closed_reason = models.TextField(blank=True, null=True)

    # ─── User Level / Role ───
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    agent_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text="Default commission rate (%) for agent transactions."
    )
    upgraded_at = models.DateTimeField(null=True, blank=True)
    upgraded_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='upgraded_users'
    )

    # ─── Referral ───
    referral_code = models.CharField(max_length=20, unique=True, blank=True, db_index=True)

    # ─── Transaction PIN (separate from login PIN) ───
    transaction_pin = models.CharField(max_length=128, blank=True, null=True)
    transaction_pin_set = models.BooleanField(default=False)

    # ─── KYC Status (Shortcut) ───
    is_kyc_verified = models.BooleanField(default=False)

    # ─── Two-Factor Authentication ───
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=64, blank=True)

    # ─── FCM Push Notification Token ───
    fcm_token = models.TextField(blank=True, null=True)

    # ─── Social Login ───
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    # ─── Two-Factor Authentication ───
    TWO_FACTOR_METHODS = [
        ('none', 'None'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('all', 'All Channels (SMS, WhatsApp, Email)'),
    ]
    two_factor_method = models.CharField(max_length=20, choices=TWO_FACTOR_METHODS, default='all')
    is_2fa_enabled = models.BooleanField(default=False)

    # ─── Profile Picture ───
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    # ─── Referral Earnings (Simplified from Points) ───
    referral_earnings_count = models.PositiveIntegerField(default=0)
    referral_earnings_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @staticmethod
    def _generate_referral_code():
        """Generate a unique 8-char alphanumeric referral code."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=8))
            if not User.objects.filter(referral_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
            should_validate_email = True

            if self.pk:
                previous_email = (
                    User.objects.filter(pk=self.pk)
                    .values_list("email", flat=True)
                    .first()
                )
                if (previous_email or "").strip().lower() == self.email:
                    should_validate_email = False

            if should_validate_email:
                duplicate_exists = (
                    User.objects.exclude(pk=self.pk)
                    .filter(email__iexact=self.email)
                    .exists()
                )
                if duplicate_exists:
                    raise ValidationError({"email": "A user with this email already exists."})

        if not self.referral_code:
            self.referral_code = self._generate_referral_code()
        super().save(*args, **kwargs)

    def set_transaction_pin(self, raw_pin):
        """Hash and store the transaction PIN."""
        self.transaction_pin = make_password(raw_pin)
        self.transaction_pin_set = True
        self.save(update_fields=['transaction_pin', 'transaction_pin_set'])

    def check_transaction_pin(self, raw_pin):
        """Verify a raw PIN against the stored hash."""
        if not self.transaction_pin:
            return False
        return django_check_password(raw_pin, self.transaction_pin)

    @property
    def full_name(self):
        names = [self.first_name, self.middle_name, self.last_name]
        return " ".join(name for name in names if name).strip()

    def __str__(self):
        if self.is_closed:
            return f"{self.phone_number} (Closed)"
        return self.full_name if self.full_name else self.phone_number

class OTP(models.Model):
    PURPOSE_CHOICES = [
        ("activation", "Account Activation"),
        ("reset", "Password Reset"),
        ("2fa", "Two-Factor Authentication"),
        ("admin_operation", "Admin Sensitive Operation"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    channel = models.CharField(max_length=20, blank=True, null=True)  # Optional: Store the channel used for sending OTP    
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.phone_number} - {self.purpose} OTP"


class Referral(models.Model):
    """Tracks referral relationships between users."""
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referred_by_rel')
    bonus_paid = models.BooleanField(default=False)
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.referrer.phone_number} → {self.referred.phone_number}"


class ReferralConfig(models.Model):
    """Admin-configurable referral commission settings (singleton)."""
    COMMISSION_TYPE_CHOICES = [
        ('percentage', 'Percentage of Sale'),
        ('flat', 'Flat Amount'),
    ]
    COMMISSION_MODE_CHOICES = [
        ('signup', 'One-time on Signup'),
        ('recurring', 'Recurring on Every Purchase'),
    ]

    is_active = models.BooleanField(default=True, help_text="Enable/disable the referral program.")
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES, default='flat')
    commission_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=100.00,
        help_text="If percentage: e.g. 5.00 means 5%. If flat: e.g. 100.00 means ₦100."
    )
    commission_mode = models.CharField(
        max_length=20, choices=COMMISSION_MODE_CHOICES, default='signup',
        help_text="'signup' = bonus when referred user signs up. 'recurring' = bonus on each purchase."
    )
    min_purchase_for_recurring = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Minimum purchase amount to trigger recurring referral bonus."
    )
    max_referral_bonus_per_user = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Max total bonus a referrer can earn from one referred user. 0 = unlimited."
    )

    class Meta:
        verbose_name = "Referral Configuration"
        verbose_name_plural = "Referral Configuration"

    def save(self, *args, **kwargs):
        if not self.pk and ReferralConfig.objects.exists():
            return  # Singleton
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Referral Config ({self.get_commission_type_display()} - {self.get_commission_mode_display()})"


class Beneficiary(models.Model):
    """Saved beneficiaries for quick repeat transactions."""
    SERVICE_TYPES = [
        ('airtime', 'Airtime'),
        ('data', 'Data'),
        ('electricity', 'Electricity'),
        ('tv', 'TV'),
        ('education', 'Education'),
        ('internet', 'Internet'),
        ('transfer', 'Wallet Transfer'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beneficiaries')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    identifier = models.CharField(max_length=50, help_text="Phone, meter number, smartcard, account number, etc.")
    nickname = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text='Extra info, e.g. {"network":"mtn", "bank_code":"044", "bank_name":"Access Bank"}'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'service_type', 'identifier')
        ordering = ['-created_at']

    def __str__(self):
        label = self.nickname or self.identifier
        return f"{self.user.phone_number} - {self.get_service_type_display()}: {label}"

class StaffPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_permissions")
    can_manage_users = models.BooleanField(default=False)
    can_manage_wallets = models.BooleanField(default=False)
    can_manage_vtu = models.BooleanField(default=False)
    can_manage_payments = models.BooleanField(default=False)
    can_manage_notifications = models.BooleanField(default=False)
    can_manage_site_config = models.BooleanField(default=False)
    can_initiate_transfers = models.BooleanField(default=False) # Admin account transfers

    class Meta:
        verbose_name = "Staff Permission"
        verbose_name_plural = "Staff Permissions"

    def __str__(self):
        return f"Permissions for {self.user.phone_number}"

class KYC(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc')
    id_type = models.CharField(max_length=50) # e.g. NIN, BVN, Passport, Driver's License
    id_number = models.CharField(max_length=50) # The specific number on the ID
    id_image = models.ImageField(upload_to='kyc/id/', null=True, blank=True)
    face_image = models.ImageField(upload_to='kyc/face/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remarks = models.TextField(blank=True, null=True) # Rejection reason or approval notes
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_kycs')
    
    time_accepted = models.DateTimeField(null=True, blank=True)
    time_rejected = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"KYC for {self.user.phone_number} ({self.status})"

    class Meta:
        verbose_name_plural = "KYC Records"


class RoleUpgradeConfig(models.Model):
    """
    Singleton model to configure the fees for self-service role upgrades.
    Managed only through the Django Admin.
    """
    customer_to_agent_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Fee charged to upgrade a Customer to Agent."
    )
    customer_to_developer_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Fee charged to upgrade a Customer directly to Developer."
    )
    agent_to_developer_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Fee charged to upgrade an Agent to Developer."
    )
    is_active = models.BooleanField(default=True, help_text="Enable/disable self-service role upgrades.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Role Upgrade Configuration"
        verbose_name_plural = "Role Upgrade Configuration"

    def save(self, *args, **kwargs):
        if not self.pk and RoleUpgradeConfig.objects.exists():
            return  # Singleton
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Role Upgrade Config (Agent: ₦{self.customer_to_agent_fee}, Developer: ₦{self.customer_to_developer_fee})"

    def get_upgrade_fee(self, from_role: str, to_role: str) -> 'Decimal':
        """Returns the required fee for the given role transition."""
        mapping = {
            ('customer', 'agent'): self.customer_to_agent_fee,
            ('customer', 'developer'): self.customer_to_developer_fee,
            ('agent', 'developer'): self.agent_to_developer_fee,
        }
        return mapping.get((from_role, to_role))


class RoleUpgradeLog(models.Model):
    """Immutable audit log for every self-service role upgrade."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_upgrade_logs')
    from_role = models.CharField(max_length=20)
    to_role = models.CharField(max_length=20)
    fee_charged = models.DecimalField(max_digits=10, decimal_places=2)
    upgraded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-upgraded_at']
        verbose_name = "Role Upgrade Log"
        verbose_name_plural = "Role Upgrade Logs"

    def __str__(self):
        return f"{self.user.phone_number}: {self.from_role} → {self.to_role} (₦{self.fee_charged})"
