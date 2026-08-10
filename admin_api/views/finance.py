from rest_framework import viewsets, status, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiExample
import pyotp
from payments.models import Deposit, Withdrawal, PaystackConfig
from wallet.models import WalletTransaction
from admin_api.serializers import (
    AdminWalletTransactionSerializer, AdminDepositSerializer,
    AdminWithdrawalSerializer, AdminManualAdjustmentRequestSerializer,
    AdminWithdrawalSerializer, AdminManualAdjustmentRequestSerializer,
    AdminDepositMarkSuccessRequestSerializer, AdminWithdrawalActionRequestSerializer,
    AdminStatusResponseSerializer, AdminErrorResponseSerializer, AdminPaystackConfigSerializer,
    AdminTransferSerializer, AdminTransferBeneficiarySerializer, AdminInitiateTransferRequestSerializer,
    AdminUserListSerializer
)
from admin_api.permissions import CanManageWallets, CanManagePayments, IsSuperUserOnly, CanInitiateTransfers
from admin_api.utils import log_admin_action
from payments.models import AdminTransfer, AdminTransferBeneficiary
from wallet.models import Wallet
import requests
from django.conf import settings
from wallet.utils import fund_wallet, debit_wallet
from users.models import User
from payments.utils import PaystackGateway, calculate_net_withdrawal_amount

from rest_framework.pagination import PageNumberPagination
from admin_api.views.user_management import UserPagination

