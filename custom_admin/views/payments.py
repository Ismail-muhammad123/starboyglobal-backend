import logging
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import requests
from custom_admin.mixins import PortalPermissionMixin
from payments.models import Deposit, Withdrawal, PaystackConfig, AdminTransfer, AdminTransferBeneficiary
from payments.utils import PaystackGateway, calculate_net_withdrawal_amount
from summary.models import SystemTransaction, SiteConfig
from admin_api.models import AdminActionLog
from django.utils import timezone

logger = logging.getLogger(__name__)

class DepositListView(PortalPermissionMixin, View):
    required_permission = ('payments.Deposit', 'view')

    def get(self, request):
        qs = Deposit.objects.all().select_related('user').order_by('-timestamp')

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(user__phone_number__icontains=search)
            )

        paginator = Paginator(qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'custom_admin/payments/deposits.html', {
            'deposits': page_obj,
            'status_filter': status_filter or '',
            'search_query': search or ''
        })


class WithdrawalListView(PortalPermissionMixin, View):
    required_permission = ('payments.Withdrawal', 'view')

    def get(self, request):
        qs = Withdrawal.objects.all().select_related('user').order_by('-created_at')

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(user__phone_number__icontains=search) |
                Q(account_number__icontains=search)
            )

        paginator = Paginator(qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        config = SiteConfig.objects.first()

        return render(request, 'custom_admin/payments/withdrawals.html', {
            'withdrawals': page_obj,
            'status_filter': status_filter or '',
            'search_query': search or '',
            'site_config': config,
        })


class DepositDetailView(PortalPermissionMixin, View):
    required_permission = ('payments.Deposit', 'view')

    def get(self, request, pk):
        deposit = get_object_or_404(Deposit.objects.select_related('user', 'processed_by'), pk=pk)
        from wallet.models import WalletTransaction
        wallet_tx = WalletTransaction.objects.filter(deposit=deposit).first()
        return render(request, 'custom_admin/payments/deposit_detail.html', {
            'deposit': deposit,
            'wallet_tx': wallet_tx
        })


class WithdrawalDetailView(PortalPermissionMixin, View):
    required_permission = ('payments.Withdrawal', 'view')

    def get(self, request, pk):
        withdrawal = get_object_or_404(Withdrawal.objects.select_related('user', 'processed_by'), pk=pk)
        return render(request, 'custom_admin/payments/withdrawal_detail.html', {
            'withdrawal': withdrawal
        })


class WithdrawalApproveView(PortalPermissionMixin, View):
    required_permission = ('payments.Withdrawal', 'approve_withdrawal')

    def post(self, request, pk):
        withdrawal = get_object_or_404(Withdrawal.objects.select_related('user'), pk=pk)
        action_type = request.POST.get('action_type', '').strip().upper()  # APPROVED / REJECTED
        remarks = request.POST.get('remarks', '').strip()
        refund_wallet_option = request.POST.get('refund_wallet', 'true').strip().lower() in ('true', 'on', '1')

        if action_type not in ['APPROVED', 'REJECTED']:
            return JsonResponse({'status': 'error', 'message': 'Invalid action type.'}, status=400)

        if withdrawal.status != 'PENDING':
            return JsonResponse({'status': 'error', 'message': f'Withdrawal is already {withdrawal.status}.'}, status=400)

        from django.db import transaction
        from wallet.utils import fund_wallet
        from notifications.utils import NotificationService

        if action_type == 'APPROVED':
            admin_pin = request.POST.get('admin_pin', '').strip() or request.POST.get('pin', '').strip()
            if not admin_pin:
                return JsonResponse({'status': 'error', 'message': 'Security PIN is required to approve withdrawal.'}, status=400)

            if request.user.is_superuser:
                if not request.user.check_password(admin_pin):
                    return JsonResponse({'status': 'error', 'message': 'Invalid Login Password/PIN.'}, status=403)
            else:
                if not request.user.check_transaction_pin(admin_pin):
                    return JsonResponse({'status': 'error', 'message': 'Invalid Admin Security PIN.'}, status=403)

            # Initiate Paystack transfer if not already initiated
            if not withdrawal.transfer_code:
                net_amount, total_charge = calculate_net_withdrawal_amount(withdrawal.amount)
                if net_amount <= 0:
                    err_msg = f"Withdrawal amount (₦{withdrawal.amount}) is less than or equal to configured withdrawal charge (₦{total_charge})."
                    print(f"[Withdrawal Approve Error]: {err_msg}")
                    return JsonResponse({'status': 'error', 'message': err_msg}, status=400)

                try:
                    gateway = PaystackGateway()
                    transfer = gateway.initiate_transfer(
                        amount=float(net_amount),
                        bank_code=withdrawal.bank_code,
                        account_number=withdrawal.account_number,
                        account_name=withdrawal.account_name,
                        reference=withdrawal.reference,
                        reason=remarks or f"Withdrawal {withdrawal.reference}",
                    )
                    transfer_status = transfer.get("status", "PENDING")
                    withdrawal.transfer_code = transfer.get("transfer_code")
                    withdrawal.transaction_status = transfer_status

                    if transfer_status == "FAILED":
                        withdrawal.status = "REJECTED"
                        withdrawal.reason = "Paystack transfer initiation failed"
                        withdrawal.processed_by = request.user
                        withdrawal.remarks = remarks or "Transfer failed via Paystack"
                        withdrawal.save(update_fields=['transfer_code', 'transaction_status', 'status', 'reason', 'processed_by', 'remarks', 'updated_at'])

                        if refund_wallet_option:
                            fund_wallet(
                                user_id=withdrawal.user.id,
                                amount=withdrawal.amount,
                                description=f"Refund: Withdrawal transfer failed ({withdrawal.reference})",
                                initiator='admin',
                                initiated_by=request.user,
                            )

                        print(f"[Withdrawal Approval Failed]: Paystack transfer failed for {withdrawal.reference}")
                        logger.error(f"[Withdrawal Approval Failed]: Paystack transfer failed for {withdrawal.reference}")
                        return JsonResponse({'status': 'error', 'message': 'Paystack transfer failed during initiation.'}, status=400)

                except Exception as e:
                    err_msg = f"Paystack Transfer Error: {str(e)}"
                    print(f"[Withdrawal Approval Error]: {err_msg}")
                    logger.error(f"[Withdrawal Approval Error]: {err_msg}", exc_info=True)
                    withdrawal.remarks = f"Transfer attempt failed: {str(e)}"
                    withdrawal.save(update_fields=['remarks', 'updated_at'])
                    return JsonResponse({'status': 'error', 'message': err_msg}, status=400)
            else:
                withdrawal.transaction_status = 'SUCCESS'

        with transaction.atomic():
            withdrawal.status = action_type
            withdrawal.processed_by = request.user
            withdrawal.remarks = remarks
            withdrawal.save(update_fields=['status', 'processed_by', 'remarks', 'updated_at'])

            if action_type == 'REJECTED':
                withdrawal.reason = remarks or 'Rejected by Admin'
                withdrawal.transaction_status = 'FAILED'
                withdrawal.save(update_fields=['reason', 'transaction_status', 'updated_at'])

                if refund_wallet_option:
                    # Refund the user's debited wallet balance
                    fund_wallet(
                        user_id=withdrawal.user.id,
                        amount=withdrawal.amount,
                        description=f"Refund: Withdrawal rejected by admin ({withdrawal.reference})",
                        initiator='admin',
                        initiated_by=request.user,
                    )

                # Send notification to user
                notif_reason = remarks or "Rejected by Admin"
                if refund_wallet_option:
                    notif_reason += " (Amount refunded to wallet)"
                else:
                    notif_reason += " (No refund issued)"

                NotificationService.send_from_template(
                    withdrawal.user,
                    "withdrawal-rejected",
                    {
                        "amount": withdrawal.amount,
                        "reference": withdrawal.reference,
                        "reason": notif_reason
                    }
                )

            elif action_type == 'APPROVED':
                if not withdrawal.transaction_status or withdrawal.transaction_status == 'PENDING':
                    withdrawal.transaction_status = 'SUCCESS'
                withdrawal.save(update_fields=['transaction_status', 'updated_at'])

                # Send notification to user
                NotificationService.send_from_template(
                    withdrawal.user,
                    "withdrawal-approved",
                    {
                        "amount": withdrawal.amount,
                        "reference": withdrawal.reference,
                        "bank_name": withdrawal.bank_name
                    }
                )

            refund_msg = " (Refunded to wallet)" if (action_type == 'REJECTED' and refund_wallet_option) else ""
            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type=f"WITHDRAWAL_{action_type}",
                target_model="Withdrawal",
                target_id=str(withdrawal.pk),
                description=f"Withdrawal of ₦{withdrawal.amount} for {withdrawal.user.phone_number} set to {action_type}{refund_msg}. Remarks: {remarks or 'None'}"
            )

        return JsonResponse({'status': 'success', 'message': f"Withdrawal status updated to {action_type}."})


