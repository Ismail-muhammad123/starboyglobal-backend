from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
User = get_user_model()


class VirtualAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="virtual_account")
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200)
    account_reference = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_name = models.CharField(max_length=200)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.account_number}"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("adjust_wallet", "Can adjust user wallet balance manually"),
        ]

    def __str__(self):
        return f"{self.user.full_name}'s wallet"



class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'debit'),
    ]

    INITIATOR_CHOICES = [
        ("self", "Self"),
        ("admin", "Admin"),
    ]
    
    STATUS_CHOICES = [
        ("success", "Success"),
        ("pending", "Pending"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, null=True, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    deposit =models.OneToOneField("payments.Deposit", null=True, on_delete=models.SET_NULL, related_name="wallet_transaction")
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    initiator = models.CharField(max_length=6, choices=INITIATOR_CHOICES, default="self")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    initiated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="initiated_transactions")
    reference = models.CharField(max_length=100, unique=True)
    
    sender_account_name = models.CharField(max_length=200, blank=True, null=True)
    sender_account_number = models.CharField(max_length=20, blank=True, null=True)
    sender_bank_name = models.CharField(max_length=100, blank=True, null=True)
    
    receiver_account_name = models.CharField(max_length=200, blank=True, null=True)
    receiver_account_number = models.CharField(max_length=20, blank=True, null=True)
    receiver_bank_name = models.CharField(max_length=100, blank=True, null=True)

    timestamp = models.DateTimeField(default=timezone.now)
    charge_for = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='charge_transactions')
    is_charge = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        permissions = [
            ("adjust_wallet", "Can adjust user wallet balance manually"),
        ]

    def __str__(self):
        return f"{self.transaction_type} of {self.amount} on {self.timestamp.date()} for {self.user.email}"




class TransferBeneficiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfer_beneficiaries")
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=200)
    nickname = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transfer Beneficiary"
        verbose_name_plural = "Transfer Beneficiaries"
        unique_together = ('user', 'bank_code', 'account_number')

    def __str__(self):
        return f"{self.nickname or self.account_name} ({self.bank_name})"

class BonusConfig(models.Model):
    service_type = models.CharField(max_length=50, unique=True, help_text="e.g. referral_deposit, referral_purchase")
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.service_type


class TransactionCharge(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('transfer_others', 'Transfer (Others)'),
        ('transfer_p2p', 'Transfer (P2P)'),
    ]

    CHARGE_TYPES = [
        ('flat', 'Flat'),
        ('percentage', 'Percentage'),
    ]

    name = models.CharField(max_length=255, help_text="Label for the charge rule, e.g. Deposit processing fee")
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES, db_index=True)
    charge_type = models.CharField(max_length=20, choices=CHARGE_TYPES, default='flat')
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Flat fee amount or percentage rate (0-100)")
    cap = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Maximum fee cap when percentage type is used (null means no cap)")
    min_transaction_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Minimum transaction amount to apply this charge")
    max_transaction_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Maximum transaction amount to apply this charge (null means no upper limit)")
    block_if_insufficient = models.BooleanField(default=False, help_text="Prevent transaction if wallet balance is insufficient for amount + charge. If False, charge is skipped if balance is insufficient.")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['transaction_type', '-created_at']
        verbose_name = "Transaction Charge"
        verbose_name_plural = "Transaction Charges"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.charge_type == 'flat':
            self.cap = None
        elif self.charge_type == 'percentage':
            if self.amount < 0 or self.amount > 100:
                raise ValidationError({"amount": "Percentage value must be between 0 and 100."})
        if self.min_transaction_amount < 0:
            raise ValidationError({"min_transaction_amount": "Minimum amount cannot be negative."})
        if self.max_transaction_amount is not None:
            if self.max_transaction_amount < self.min_transaction_amount:
                raise ValidationError({"max_transaction_amount": "Maximum transaction amount must be greater than or equal to minimum transaction amount."})

    def save(self, *args, **kwargs):
        if self.charge_type == 'flat':
            self.cap = None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_transaction_type_display()} - {self.get_charge_type_display()} {self.amount})"

