from rest_framework import serializers
from wallet.models import WalletTransaction

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'amount', 'transaction_type', 'description', 'timestamp', 'initiator',
            'sender_account_name', 'sender_account_number', 'sender_bank_name',
            'receiver_account_name', 'receiver_account_number', 'receiver_bank_name'
        ]