class AdminTransferListView(PortalPermissionMixin, View):
    required_permission = ('payments.AdminTransfer', 'view')

    def get(self, request):
        transfers = AdminTransfer.objects.all().select_related('beneficiary', 'initiated_by').order_by('-created_at')
        beneficiaries = AdminTransferBeneficiary.objects.all()
        return render(request, 'custom_admin/payments/transfers.html', {
            'transfers': transfers,
            'beneficiaries': beneficiaries
        })

    def post(self, request):
        from custom_admin.mixins import user_has_portal_permission
        if not user_has_portal_permission(request.user, 'payments.AdminTransfer', 'initiate_admin_transfer'):
            return JsonResponse({'status': 'error', 'message': 'You do not have permission to initiate admin bank transfers.'}, status=403)

        admin_pin = request.POST.get('admin_pin', '').strip()
        if not admin_pin:
            return JsonResponse({'status': 'error', 'message': 'Admin Security PIN is required.'}, status=400)

        is_pin_valid = request.user.check_transaction_pin(admin_pin) or request.user.check_password(admin_pin)
        if not is_pin_valid:
            return JsonResponse({'status': 'error', 'message': 'Invalid Admin Security PIN.'}, status=403)

        amount_str = request.POST.get('amount', '0').strip()
        remarks = request.POST.get('remarks', '').strip()
        beneficiary_id = request.POST.get('beneficiary_id')
        account_number = request.POST.get('account_number', '').strip()
        bank_code = request.POST.get('bank_code', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        account_name = request.POST.get('account_name', '').strip()

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            return JsonResponse({'status': 'error', 'message': 'Amount must be greater than 0.'}, status=400)

        beneficiary = None
        if beneficiary_id:
            beneficiary = get_object_or_404(AdminTransferBeneficiary, pk=beneficiary_id)
        elif account_number and bank_code:
            if not account_name:
                return JsonResponse({'status': 'error', 'message': 'Account details must be verified before proceeding.'}, status=400)

            beneficiary, _ = AdminTransferBeneficiary.objects.get_or_create(
                account_number=account_number,
                bank_code=bank_code,
                defaults={
                    'name': account_name,
                    'bank_name': bank_name or 'Bank Transfer'
                }
            )
            if account_name and beneficiary.name != account_name:
                beneficiary.name = account_name
                beneficiary.save(update_fields=['name'])
        else:
            return JsonResponse({'status': 'error', 'message': 'Please select a beneficiary or enter valid bank account details.'}, status=400)

        ref_code = f"ADM-TRF-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        config = PaystackConfig.load()
        secret_key = config.secret_key
        status_val = 'PENDING'
        transfer_code_val = None

        if secret_key:
            try:
                gateway = PaystackGateway(secret_key)
                trf_res = gateway.initiate_transfer(
                    amount=float(amount),
                    bank_code=beneficiary.bank_code,
                    account_number=beneficiary.account_number,
                    account_name=beneficiary.name,
                    reference=ref_code,
                    reason=remarks or "Admin Transfer"
                )
                status_val = (trf_res.get('status') or 'SUCCESS').upper()
                transfer_code_val = trf_res.get('transfer_code')
            except Exception as e:
                logger.error(f"Paystack transfer error: {str(e)}")
                return JsonResponse({'status': 'error', 'message': f'Bank Transfer Failed via Paystack: {str(e)}'}, status=400)

        transfer = AdminTransfer.objects.create(
            amount=amount,
            beneficiary=beneficiary,
            status=status_val,
            reference=ref_code,
            transfer_code=transfer_code_val,
            initiated_by=request.user,
            remarks=remarks
        )

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type="ADMIN_TRANSFER",
            target_model="AdminTransfer",
            target_id=str(transfer.pk),
            description=f"Initiated admin transfer of ₦{amount} to {beneficiary.name} ({beneficiary.bank_name} - {beneficiary.account_number})."
        )

        return JsonResponse({'status': 'success', 'message': f"Admin Transfer of ₦{amount} to {beneficiary.name} initiated successfully."})


