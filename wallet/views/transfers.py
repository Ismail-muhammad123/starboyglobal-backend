import uuid
from django.db import transaction as db_transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from wallet.models import TransferBeneficiary, User
from wallet.serializers import (
    BankTransferRequestSerializer, BankTransferResponseSerializer, WalletTransferSerializer, 
    WalletTransferResponseSerializer, VerifyRecipientRequestSerializer, VerifyRecipientResponseSerializer, 
    TransferBeneficiarySerializer, ErrorResponseSerializer
)
from wallet.utils import fund_wallet, debit_wallet, apply_charges, refund_charges, validate_balance_for_transaction
from notifications.utils import NotificationService
from payments.models import Withdrawal
from payments.utils import PaystackGateway, calculate_net_withdrawal_amount
from summary.models import SiteConfig
import logging

logger = logging.getLogger(__name__)

class InitiateBankTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(tags=["Wallet - Withdrawals"], summary="Withdraw to bank", request=BankTransferRequestSerializer, responses={201: BankTransferResponseSerializer})
    def post(self, request):
        serializer = BankTransferRequestSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        user, amount, pin = request.user, serializer.validated_data['amount'], serializer.validated_data['transaction_pin']
        if not user.check_transaction_pin(pin): return Response({"error": "Invalid PIN"}, status=403)
        config = SiteConfig.objects.first()
        if config and not config.withdrawals_enabled:
            return Response({"error": "Withdrawals are currently disabled"}, status=403)

        # Validate balance against amount + blocking charges
        is_valid, total_required, err_msg = validate_balance_for_transaction(user.id, 'transfer_others', amount)
        if not is_valid:
            return Response({"error": err_msg}, status=400)

        # Get sender virtual account details
        sender_account_name = None
        sender_account_number = None
        sender_bank_name = None
        try:
            va = user.virtual_account
            sender_account_name = va.account_name
            sender_account_number = va.account_number
            sender_bank_name = va.bank_name
        except Exception:
            pass

        # Receiver bank details (the withdrawal target bank account)
        receiver_account_name = serializer.validated_data['account_name']
        receiver_account_number = serializer.validated_data['account_number']
        receiver_bank_name = serializer.validated_data['bank_name']

        ref = f"WTH-{uuid.uuid4().hex[:12].upper()}"
        wallet_tx = None
        try:
            with db_transaction.atomic():
                _, wallet_tx = debit_wallet(
                    user.id,
                    amount,
                    description=f"Withdrawal to {receiver_bank_name}",
                    reference=ref,
                    initiator="self",
                    sender_account_name=sender_account_name,
                    sender_account_number=sender_account_number,
                    sender_bank_name=sender_bank_name,
                    receiver_account_name=receiver_account_name,
                    receiver_account_number=receiver_account_number,
                    receiver_bank_name=receiver_bank_name,
                    return_tx=True
                )
                apply_charges(user.id, 'transfer_others', amount, parent_wallet_tx=wallet_tx, initiator='self')
                withdrawal = Withdrawal.objects.create(
                    user=user,
                    amount=amount,
                    bank_name=receiver_bank_name,
                    bank_code=serializer.validated_data['bank_code'],
                    account_number=receiver_account_number,
                    account_name=receiver_account_name,
                    reference=ref,
                    status="PENDING",
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        if config and config.automatic_withdrawal:
            net_amount, total_charge = calculate_net_withdrawal_amount(amount)
            if net_amount <= 0:
                refund_err = f"Withdrawal amount (₦{amount}) is invalid."
                print(f"[Auto Withdrawal Error]: {refund_err}")
                fund_wallet(
                    user.id,
                    amount,
                    description=f"Refund: Withdrawal failed ({ref})",
                    initiator='system'
                )
                if wallet_tx:
                    refund_charges(wallet_tx)
                withdrawal.status = "REJECTED"
                withdrawal.reason = refund_err
                withdrawal.save(update_fields=["status", "reason", "updated_at"])
                return Response({"error": refund_err}, status=400)

            try:
                gateway = PaystackGateway()
                transfer = gateway.initiate_transfer(
                    amount=float(net_amount),
                    bank_code=withdrawal.bank_code,
                    account_number=withdrawal.account_number,
                    account_name=withdrawal.account_name,
                    reference=withdrawal.reference,
                    reason=f"Withdrawal {withdrawal.reference}",
                )
                transfer_status = transfer.get("status", "PENDING")
                withdrawal.transfer_code = transfer.get("transfer_code")
                withdrawal.transaction_status = transfer_status
                withdrawal.status = "APPROVED" if transfer_status != "FAILED" else "REJECTED"
                withdrawal.reason = None if transfer_status != "FAILED" else "Transfer initiation failed"
                withdrawal.save(update_fields=["transfer_code", "transaction_status", "status", "reason", "updated_at"])

                if transfer_status == "FAILED":
                    fund_wallet(
                        withdrawal.user.id,
                        withdrawal.amount,
                        description=f"Refund: Withdrawal failed ({withdrawal.reference})",
                        initiator='system',
                        sender_account_name=receiver_account_name,
                        sender_account_number=receiver_account_number,
                        sender_bank_name=receiver_bank_name,
                        receiver_account_name=sender_account_name,
                        receiver_account_number=sender_account_number,
                        receiver_bank_name=sender_bank_name,
                    )
                    if wallet_tx:
                        refund_charges(wallet_tx)
                    return Response(
                        {"message": "Withdrawal failed and amount refunded", "reference": ref},
                        status=400
                    )

                NotificationService.send_from_template(
                    user,
                    "withdrawal-initiated",
                    {"amount": amount, "bank_name": serializer.validated_data['bank_name'], "reference": ref}
                )
                return Response({"message": "Withdrawal approved and transfer initiated", "reference": ref}, status=201)
            except Exception as exc:
                print(f"[Auto Withdrawal Paystack Error]: {str(exc)}")
                logger.error(f"[Auto Withdrawal Paystack Error]: {str(exc)}", exc_info=True)
                withdrawal.remarks = f"Automatic transfer initiation failed: {str(exc)}"
                withdrawal.save(update_fields=["remarks", "updated_at"])

        NotificationService.send_from_template(user, "withdrawal-initiated", {"amount": amount, "bank_name": serializer.validated_data['bank_name'], "reference": ref})
        return Response({"message": "Withdrawal initiated", "reference": ref}, status=201)

class WalletTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(tags=["Wallet - P2P"], summary="Transfer to another wallet", request=WalletTransferSerializer, responses={200: WalletTransferResponseSerializer})
    def post(self, request):
        serializer = WalletTransferSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        sender, amount, phone, pin = request.user, serializer.validated_data['amount'], serializer.validated_data['recipient_phone'], serializer.validated_data['transaction_pin']
        if not sender.check_transaction_pin(pin): return Response({"error": "Incorrect PIN"}, status=401)
        search_phone = phone[1:] if phone.startswith('0') else phone
        try: recipient = User.objects.get(phone_number__icontains=search_phone)
        except User.DoesNotExist: return Response({"error": "Recipient not found"}, status=404)
        if sender == recipient: return Response({"error": "Cannot transfer to yourself"}, status=400)

        # Validate sender balance for amount + blocking charges
        is_valid, total_required, err_msg = validate_balance_for_transaction(sender.id, 'transfer_p2p', amount)
        if not is_valid:
            return Response({"error": err_msg}, status=400)

        # Get sender virtual account details
        sender_account_name = None
        sender_account_number = None
        sender_bank_name = None
        try:
            va_sender = sender.virtual_account
            sender_account_name = va_sender.account_name
            sender_account_number = va_sender.account_number
            sender_bank_name = va_sender.bank_name
        except Exception:
            pass

        # Get recipient virtual account details
        receiver_account_name = None
        receiver_account_number = None
        receiver_bank_name = None
        try:
            va_recipient = recipient.virtual_account
            receiver_account_name = va_recipient.account_name
            receiver_account_number = va_recipient.account_number
            receiver_bank_name = va_recipient.bank_name
        except Exception:
            pass

        try:
            with db_transaction.atomic():
                _, sender_tx = debit_wallet(
                    sender.id,
                    amount,
                    description=f"Transfer to {recipient.phone_number}",
                    initiator='self',
                    sender_account_name=sender_account_name,
                    sender_account_number=sender_account_number,
                    sender_bank_name=sender_bank_name,
                    receiver_account_name=receiver_account_name,
                    receiver_account_number=receiver_account_number,
                    receiver_bank_name=receiver_bank_name,
                    return_tx=True
                )
                fund_wallet(
                    recipient.id,
                    amount,
                    description=f"Transfer from {sender.phone_number}",
                    initiator='self',
                    sender_account_name=sender_account_name,
                    sender_account_number=sender_account_number,
                    sender_bank_name=sender_bank_name,
                    receiver_account_name=receiver_account_name,
                    receiver_account_number=receiver_account_number,
                    receiver_bank_name=receiver_bank_name,
                )
                apply_charges(sender.id, 'transfer_p2p', amount, parent_wallet_tx=sender_tx, initiator='self')
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        NotificationService.send_from_template(
            sender, 
            "wallet-transfer-sent", 
            {"amount": amount, "recipient": recipient.full_name or recipient.phone_number}
        )
        NotificationService.send_from_template(
            recipient, 
            "wallet-transfer-received", 
            {"amount": amount, "sender": sender.full_name or sender.phone_number, "balance": recipient.wallet.balance}
        )
        return Response({"success": True, "message": f"Transferred ₦{amount} to {recipient.full_name}."})


class VerifyRecipientView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(tags=["Wallet - P2P"], summary="Verify recipient", parameters=[VerifyRecipientRequestSerializer], responses={200: VerifyRecipientResponseSerializer})
    def get(self, request):
        phone = request.query_params.get('phone_number')
        if not phone: return Response({"error": "Phone required"}, status=400)
        search_phone = phone[1:] if phone.startswith('0') else phone

        if search_phone == request.user.phone_number: return Response({"error": "Cannot transfer to yourself"}, status=400)
        try:
            r = User.objects.get(phone_number__icontains=search_phone)
            return Response({"full_name": r.full_name, "phone_number": r.phone_number, "profile_image": r.profile_image.url if r.profile_image else None})
        except User.DoesNotExist: return Response({"error": "Not found"}, status=404)

class TransferBeneficiaryListCreateView(generics.ListCreateAPIView):
    serializer_class = TransferBeneficiarySerializer; permission_classes = [permissions.IsAuthenticated]
    @extend_schema(tags=["Wallet - Beneficiaries"])
    def get_queryset(self): return TransferBeneficiary.objects.filter(user=self.request.user).order_by('-id')
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class TransferBeneficiaryDeleteView(generics.DestroyAPIView):
    serializer_class = TransferBeneficiarySerializer; permission_classes = [permissions.IsAuthenticated]
    @extend_schema(tags=["Wallet - Beneficiaries"])
    def get_queryset(self): return TransferBeneficiary.objects.filter(user=self.request.user).order_by('-id')
