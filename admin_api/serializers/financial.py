from rest_framework import serializers
from admin_api.models import AdminBeneficiary, AdminTransferLog
from payments.models import PaystackConfig, Deposit, Withdrawal, AdminTransfer, AdminTransferBeneficiary
from orders.models import Purchase
from wallet.models import WalletTransaction

class AdminBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminBeneficiary
        fields = '__all__'

class AdminTransferLogSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source='beneficiary.name', read_only=True)
    class Meta:
        model = AdminTransferLog
        fields = '__all__'

class AdminPaystackConfigSerializer(serializers.ModelSerializer):
    webhook_url = serializers.ReadOnlyField()
    callback_url = serializers.ReadOnlyField()
    class Meta:
        model = PaystackConfig
        fields = ["id", "is_active", "public_key", "secret_key", "webhook_url", "callback_url"]

class AdminPurchaseSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    class Meta:
        model = Purchase
        fields = '__all__'

class AdminDepositSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.phone_number', read_only=True)
    class Meta:
        model = Deposit
        fields = '__all__'

class AdminWithdrawalSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.phone_number', read_only=True)
    class Meta:
        model = Withdrawal
        fields = '__all__'

class AdminWalletTransactionSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    class Meta:
        model = WalletTransaction
        fields = '__all__'

class AdminTransferBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminTransferBeneficiary
        fields = '__all__'

class AdminTransferSerializer(serializers.ModelSerializer):
    beneficiary_details = AdminTransferBeneficiarySerializer(source='beneficiary', read_only=True)
    initiated_by_name = serializers.CharField(source='initiated_by.phone_number', read_only=True)
    class Meta:
        model = AdminTransfer
        fields = '__all__'

class AdminManualAdjustmentRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(required=False, default="Admin Adjustment")
    pin = serializers.CharField()
    type = serializers.ChoiceField(choices=['credit', 'debit'])

class AdminInitiateTransferRequestSerializer(serializers.Serializer):
    beneficiary_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pin = serializers.CharField()

from wallet.models import TransactionCharge

class TransactionChargeSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    charge_type_display = serializers.CharField(source='get_charge_type_display', read_only=True)

    class Meta:
        model = TransactionCharge
        fields = [
            'id',
            'name',
            'transaction_type',
            'transaction_type_display',
            'charge_type',
            'charge_type_display',
            'amount',
            'cap',
            'min_transaction_amount',
            'max_transaction_amount',
            'block_if_insufficient',
            'is_active',
            'created_at',
            'updated_at'
        ]

    def validate(self, data):
        charge_type = data.get('charge_type', getattr(self.instance, 'charge_type', 'flat'))
        amount = data.get('amount', getattr(self.instance, 'amount', None))
        min_amt = data.get('min_transaction_amount', getattr(self.instance, 'min_transaction_amount', 0))
        max_amt = data.get('max_transaction_amount', getattr(self.instance, 'max_transaction_amount', None))

        if charge_type == 'flat':
            data['cap'] = None
        elif charge_type == 'percentage':
            if amount is not None and (amount < 0 or amount > 100):
                raise serializers.ValidationError({"amount": "Percentage value must be between 0 and 100."})

        if min_amt is not None and min_amt < 0:
            raise serializers.ValidationError({"min_transaction_amount": "Minimum amount cannot be negative."})

        if max_amt is not None and min_amt is not None and max_amt < min_amt:
            raise serializers.ValidationError({"max_transaction_amount": "Maximum amount must be greater than or equal to minimum amount."})

        return data


class TransactionChargeCalculateRequestSerializer(serializers.Serializer):
    transaction_type = serializers.ChoiceField(choices=TransactionCharge.TRANSACTION_TYPES)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class TransactionChargeCalculateResponseSerializer(serializers.Serializer):
    transaction_type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    charges = serializers.ListField(child=serializers.DictField())
    total_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)

