from django.db import models
from wallet.models import Wallet
from django.contrib.auth import get_user_model


User = get_user_model()

STATUS_OPTIONS = [
    ("PENDING", "Pending"),
    ("SUCCESS", "Success"),
    ("FAILED", "Failed"),
]

PAYMENT_TYPES = [
    ("DEBIT", "Debit"),
    ("CREDIT", "Credit"),
]

APPROVAL_STATUS_OPTIONS = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
]

class Deposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deposits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_OPTIONS, default="PENDING")
    timestamp = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, unique=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default="CREDIT")
    recieved = models.BooleanField(default=False)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_deposits')
    remarks = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Deposit {self.amount} from {self.user}"

class Withdrawal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=APPROVAL_STATUS_OPTIONS, default="PENDING")
    transaction_status = models.CharField(max_length=10, choices=STATUS_OPTIONS, default="PENDING")
    reference = models.CharField(max_length=100, unique=True)
    transfer_code = models.CharField(max_length=100, null=True, blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_withdrawals')
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("approve_withdrawal", "Can accept or reject user withdrawal requests"),
        ]

    def __str__(self):
        return f"Withdrawal {self.amount} by {self.user.full_name}"




class PaystackConfig(models.Model):
    is_active = models.BooleanField(default=False)
    public_key = models.CharField(max_length=255, blank=True, null=True)
    secret_key = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paystack Configuration"
        verbose_name_plural = "Paystack Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Paystack Config"

    @property
    def webhook_url(self):
        from django.conf import settings
        domain = getattr(settings, 'SITE_DOMAIN', 'https://yourdomain.com')
        return f"{domain}/payments/webhook/paystack/"

    @property
    def callback_url(self):
        from django.conf import settings
        domain = getattr(settings, 'SITE_DOMAIN', 'https://yourdomain.com')
        return f"{domain}/payments/callback/paystack/"

class AdminTransferBeneficiary(models.Model):
    name = models.CharField(max_length=200)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10)
    account_number = models.CharField(max_length=20)
    recipient_code = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Admin Transfer Beneficiary"
        verbose_name_plural = "Admin Transfer Beneficiaries"

    def __str__(self):
        return f"{self.name} ({self.bank_name})"

class AdminTransfer(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    beneficiary = models.ForeignKey(AdminTransferBeneficiary, on_delete=models.CASCADE, related_name='transfers')
    status = models.CharField(max_length=10, choices=STATUS_OPTIONS, default="PENDING")
    reference = models.CharField(max_length=100, unique=True)
    transfer_code = models.CharField(max_length=100, null=True, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='initiated_admin_transfers')
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("initiate_admin_transfer", "Can initiate administrative bank transfers"),
        ]

    def __str__(self):
        return f"Admin Transfer {self.amount} to {self.beneficiary.name}"