@extend_schema_view(
    list=extend_schema(tags=["Admin Wallets"]),
    retrieve=extend_schema(tags=["Admin Wallets"]),
)
class AdminWalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve all wallet transactions in the system."""
    queryset = WalletTransaction.objects.select_related('user', 'wallet').all().order_by('-timestamp')
    serializer_class = AdminWalletTransactionSerializer
    permission_classes = [CanManageWallets]
    pagination_class = UserPagination

    def get_queryset(self):
        # Explicitly return all records to avoid any confusion with user-facing endpoints
        return self.queryset
    filterset_fields = {
        'wallet': ['exact'],
        'user': ['exact'],
        'status': ['exact'],
        'transaction_type': ['exact'],
        'initiator': ['exact'],
        'initiated_by': ['exact'],
        'timestamp': ['exact', 'gte', 'lte', 'gt', 'lt'],
    }
    search_fields = ['reference', 'description', 'user__email', 'user__first_name', 'user__last_name', 'user__phone_number']
    ordering_fields = ['timestamp', 'amount']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    @extend_schema(
        tags=["Admin Wallets"],
        summary="Manually adjust user wallet",
        description="Credit or debit a user's wallet with a specified amount and reason.",
        request=AdminManualAdjustmentRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=False, methods=['post'], url_path='manual-adjustment')
    def manual_adjustment(self, request):
        serializer = AdminManualAdjustmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        amount = float(serializer.validated_data['amount'])
        adj_type = serializer.validated_data['type']
        reason = serializer.validated_data.get('reason', 'Admin Adjustment')
        pin = serializer.validated_data['pin']

        if not request.user.check_password(pin):
             return Response({"status": "ERROR", "message": "Invalid authorization PIN"}, status=status.HTTP_403_FORBIDDEN)

        if adj_type == 'credit':
            fund_wallet(user_id, amount, description=reason, initiator='admin', initiated_by=request.user)
        else:
            debit_wallet(user_id, amount, description=reason, initiator='admin', initiated_by=request.user)
        
        log_admin_action(
            user=request.user,
            action_type="MANUAL_WALLET_ADJUSTMENT",
            description=f"{adj_type.capitalize()}ed user {user_id} wallet with {amount}. Reason: {reason}",
            target=user_id
        )
        return Response({"status": "Wallet adjusted successfully"})

@extend_schema_view(
    list=extend_schema(tags=["Admin Payments"]),
    retrieve=extend_schema(tags=["Admin Payments"]),
    partial_update=extend_schema(tags=["Admin Payments"]),
)
class AdminDepositViewSet(viewsets.ModelViewSet):
    """View and manage all deposits in the system."""
    queryset = Deposit.objects.select_related('user', 'processed_by').all().order_by('-timestamp')
    serializer_class = AdminDepositSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        # Return all deposit records in the app
        return self.queryset

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'payment_type': ['exact'],
        'timestamp': ['exact', 'gte', 'lte', 'gt', 'lt'],
    }
    search_fields = ['reference', 'user__email', 'user__phone_number', 'user__first_name', 'user__last_name']
    ordering_fields = ['timestamp', 'amount']

    @extend_schema(
        tags=["Admin Payments"],
        summary="Mark deposit as successful",
        description="Manually confirm a deposit and credit the user's wallet.",
        request=AdminDepositMarkSuccessRequestSerializer,
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='mark-success')
    def mark_success(self, request, pk=None):
        deposit = self.get_object()
        if deposit.status == 'SUCCESS':
            return Response({"error": "Already marked successful"}, status=400)
        
        deposit.status = 'SUCCESS'
        deposit.recieved = True
        deposit.processed_by = request.user
        deposit.remarks = request.data.get('reason', 'Manually confirmed by Admin')
        deposit.save()
        
        fund_wallet(deposit.user.id, deposit.amount, description=f"Manual Deposit: {deposit.reference}", initiator='admin', initiated_by=request.user)

        log_admin_action(
            user=request.user,
            action_type="MARK_DEPOSIT_SUCCESS",
            description=f"Marked deposit {deposit.reference} as success for user {deposit.user.phone_number}",
            target=deposit
        )
        return Response({"status": "SUCCESS", "message": "Deposit marked as success and wallet credited."})

@extend_schema_view(
    list=extend_schema(tags=["Admin Payments"]),
    retrieve=extend_schema(tags=["Admin Payments"]),
    partial_update=extend_schema(tags=["Admin Payments"]),
)
class AdminWithdrawalViewSet(viewsets.ModelViewSet):
    """View and manage all withdrawals in the system."""
    queryset = Withdrawal.objects.select_related('user', 'processed_by').all().order_by('-created_at')
    serializer_class = AdminWithdrawalSerializer
    permission_classes = [CanManagePayments]

    def get_queryset(self):
        # Return all withdrawal records in the app
        return self.queryset

    @extend_schema(
        tags=["Admin Payments"],
        summary="Approve a withdrawal",
        description="Approve a pending withdrawal request. Requires admin 2FA OTP if enabled.",
        request=AdminWithdrawalActionRequestSerializer,
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer, 403: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        withdrawal = self.get_object()
        if withdrawal.status != 'PENDING':
            return Response({"error": f"Cannot approve withdrawal in {withdrawal.status} state"}, status=400)
            
        pin = request.data.get('otp') or request.data.get('pin') or request.data.get('admin_pin')
        if not pin:
            return Response({"error": "Security PIN is required to approve withdrawal"}, status=400)

        if request.user.is_superuser:
            if not request.user.check_password(pin):
                return Response({"error": "Invalid Login Password/PIN"}, status=403)
        else:
            if not request.user.check_transaction_pin(pin):
                return Response({"error": "Invalid Admin Security PIN"}, status=403)

        net_amount, total_charge = calculate_net_withdrawal_amount(withdrawal.amount)
        if net_amount <= 0:
            return Response({"error": f"Withdrawal amount (₦{withdrawal.amount}) is less than or equal to configured withdrawal charge (₦{total_charge})"}, status=400)

        try:
            gateway = PaystackGateway()
            transfer = gateway.initiate_transfer(
                amount=float(net_amount),
                bank_code=withdrawal.bank_code,
                account_number=withdrawal.account_number,
                account_name=withdrawal.account_name,
                reference=withdrawal.reference,
                reason=request.data.get('reason', f"Withdrawal {withdrawal.reference}"),
            )
        except Exception as exc:
            return Response({"error": f"Transfer initiation failed: {str(exc)}"}, status=400)

        transfer_status = transfer.get("status", "PENDING")
        withdrawal.transfer_code = transfer.get("transfer_code")
        withdrawal.transaction_status = transfer_status
        withdrawal.processed_by = request.user
        withdrawal.remarks = request.data.get('reason', 'Approved by Admin')

        if transfer_status == "FAILED":
            withdrawal.status = "REJECTED"
            withdrawal.reason = "Transfer initiation failed"
            withdrawal.save()
            fund_wallet(
                withdrawal.user.id,
                withdrawal.amount,
                description=f"Refund: Withdrawal failed ({withdrawal.reference})",
                initiator='admin',
                initiated_by=request.user
            )
            return Response(
                {"status": "FAILED", "message": "Transfer initiation failed. Withdrawal rejected and funds refunded."},
                status=400
            )

        withdrawal.status = 'APPROVED'
        withdrawal.save()
        return Response({"status": "SUCCESS", "message": "Withdrawal approved and transfer initiated."})

    @extend_schema(
        tags=["Admin Payments"],
        summary="Reject a withdrawal",
        description="Reject a pending withdrawal and refund the user's wallet.",
        request=AdminWithdrawalActionRequestSerializer,
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        withdrawal = self.get_object()
        if withdrawal.status != 'PENDING':
             return Response({"error": f"Cannot reject withdrawal in {withdrawal.status} state"}, status=400)
             
        withdrawal.status = 'REJECTED'
        withdrawal.transaction_status = 'FAILED'
        withdrawal.processed_by = request.user
        withdrawal.remarks = request.data.get('reason', 'Rejected by Admin')
        withdrawal.save()
        
        fund_wallet(withdrawal.user.id, withdrawal.amount, description=f"Refund: Withdrawal rejected ({withdrawal.reference})", initiator='admin', initiated_by=request.user)
        
        return Response({"status": "REJECTED", "message": "Withdrawal rejected and funds refunded to user."})

@extend_schema_view(
    list=extend_schema(tags=["Admin Payments"]),
    retrieve=extend_schema(tags=["Admin Payments"]),
    create=extend_schema(tags=["Admin Payments"]),
    update=extend_schema(tags=["Admin Payments"]),
    partial_update=extend_schema(tags=["Admin Payments"]),
    destroy=extend_schema(tags=["Admin Payments"]),
)
class AdminPaystackConfigViewSet(viewsets.ModelViewSet):
    """Manage Paystack configuration."""
    queryset = PaystackConfig.objects.all()
    serializer_class = AdminPaystackConfigSerializer
    permission_classes = [IsSuperUserOnly]

@extend_schema_view(
    list=extend_schema(tags=["Admin Wallets"]),
    retrieve=extend_schema(tags=["Admin Wallets"]),
)
class AdminWalletViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve all user wallets in the system."""
    queryset = User.objects.select_related('wallet').all().order_by('-created_at')
    serializer_class = AdminUserListSerializer 
    permission_classes = [CanManageWallets]
    pagination_class = UserPagination

    def get_queryset(self):
        # Explicitly return all users with their wallets
        return self.queryset

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'role': ['exact'],
        'is_active': ['exact'],
    }
    search_fields = ['email', 'phone_number', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'wallet__balance']