class AdminBankListView(PortalPermissionMixin, View):
    required_permission = ('payments.AdminTransfer', 'view')

    def get(self, request):
        config = PaystackConfig.load()
        secret_key = config.secret_key
        banks = []

        if secret_key:
            try:
                gateway = PaystackGateway(secret_key)
                banks = gateway.list_banks()
            except Exception as e:
                logger.error(f"Error fetching banks from Paystack: {str(e)}")

        if not banks:
            banks = [
                {"name": "Access Bank", "code": "044"},
                {"name": "Access Bank (Diamond)", "code": "063"},
                {"name": "ALAT by WEMA", "code": "035A"},
                {"name": "First Bank of Nigeria", "code": "011"},
                {"name": "First City Monument Bank (FCMB)", "code": "214"},
                {"name": "Guaranty Trust Bank (GTB)", "code": "058"},
                {"name": "Kuda Bank", "code": "50211"},
                {"name": "Moniepoint Microfinance Bank", "code": "50515"},
                {"name": "OPay Digital Services Limited", "code": "999992"},
                {"name": "PalmPay", "code": "999991"},
                {"name": "Polaris Bank", "code": "076"},
                {"name": "Stanbic IBTC Bank", "code": "221"},
                {"name": "Sterling Bank", "code": "232"},
                {"name": "United Bank For Africa (UBA)", "code": "033"},
                {"name": "Wema Bank", "code": "035"},
                {"name": "Zenith Bank", "code": "057"}
            ]

        banks = sorted(banks, key=lambda x: x.get('name', ''))
        return JsonResponse({'status': 'success', 'banks': banks})


