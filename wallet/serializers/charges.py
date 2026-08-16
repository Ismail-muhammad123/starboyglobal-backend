from decimal import Decimal
from rest_framework import serializers
from wallet.models import TransactionCharge


class TransactionChargeItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Charge rule ID")
    name = serializers.CharField(help_text="Name or description of the charge")
    charge_type = serializers.ChoiceField(
        choices=TransactionCharge.CHARGE_TYPES,
        help_text="Charge calculation type: 'flat' or 'percentage'"
    )
    rate_or_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Configured flat fee or percentage rate"
    )
    cap = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        allow_null=True,
        required=False,
        help_text="Maximum fee cap when percentage type is used (null if no cap)"
    )
    computed_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Calculated charge amount in Naira"
    )
    block_if_insufficient = serializers.BooleanField(
        help_text="Whether transaction is blocked if wallet balance cannot cover this charge"
    )


class TransactionChargeListRequestSerializer(serializers.Serializer):
    transaction_type = serializers.ChoiceField(
        choices=TransactionCharge.TRANSACTION_TYPES,
        help_text="Transaction type ('deposit', 'transfer_others', or 'transfer_p2p')"
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text="Transaction amount in Naira"
    )


class TransactionChargeListResponseSerializer(serializers.Serializer):
    transaction_type = serializers.CharField(help_text="Transaction type evaluated")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Transaction amount")
    charges = TransactionChargeItemSerializer(many=True, help_text="List of applicable charges and breakdown")
    total_charge = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Total calculated charges")
    total_required = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Total required amount (amount + total_charge)")
