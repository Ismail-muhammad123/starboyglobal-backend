from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import requests
from custom_admin.mixins import PortalPermissionMixin
from payments.models import Deposit, Withdrawal, PaystackConfig, AdminTransfer, AdminTransferBeneficiary
from summary.models import SystemTransaction
from admin_api.models import AdminActionLog
from django.utils import timezone

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

        return render(request, 'custom_admin/payments/withdrawals.html', {
            'withdrawals': page_obj,
            'status_filter': status_filter or '',
            'search_query': search or ''
        })


class WithdrawalApproveView(PortalPermissionMixin, View):
    required_permission = ('payments.Withdrawal', 'change')

    def post(self, request, pk):
        withdrawal = get_object_or_404(Withdrawal, pk=pk)
        action_type = request.POST.get('action_type')  # APPROVED / REJECTED
        remarks = request.POST.get('remarks', '').strip()

        if action_type not in ['APPROVED', 'REJECTED']:
            return JsonResponse({'status': 'error', 'message': 'Invalid action type.'}, status=400)

        withdrawal.status = action_type
        withdrawal.processed_by = request.user
        withdrawal.remarks = remarks
        withdrawal.save()

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type=f"WITHDRAWAL_{action_type}",
            target_model="Withdrawal",
            target_id=str(withdrawal.pk),
            description=f"Withdrawal of ₦{withdrawal.amount} for {withdrawal.user.phone_number} set to {action_type}."
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
        beneficiary_id = request.POST.get('beneficiary_id')
        amount_str = request.POST.get('amount', '0')
        remarks = request.POST.get('remarks', '').strip()

        try:
            amount = float(amount_str)
            if amount <= 0: raise ValueError
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid amount.'}, status=400)

        beneficiary = get_object_or_404(AdminTransferBeneficiary, pk=beneficiary_id)
        ref_code = f"ADM-TRF-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        transfer = AdminTransfer.objects.create(
            amount=amount,
            beneficiary=beneficiary,
            status='PENDING',
            reference=ref_code,
            initiated_by=request.user,
            remarks=remarks
        )

        return JsonResponse({'status': 'success', 'message': f"Admin Transfer of ₦{amount} to {beneficiary.name} initiated."})


class PaystackRecordsView(PortalPermissionMixin, View):
    required_permission = ('payments.PaystackConfig', 'view')

    def get(self, request):
        paystack_config = PaystackConfig.load()
        secret_key = paystack_config.secret_key

        paystack_txs = []
        error_msg = None

        if secret_key:
            try:
                headers = {'Authorization': f'Bearer {secret_key}'}
                res = requests.get('https://api.paystack.co/transaction?perPage=25', headers=headers, timeout=10)
                if res.status_code == 200:
                    paystack_txs = res.json().get('data', [])
                else:
                    error_msg = f"Paystack API returned status {res.status_code}"
            except Exception as e:
                error_msg = f"Failed to connect to Paystack API: {str(e)}"

        payouts = SystemTransaction.objects.filter(transaction_type='CASHOUT').order_by('-created_at')[:25]

        return render(request, 'custom_admin/payments/paystack_records.html', {
            'paystack_txs': paystack_txs,
            'payouts': payouts,
            'error_msg': error_msg
        })
