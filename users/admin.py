from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from users.models import OTP, User, Referral, ReferralConfig, Beneficiary, RoleUpgradeConfig, RoleUpgradeLog
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from rest_framework.authtoken.models import Token

# update labels for dashboard
admin.site.site_title = "Starboy Global Admin Dashboard"
admin.site.site_header = "Starboy Global Admin"
admin.site.index_title = "Dashboard"


# Unregister Token if already registered
try:
    admin.site.unregister(Token)
except admin.sites.NotRegistered:
    pass

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "middle_name",
            "phone_country_code",
            "phone_number",
            "email",
            )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        # remove the first 0 in the users phone number
        phone = user.phone_number
        if phone.startswith("0"):
            user.phone_number = phone[1:]
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "middle_name",
            "phone_country_code",
            "phone_number",
            "email",
            "is_active",
            "is_staff",
            "is_closed",
            "closed_at",
            "closed_reason",
            'password',
            'role',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        phone = user.phone_number
        if phone.startswith("0"):
            user.phone_number = phone[1:]
        if commit:
            user.save()
        return user


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = [
        "full_name_and_phone",
        "email",
        "wallet_balance",
        "user_role",
        "account_verification_status",
        "active_status",
        "staff_status",
        "created_at",
    ]
    readonly_fields = [
        "created_at",
        "referral_code",
        "transaction_pin_set",
    ]
    actions = ["create_virtual_account", "deactivate_user", "activate_user", "set_as_verified", "upgrade_to_agent", "downgrade_to_customer"]



    def wallet_balance(self, obj):
        from wallet.models import Wallet
        wallet = Wallet.objects.filter(user=obj).first()
        if wallet:
            return f"₦{wallet.balance:,.2f}"
        return "₦0.00"
    wallet_balance.short_description = "Wallet Balance"

    def full_name_and_phone(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<div style="font-weight: bold; color: var(--body-quiet-color);">{}</div>'
            '<div style="font-size: 0.9em; color: var(--body-loud-color);">{}</div>',
            f"{obj.first_name or ''} {obj.last_name or ''}".strip() or "No Name",
            obj.phone_number
        )
    full_name_and_phone.short_description = "User Details"

    def user_role(self, obj):
        from django.utils.html import format_html
        colors = {'customer': '#6b7280', 'agent': '#2563eb', 'staff': '#7c3aed'}
        color = colors.get(obj.role, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: 600; text-transform: capitalize;">{}</span>',
            color, obj.get_role_display()
        )
    user_role.short_description = "Role"

    def active_status(self, obj):
        from django.utils.html import format_html
        color = "#16a34a" if obj.is_active else "#dc2626"
        status ="Closed" if obj.is_closed else "Active" if obj.is_active else "Inactive"
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            color, status
        )
    active_status.short_description = "Status"

    def staff_status(self, obj):
        status = "Admin" if obj.is_staff else "Customer"
        return status
    staff_status.short_description = "Role"


    def account_verification_status(self, obj):
        from django.utils.html import format_html
        methods = []
        if obj.email_verified:
            methods.append("Email")
        if obj.phone_number_verified:
            methods.append("Phone")

        if not methods:
            return format_html('<span style="color: #dc2626;">Not Verified</span>')

        return format_html(
            '<span style="color: #2563eb; font-weight: 500;">{} Verified</span>',
            " & ".join(methods)
        )
    account_verification_status.short_description = "Verification"

    @admin.display(description="Deactivate User")
    def deactivate_user(self, request, queryset):
        for obj in queryset:
            obj.is_active = False
            obj.save()
        self.message_user(request, "Users deactivated successfully")

    @admin.display(description="Activate User")
    def activate_user(self, request, queryset):
        for obj in queryset:
            obj.is_active = True
            obj.save()
        self.message_user(request, "Users activated successfully")

    @admin.display(description="Set as Verified")
    def set_as_verified(self, request, queryset):
        for obj in queryset:
            obj.is_verified = True
            obj.save()
        self.message_user(request, "Users verified successfully")

    @admin.action(description="Upgrade to Agent")
    def upgrade_to_agent(self, request, queryset):
        from django.utils import timezone
        for obj in queryset:
            obj.role = 'agent'
            obj.upgraded_at = timezone.now()
            obj.upgraded_by = request.user
            obj.save()
        self.message_user(request, f"{queryset.count()} user(s) upgraded to Agent.")

    @admin.action(description="Downgrade to Customer")
    def downgrade_to_customer(self, request, queryset):
        for obj in queryset:
            obj.role = 'customer'
            obj.save()
        self.message_user(request, f"{queryset.count()} user(s) downgraded to Customer.")

    @admin.action(description="Create virtual account")
    def create_virtual_account(self, request, queryset):
        from wallet.models import VirtualAccount
        from payments.utils import PaystackGateway
        from django.conf import settings
        import logging

        success_count = 0
        failed_count = 0

        logger = logging.getLogger(__name__)

        for obj in queryset:
            is_complete = all([obj.first_name, obj.last_name, obj.email])
            has_account = VirtualAccount.objects.filter(user=obj).exists()

            if is_complete and not has_account:
                try:
                    client = PaystackGateway(settings.PAYSTACK_SECRET_KEY)
                    phone = f"{obj.phone_country_code}{obj.phone_number}" if obj.phone_number else ""

                    client.create_virtual_account(
                        email=obj.email,
                        first_name=obj.first_name,
                        middle_name=obj.middle_name or "",
                        last_name=obj.last_name,
                        phone=phone,
                    )
                    success_count += 1
                except Exception as e:
                    error_msg = f"Error creating virtual account for {obj.email}: {str(e)}"
                    logger.error(error_msg)
                    print(error_msg)
                    self.message_user(request, error_msg, level='error')
                    failed_count += 1
            else:
                reason = ""
                if not is_complete:
                    reason = "Profile incomplete (missing name or email)"
                elif has_account:
                    reason = "Already has a virtual account"

                error_msg = f"Skipped {obj.email or obj.phone_number}: {reason}"
                logger.error(error_msg)
                print(error_msg)
                self.message_user(request, error_msg, level='warning')
                failed_count += 1

        if success_count > 0:
            self.message_user(request, f"Successfully triggered virtual account creation for {success_count} users.")

    ordering = ['-created_at']
    list_filter = ('is_active', 'is_staff', 'role')
    search_fields = ('first_name', 'last_name', 'email', "phone_number", "referral_code")
    filter_horizontal = ('groups', 'user_permissions',)
    fieldsets = (
        ('Authentication', {'fields': ('phone_country_code', 'phone_number', 'password')}),
        ("Personal Information", {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'middle_name', 'email'),
        }),
        ("Verification Status", {"fields": ("is_verified", "email_verified", "phone_number_verified")}),
        ("Role & Referral", {
            "fields": ("role", "agent_commission_rate", "referral_code"),
            "description": "User role and referral settings."
        }),
        ("Transaction Security", {
            "fields": ("transaction_pin_set", "two_factor_enabled"),
        }),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('created_at', )}),
        ('Account Status', {
            'fields': (
                'is_closed',
                'closed_at',
                'closed_reason',
            ),
        }),
    )
    add_fieldsets = (
        ('Authentication', {'fields': ('phone_country_code', 'phone_number', 'password1', 'password2')}),
        ("Personal Information", {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'middle_name', 'email', ),
        }),
        ("Role", {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions')}),
        ('Account Status', {
            'fields': (
                'is_closed',
                'closed_at',
                'closed_reason',
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.first_name and obj.last_name and obj.email:
            from wallet.models import VirtualAccount
            if not VirtualAccount.objects.filter(user=obj).exists():
                try:
                    from payments.utils import PaystackGateway
                    from django.conf import settings
                    client = PaystackGateway(settings.PAYSTACK_SECRET_KEY)

                    phone = f"{obj.phone_country_code}{obj.phone_number}" if obj.phone_number else ""

                    client.create_virtual_account(
                        email=obj.email,
                        first_name=obj.first_name,
                        middle_name=obj.middle_name or "",
                        last_name=obj.last_name,
                        phone=phone,
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create virtual account in admin: {e}")


from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    filter_horizontal = ('permissions',)

admin.site.register(User, UserAdmin)


# ─── Referral Admin ───

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred', 'bonus_paid', 'bonus_amount', 'created_at')
    list_filter = ('bonus_paid', 'created_at')
    search_fields = ('referrer__phone_number', 'referred__phone_number')
    readonly_fields = ('referrer', 'referred', 'bonus_paid', 'bonus_amount', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(ReferralConfig)
class ReferralConfigAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'commission_type', 'commission_value', 'commission_mode')
    fieldsets = (
        ("Referral Program Status", {
            "fields": ("is_active",),
        }),
        ("Commission Settings", {
            "fields": ("commission_type", "commission_value", "commission_mode"),
            "description": "Configure how referral bonuses are calculated and when they are paid."
        }),
        ("Advanced", {
            "fields": ("min_purchase_for_recurring", "max_referral_bonus_per_user"),
            "classes": ("collapse",),
        }),
    )

    def has_add_permission(self, request):
        if ReferralConfig.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False


# ─── Beneficiary Admin ───

@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'service_type', 'identifier', 'nickname', 'created_at')
    list_filter = ('service_type', 'created_at')
    search_fields = ('user__phone_number', 'identifier', 'nickname')
    readonly_fields = ('created_at',)


# ─── Role Upgrade Config ───

@admin.register(RoleUpgradeConfig)
class RoleUpgradeConfigAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'customer_to_agent_fee', 'customer_to_developer_fee', 'agent_to_developer_fee', 'updated_at')
    fieldsets = (
        ("Program Status", {
            "fields": ("is_active",),
        }),
        ("Upgrade Fees", {
            "fields": ("customer_to_agent_fee", "customer_to_developer_fee", "agent_to_developer_fee"),
            "description": "Set ₦0.00 for a free upgrade. These fees are charged from the user's wallet."
        }),
    )

    def has_add_permission(self, request):
        if RoleUpgradeConfig.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RoleUpgradeLog)
class RoleUpgradeLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_role', 'to_role', 'fee_charged', 'upgraded_at')
    list_filter = ('from_role', 'to_role', 'upgraded_at')
    search_fields = ('user__phone_number', 'user__email')
    readonly_fields = ('user', 'from_role', 'to_role', 'fee_charged', 'upgraded_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False