class AdminAccountResolveView(PortalPermissionMixin, View):
    required_permission = ('payments.AdminTransfer', 'view')

    def get(self, request):
        account_number = request.GET.get('account_number', '').strip()
        bank_code = request.GET.get('bank_code', '').strip()

        if not account_number or len(account_number) != 10 or not account_number.isdigit():
            return JsonResponse({'status': 'error', 'message': 'Please enter a valid 10-digit account number.'}, status=400)

        if not bank_code:
            return JsonResponse({'status': 'error', 'message': 'Please select a bank.'}, status=400)

        config = PaystackConfig.load()
        secret_key = config.secret_key

        if not secret_key:
            return JsonResponse({'status': 'error', 'message': 'Paystack API key is not configured.'}, status=400)

        try:
            gateway = PaystackGateway(secret_key)
            result = gateway.resolve_account(account_number, bank_code)
            return JsonResponse({
                'status': 'success',
                'data': {
                    'account_name': result.get('account_name', ''),
                    'account_number': account_number,
                    'bank_code': bank_code
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Could not resolve account details: {str(e)}'}, status=400)


class PaystackRecordsView(PortalPermissionMixin, View):
    required_permission = ('payments.PaystackConfig', 'view')

    def get(self, request):
        paystack_config = PaystackConfig.load()
        secret_key = paystack_config.secret_key

        raw_records = []
        error_msg = None

        search_query = request.GET.get('search', '').strip().lower()
        flow_filter = request.GET.get('flow', '').strip().lower()  # 'credit', 'debit'
        status_filter = request.GET.get('status', '').strip().lower()
        sort_by = request.GET.get('sort', '').strip().lower()

        if secret_key:
            headers = {'Authorization': f'Bearer {secret_key}'}
            # 1. Fetch transactions (incoming credits)
            try:
                res = requests.get('https://api.paystack.co/transaction?perPage=50', headers=headers, timeout=10)
                if res.status_code == 200:
                    for t in res.json().get('data', []):
                        amt_kobo = t.get('amount', 0)
                        amt_naira = float(amt_kobo) / 100.0
                        cust = t.get('customer', {}) or {}
                        cust_email = cust.get('email', '-')
                        first_n = cust.get('first_name') or ''
                        last_n = cust.get('last_name') or ''
                        full_n = f"{first_n} {last_n}".strip()

                        raw_records.append({
                            'id': t.get('id'),
                            'reference': t.get('reference', '-'),
                            'flow_type': 'CREDIT',
                            'flow_sign': '+',
                            'amount_naira': amt_naira,
                            'formatted_amount': f"₦{amt_naira:,.2f}",
                            'channel': t.get('channel', 'card'),
                            'status': t.get('status', 'unknown'),
                            'email': cust_email,
                            'customer_name': full_n or cust_email,
                            'date_str': t.get('paid_at') or t.get('created_at', ''),
                            'created_at': t.get('created_at', '')
                        })
                else:
                    error_msg = f"Paystack API returned status {res.status_code}"
            except Exception as e:
                error_msg = f"Failed to connect to Paystack API: {str(e)}"

            # 2. Fetch transfers (outgoing debits)
            try:
                res_trf = requests.get('https://api.paystack.co/transfer?perPage=50', headers=headers, timeout=10)
                if res_trf.status_code == 200:
                    for t in res_trf.json().get('data', []):
                        amt_kobo = t.get('amount', 0)
                        amt_naira = float(amt_kobo) / 100.0
                        recip = t.get('recipient', {}) or {}
                        recip_email = recip.get('email', '-')
                        recip_name = recip.get('name', 'Bank Recipient')

                        raw_records.append({
                            'id': t.get('id'),
                            'reference': t.get('reference', '') or t.get('transfer_code', '-'),
                            'flow_type': 'DEBIT',
                            'flow_sign': '-',
                            'amount_naira': amt_naira,
                            'formatted_amount': f"₦{amt_naira:,.2f}",
                            'channel': 'bank_transfer',
                            'status': t.get('status', 'unknown'),
                            'email': recip_email,
                            'customer_name': recip_name,
                            'date_str': t.get('createdAt') or t.get('created_at', ''),
                            'created_at': t.get('createdAt') or t.get('created_at', '')
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch Paystack transfers: {str(e)}")
        else:
            error_msg = "Paystack secret key is not configured in settings."

        # Filter by Flow Type (Credit / Debit)
        if flow_filter:
            raw_records = [t for t in raw_records if t['flow_type'].lower() == flow_filter]

        # Filter by Status
        if status_filter:
            raw_records = [t for t in raw_records if t['status'].lower() == status_filter]

        # Search filter (reference, email, customer_name, channel)
        if search_query:
            raw_records = [t for t in raw_records if (
                search_query in t['reference'].lower() or
                search_query in t['email'].lower() or
                search_query in t['customer_name'].lower() or
                search_query in t['channel'].lower()
            )]

        # Sorting
        if sort_by == 'amount_high':
            raw_records.sort(key=lambda x: x['amount_naira'], reverse=True)
        elif sort_by == 'amount_low':
            raw_records.sort(key=lambda x: x['amount_naira'])
        elif sort_by == 'date_oldest':
            raw_records.sort(key=lambda x: x['created_at'])
        else:  # default: newest date first
            raw_records.sort(key=lambda x: x['created_at'], reverse=True)

        payouts = SystemTransaction.objects.filter(transaction_type='CASHOUT').order_by('-created_at')[:25]

        return render(request, 'custom_admin/payments/paystack_records.html', {
            'paystack_txs': raw_records,
            'payouts': payouts,
            'error_msg': error_msg,
            'search_query': search_query or '',
            'flow_filter': flow_filter or '',
            'status_filter': status_filter or '',
            'sort_by': sort_by or ''
        })
