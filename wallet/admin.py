from wallet.utils import debit_wallet, fund_wallet

from .models import WalletTransaction, Wallet, VirtualAccount
from django.contrib import messages, admin
from django.utils import timezone
from django import forms
from decimal import Decimal
import uuid
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.html import format_html

User = get_user_model()



@admin.register(VirtualAccount)
class VirtualAccountAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "account_number",
        "bank_name",
        "status",
        "created_at",
    )
    list_filter = ("bank_name", "status", "created_at")
    search_fields = ("user__email", "user__phone_number", "account_number")
    readonly_fields = ("created_at",)

    def has_change_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False

    def deactivate_accounts(modeladmin, request, queryset):
        updated = queryset.update(status="INACTIVE")
        messages.success(request, f"{updated} account(s) deactivated successfully.")
    deactivate_accounts.short_description = "Deactivate selected virtual accounts"

    actions = [deactivate_accounts]


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user','balance','updated_at','created_at')
    sortable_by = ('balance', 'updated_at', 'created_at')
    readonly_fields = ('user', 'balance', 'updated_at', 'created_at')
    search_fields = ('user__email', 'user__phone_number')

    # inlines = [WalletTransactionInline]



# -------------------------------
# Admin Form (customized form logic)
# -------------------------------
class WalletTransactionAdminForm(forms.ModelForm):
    # Add custom field for user phone number
    user_phone = forms.CharField(
        label="User Phone Number",
        help_text="Enter the user's phone number (username).",
    )

    class Meta:
        model = WalletTransaction
        fields = ["user_phone", "transaction_type", "amount", "description"]

    def clean_user_phone(self):
        phone = self.cleaned_data["user_phone"]
        if str(phone).startswith("0"):
            phone = phone[1:]
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            raise forms.ValidationError(f"No user found with phone number {phone}")
        self.cleaned_data["user"] = user
        return phone

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        if user:
            wallet = Wallet.objects.filter(user=user).first()
            if not wallet:
                raise forms.ValidationError("This user does not have a wallet.")
            cleaned_data["wallet"] = wallet
        return cleaned_data


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    form = WalletTransactionAdminForm

    list_display = (
        "user",
        "wallet",
        "transaction_type",
        "transaction_initiator",
        "transaction_amount",
        "reference",
        "timestamp",
    )

    readonly_fields = (
        "wallet",
        "balance_before",
        "balance_after",
        "reference",
        "timestamp",
        "initiator",
        "initiated_by",
    )


    def transaction_amount(self, obj):
        amount = "{:,.2f}".format(obj.amount)

        if obj.transaction_type.lower() in ["credit", "deposit", "reversal"]:
            return format_html("<span style='color:green;'>+ {}</span>", amount)

        elif obj.transaction_type.lower() in ["debit", "withdrawal", "purchase"]:
            return format_html("<span style='color:red;'>- {}</span>", amount)

        return amount
     
    def transaction_initiator(self, obj):
        if obj.initiator == "self":
            return "Self Initiated"
        elif obj.initiator == "admin":
            return f"Admin: {obj.initiated_by}"
        return obj.initiator



        

    search_fields = ("user__username", "reference")
    list_filter = ("transaction_type", "initiator")

    def has_change_permission(self, request, obj = ...):
        return False
    
    def has_delete_permission(self, request, obj = ...):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        obj.user = form.cleaned_data["user"]
        obj.wallet = form.cleaned_data["wallet"]
        obj.initiated_by = request.user
        obj.initiator = "admin"
        obj.reference = f"ADM-{uuid.uuid4().hex[:10].upper()}"
        obj.timestamp = timezone.now()

        try:
            wallet = obj.wallet
            if not wallet:
                raise ValueError("Wallet not found")

            obj.balance_before = wallet.balance

            if obj.transaction_type.lower() in ['deposit', 'reversal', 'credit']:
                fund_wallet(obj.user, obj.amount, reference=obj.reference, description=obj.description)
                obj.balance_after = float(wallet.balance) + float(obj.amount)
                # wallet.balance += obj.amount
            elif obj.transaction_type.lower() in ['withdrawal', 'purchase', 'debit']:
                if wallet.balance < obj.amount:
                    raise ValueError("Insufficient funds")
                debit_wallet(obj.user, obj.amount, reference=obj.reference, description=obj.description)
                obj.balance_after = float(wallet.balance) - float(obj.amount)

            # Save both atomically
            with transaction.atomic():
                # wallet.save(update_fields=["balance"])
                obj.save()
                messages.success(request, f"✅ Transaction applied and wallet updated for {obj.user} - {obj.user.phone_number}.")
        except Exception as e:
            messages.error(request, f"❌ Transaction failed: {e}")


from .models import TransactionCharge

@admin.register(TransactionCharge)
class TransactionChargeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'transaction_type',
        'charge_type',
        'amount',
        'cap',
        'min_transaction_amount',
        'max_transaction_amount',
        'block_if_insufficient',
        'is_active',
        'created_at'
    )
    list_filter = ('transaction_type', 'charge_type', 'is_active', 'block_if_insufficient')
    search_fields = ('name',)
    ordering = ('transaction_type', '-created_at')