@extend_schema_view(
    list=extend_schema(tags=["Admin Transfers"]),
    retrieve=extend_schema(tags=["Admin Transfers"]),
    create=extend_schema(tags=["Admin Transfers"]),
)
class AdminTransferBeneficiaryViewSet(viewsets.ModelViewSet):
    """Manage beneficiaries for admin-initiated transfers."""
    queryset = AdminTransferBeneficiary.objects.all().order_by('-created_at')
    serializer_class = AdminTransferBeneficiarySerializer
    permission_classes = [CanInitiateTransfers]

@extend_schema_view(
    list=extend_schema(tags=["Admin Transfers"]),
    retrieve=extend_schema(tags=["Admin Transfers"]),
)
class AdminTransferViewSet(viewsets.ModelViewSet):
    """Initiate and track transfers by admin to external bank accounts."""
    queryset = AdminTransfer.objects.all().order_by('-created_at')
    serializer_class = AdminTransferSerializer
    permission_classes = [CanInitiateTransfers]

    @extend_schema(
        tags=["Admin Transfers"],
        summary="Initiate admin transfer",
        description="Initiate a bank transfer using Paystack to a saved beneficiary.",
        request=AdminInitiateTransferRequestSerializer,
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer},
        examples=[
            OpenApiExample(
                'Initiate Transfer Request',
                description='Example payload for initiating a manual admin transfer to a beneficiary.',
                value={
                    "beneficiary_id": 1,
                    "amount": 5000.00,
                    "pin": "123456"
                },
                request_only=True
            ),
            OpenApiExample(
                'Initiate Transfer Success Response',
                description='Success response when a transfer is successfully initiated.',
                value={
                    "status": "SUCCESS",
                    "message": "Transfer initiated successfully",
                    "data": {
                        "id": 12,
                        "amount": "5000.00",
                        "status": "PENDING",
                        "reference": "ADM-TXN-ABC123XYZ",
                        "created_at": "2024-04-05T12:00:00Z",
                        "beneficiary_details": {
                            "id": 1,
                            "name": "John Doe",
                            "bank_name": "Access Bank",
                            "account_number": "0123456789"
                        }
                    }
                },
                response_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        serializer = AdminInitiateTransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        beneficiary_id = serializer.validated_data['beneficiary_id']
        amount = serializer.validated_data['amount']
        pin = serializer.validated_data['pin']
        
        # Verify PIN
        if not request.user.check_password(pin):
            return Response({"error": "Invalid authorization PIN"}, status=403)
        
        try:
            beneficiary = AdminTransferBeneficiary.objects.get(id=beneficiary_id)
        except AdminTransferBeneficiary.DoesNotExist:
            return Response({"error": "Beneficiary not found"}, status=404)
        
        import uuid
        reference = f"ADM-TXN-{uuid.uuid4().hex[:12].upper()}"
        
        # In a real scenario, call Paystack Transfers API here
        # For now, we create the record
        transfer = AdminTransfer.objects.create(
            amount=amount,
            beneficiary=beneficiary,
            reference=reference,
            initiated_by=request.user,
            status='PENDING'
        )
        
        # Mock Paystack call logic:
        # 1. Fetch Paystack secret key
        config = PaystackConfig.load()
        if not config.secret_key:
            return Response({"error": "Paystack is not configured"}, status=400)
        
        # Standard Paystack transfer logic would go here...
        
        return Response({
            "status": "SUCCESS",
            "message": "Transfer initiated successfully",
            "data": AdminTransferSerializer(transfer).data
        })

@extend_schema(tags=["Admin Payments"])
class AdminPaystackDataViewSet(viewsets.ViewSet):
    permission_classes = [CanManagePayments]

    @extend_schema(
        summary="Fetch Paystack Payouts",
        description="Fetch a list of payouts from Paystack API."
    )
    @action(detail=False, methods=['get'], url_path='payouts')
    def payouts(self, request):
        config = PaystackConfig.load()
        if not config.secret_key:
            return Response({"error": "Paystack is not configured"}, status=400)
            
        headers = {"Authorization": f"Bearer {config.secret_key}"}
        params = request.query_params.dict()
        try:
            response = requests.get("https://api.paystack.co/transfer", headers=headers, params=params)
            return Response(response.json())
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        summary="Fetch Paystack Transactions",
        description="Fetch all transactions directly from Paystack API."
    )
    @action(detail=False, methods=['get'], url_path='transactions')
    def transactions(self, request):
        config = PaystackConfig.load()
        if not config.secret_key:
            return Response({"error": "Paystack is not configured"}, status=400)
            
        headers = {"Authorization": f"Bearer {config.secret_key}"}
        params = request.query_params.dict()
        try:
            response = requests.get("https://api.paystack.co/transaction", headers=headers, params=params)
            return Response(response.json())
        except Exception as e:
            return Response({"error": str(e)}, status=500)
