from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

from wallet.serializers import (
    TransactionChargeListRequestSerializer,
    TransactionChargeListResponseSerializer,
    ErrorResponseSerializer
)
from wallet.utils import calculate_total_charges


class TransactionChargesView(APIView):
    """
    Get applicable charges and total fees for a given transaction type and amount.
    Supports both GET (with query parameters) and POST (with request body).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Wallet"],
        summary="Get transaction charges",
        description="Retrieve and calculate all applicable charges and breakdown for a given amount and transaction type (`deposit`, `transfer_others`, or `transfer_p2p`).",
        parameters=[
            OpenApiParameter(
                name='transaction_type',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Type of transaction: `deposit`, `transfer_others`, or `transfer_p2p`",
                enum=['deposit', 'transfer_others', 'transfer_p2p'],
                examples=[
                    OpenApiExample('P2P Transfer', value='transfer_p2p'),
                    OpenApiExample('Bank Withdrawal', value='transfer_others'),
                    OpenApiExample('Wallet Deposit', value='deposit'),
                ]
            ),
            OpenApiParameter(
                name='amount',
                type=float,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Transaction amount in Naira",
                examples=[
                    OpenApiExample('Example Amount', value=5000.00),
                ]
            ),
        ],
        responses={
            200: TransactionChargeListResponseSerializer,
            400: ErrorResponseSerializer
        },
        examples=[
            OpenApiExample(
                'P2P Charges Response Example',
                description='Calculated charges breakdown for a ₦5,000 P2P transfer',
                value={
                    "transaction_type": "transfer_p2p",
                    "amount": "5000.00",
                    "charges": [
                        {
                            "id": 1,
                            "name": "P2P Transfer Fee",
                            "charge_type": "flat",
                            "rate_or_amount": "25.00",
                            "cap": None,
                            "computed_amount": "25.00",
                            "block_if_insufficient": True
                        }
                    ],
                    "total_charge": "25.00",
                    "total_required": "5025.00"
                },
                response_only=True,
                status_codes=["200"]
            ),
            OpenApiExample(
                'Deposit Percentage Charge Response Example',
                description='Calculated charges breakdown for a ₦10,000 deposit with 1.5% fee capped at ₦200',
                value={
                    "transaction_type": "deposit",
                    "amount": "10000.00",
                    "charges": [
                        {
                            "id": 2,
                            "name": "Deposit Processing Fee",
                            "charge_type": "percentage",
                            "rate_or_amount": "1.50",
                            "cap": "200.00",
                            "computed_amount": "150.00",
                            "block_if_insufficient": False
                        }
                    ],
                    "total_charge": "150.00",
                    "total_required": "10150.00"
                },
                response_only=True,
                status_codes=["200"]
            )
        ]
    )
    def get(self, request):
        serializer = TransactionChargeListRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return self._process_charges(serializer.validated_data)

    @extend_schema(
        tags=["Wallet"],
        summary="Calculate transaction charges",
        description="Calculate and preview applicable charges for a given transaction type and amount via POST payload.",
        request=TransactionChargeListRequestSerializer,
        responses={
            200: TransactionChargeListResponseSerializer,
            400: ErrorResponseSerializer
        },
        examples=[
            OpenApiExample(
                'Calculate Charges Request Example',
                description='Request payload to calculate charges for a transfer or deposit',
                value={
                    "transaction_type": "transfer_p2p",
                    "amount": 5000.00
                },
                request_only=True
            ),
            OpenApiExample(
                'Calculate Charges Response Example',
                description='Calculated charges breakdown response',
                value={
                    "transaction_type": "transfer_p2p",
                    "amount": "5000.00",
                    "charges": [
                        {
                            "id": 1,
                            "name": "P2P Transfer Fee",
                            "charge_type": "flat",
                            "rate_or_amount": "25.00",
                            "cap": None,
                            "computed_amount": "25.00",
                            "block_if_insufficient": True
                        }
                    ],
                    "total_charge": "25.00",
                    "total_required": "5025.00"
                },
                response_only=True,
                status_codes=["200"]
            )
        ]
    )
    def post(self, request):
        serializer = TransactionChargeListRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._process_charges(serializer.validated_data)

    def _process_charges(self, validated_data):
        txn_type = validated_data['transaction_type']
        amount = validated_data['amount']

        total_charge, breakdown = calculate_total_charges(txn_type, amount)
        total_required = amount + total_charge

        response_data = {
            "transaction_type": txn_type,
            "amount": f"{amount:.2f}",
            "charges": breakdown,
            "total_charge": f"{total_charge:.2f}",
            "total_required": f"{total_required:.2f}"
        }
        return Response(response_data, status=status.HTTP_200_OK)
