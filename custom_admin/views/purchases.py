from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from custom_admin.mixins import PortalPermissionMixin
from orders.models import Purchase
from wallet.models import Wallet, WalletTransaction
from admin_api.models import AdminActionLog


class PurchaseListView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'view')

    def get(self, request):
        qs = Purchase.objects.all().select_related('user', 'provider').order_by('-time')

        purchase_type = request.GET.get('type')
        if purchase_type:
            qs = qs.filter(purchase_type=purchase_type)

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(beneficiary__icontains=search) |
                Q(user__phone_number__icontains=search) |
                Q(user__email__icontains=search)
            )

        per_page = request.GET.get('per_page', 25)
        try:
            per_page = int(per_page)
            if per_page not in [25, 50, 100, 200]:
                per_page = 25
        except (ValueError, TypeError):
            per_page = 25

        paginator = Paginator(qs, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'purchases': page_obj,
            'type_filter': purchase_type or '',
            'status_filter': status_filter or '',
            'search_query': search or '',
            'per_page': per_page,
        }
        return render(request, 'custom_admin/purchases/list.html', context)


class PurchaseDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'view')

    def get(self, request, pk):
        purchase_obj = get_object_or_404(Purchase, pk=pk)
        return render(request, 'custom_admin/purchases/detail.html', {'purchase': purchase_obj})


class PurchaseRefundView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'change')

    def post(self, request, pk):
        purchase_obj = get_object_or_404(Purchase, pk=pk)
        if purchase_obj.status == 'refunded':
            return JsonResponse({'status': 'error', 'message': 'Purchase has already been refunded.'}, status=400)

        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(user=purchase_obj.user)
            bal_before = wallet.balance
            bal_after = bal_before + purchase_obj.amount
            wallet.balance = bal_after
            wallet.save()

            WalletTransaction.objects.create(
                user=purchase_obj.user,
                wallet=wallet,
                transaction_type='credit',
                amount=purchase_obj.amount,
                balance_before=bal_before,
                balance_after=bal_after,
                description=f"Refund for failed {purchase_obj.purchase_type} purchase (Ref: {purchase_obj.reference})",
                initiator='admin',
                initiated_by=request.user,
                reference=f"REFUND-{purchase_obj.reference}",
                status='success'
            )

            purchase_obj.status = 'refunded'
            purchase_obj.remarks = f"Manual refund by admin ({request.user.phone_number})"
            purchase_obj.save(update_fields=['status', 'remarks'])

            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type="REFUND_PURCHASE",
                target_model="Purchase",
                target_id=str(purchase_obj.pk),
                description=f"Refunded {purchase_obj.amount} for purchase {purchase_obj.reference} to user {purchase_obj.user.phone_number}."
            )

        return JsonResponse({'status': 'success', 'message': f"Successfully refunded ₦{purchase_obj.amount} to user wallet."})
