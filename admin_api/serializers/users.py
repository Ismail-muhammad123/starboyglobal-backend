from rest_framework import serializers
from users.models import User, StaffPermission, KYC
from django.db.models import Sum
from drf_spectacular.utils import extend_schema_field

class StaffPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffPermission
        fields = '__all__'

class KYCSerializer(serializers.ModelSerializer):
    processed_by_name = serializers.CharField(source='processed_by.phone_number', read_only=True)
    class Meta:
        model = KYC
        fields = '__all__'

class AdminUserListSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.DecimalField(source='wallet.balance', max_digits=12, decimal_places=2, read_only=True, default=0)
    total_credits = serializers.SerializerMethodField()
    total_debits = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id","phone_country_code", "phone_number", "first_name", "last_name", "email", "profile_image", "role", "is_active", 
            "is_verified", "is_kyc_verified", "is_staff", "is_admin", "is_closed", "referral_code", 
            "wallet_balance", "total_credits", "total_debits", "created_at"
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_credits(self, obj):
        return obj.wallet_transactions.filter(transaction_type='credit', status='success').aggregate(total=Sum('amount'))['total'] or 0

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_debits(self, obj):
        return obj.wallet_transactions.filter(transaction_type='debit', status='success').aggregate(total=Sum('amount'))['total'] or 0

class AdminUserDetailSerializer(serializers.ModelSerializer):
    staff_permissions = StaffPermissionSerializer(required=False, read_only=True)
    wallet_balance = serializers.DecimalField(source='wallet.balance', max_digits=12, decimal_places=2, read_only=True, default=0)
    kyc = KYCSerializer(read_only=True)
    virtual_account = serializers.SerializerMethodField()
    beneficiaries = serializers.SerializerMethodField()
    purchase_beneficiaries = serializers.SerializerMethodField()
    transfer_beneficiaries = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    recent_purchases = serializers.SerializerMethodField()
    total_credits = serializers.SerializerMethodField()
    total_debits = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    all_permissions = serializers.SerializerMethodField()
    developer_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "phone_number", "first_name", "last_name", "middle_name", "email", 
            "phone_country_code", "role", "agent_commission_rate", "is_active", "is_verified", 
            "is_kyc_verified", "is_staff", "is_admin", "is_superuser", "is_closed", "closed_at", 
            "closed_reason", "referral_code", "referral_earnings_count", "referral_earnings_amount", 
            "transaction_pin_set", "two_factor_enabled", "profile_image", "wallet_balance", 
            "kyc", "staff_permissions", "virtual_account", "beneficiaries", "purchase_beneficiaries", 
            "transfer_beneficiaries", "recent_transactions", "recent_purchases", "total_credits", 
            "total_debits", "groups", "all_permissions", "created_at", "upgraded_at", "developer_profile"
        ]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_virtual_account(self, obj):
        try:
            return {
                "account_number": obj.virtual_account.account_number, 
                "bank_name": obj.virtual_account.bank_name, 
                "account_name": obj.virtual_account.account_name
            }
        except:
            return None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_beneficiaries(self, obj):
        return list(obj.beneficiaries.values("id", "service_type", "identifier", "nickname")[:20])

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_purchase_beneficiaries(self, obj):
        return list(obj.purchase_beneficiaries.values("id", "service_type", "identifier", "nickname")[:20])

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_transfer_beneficiaries(self, obj):
        return list(obj.transfer_beneficiaries.values("id", "bank_name", "account_number", "account_name", "nickname")[:20])

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_recent_transactions(self, obj):
        return [
            {
                "id": t.id, "type": t.transaction_type, "amount": float(t.amount), 
                "balance_after": float(t.balance_after), "description": t.description, 
                "reference": t.reference, "timestamp": t.timestamp.isoformat()
            } for t in obj.wallet_transactions.order_by('-timestamp')[:15]
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_recent_purchases(self, obj):
        return [
            {
                "id": p.id, "type": p.purchase_type, "amount": float(p.amount), 
                "beneficiary": p.beneficiary, "status": p.status, "reference": p.reference, 
                "time": p.time.isoformat()
            } for p in obj.purchases.order_by('-time')[:15]
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_credits(self, obj):
        return obj.wallet_transactions.filter(transaction_type='credit', status='success').aggregate(total=Sum('amount'))['total'] or 0

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_debits(self, obj):
        return obj.wallet_transactions.filter(transaction_type='debit', status='success').aggregate(total=Sum('amount'))['total'] or 0

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_groups(self, obj):
        return list(obj.groups.values('id', 'name'))

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_all_permissions(self, obj):
        return sorted(list(obj.get_all_permissions()))

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_developer_profile(self, obj):
        if obj.role == 'developer' and hasattr(obj, 'developer_profile'):
            from developer_api.views.auth import DeveloperProfileSerializer, APIKeySerializer
            profile = obj.developer_profile
            profile_data = DeveloperProfileSerializer(profile).data
            api_keys = profile.api_keys.all()
            profile_data['api_keys'] = APIKeySerializer(api_keys, many=True).data
            return profile_data
        return None

class AdminCreateUserRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField()
    role = serializers.ChoiceField(choices=['customer', 'agent', 'developer'], default='customer')
    is_active = serializers.BooleanField(default=True)
    is_staff = serializers.BooleanField(default=False)
    is_admin = serializers.BooleanField(default=False)

class AdminSetRoleRequestSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['customer', 'agent', 'developer'])
    commission_rate = serializers.FloatField(required=False, default=0.0)
    is_staff = serializers.BooleanField(required=False, default=None, allow_null=True)
    is_admin = serializers.BooleanField(required=False, default=None, allow_null=True)

class AdminSetPermissionsRequestSerializer(serializers.Serializer):
    can_manage_users = serializers.BooleanField(default=False)
    can_manage_wallets = serializers.BooleanField(default=False)
    can_manage_vtu = serializers.BooleanField(default=False)
    can_manage_payments = serializers.BooleanField(default=False)
    can_manage_notifications = serializers.BooleanField(default=False)
    can_manage_site_config = serializers.BooleanField(default=False)
    can_initiate_transfers = serializers.BooleanField(default=False)

class AdminResetPinRequestSerializer(serializers.Serializer):
    new_pin = serializers.CharField(min_length=4, max_length=6)
