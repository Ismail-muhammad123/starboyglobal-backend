from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from custom_admin.mixins import PortalPermissionMixin
from wallet.models import Wallet, WalletTransaction
from users.models import User
from admin_api.models import AdminActionLog


class WalletListView(PortalPermissionMixin, View):
    required_permission = ('wallet.Wallet', 'view')

    def get(self, request):
        qs = Wallet.objects.all().select_related('user').order_by('-balance')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(user__phone_number__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )

        paginator = Paginator(qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'custom_admin/wallet/list.html', {
            'wallets': page_obj,
            'search_query': search or ''
        })


class WalletDetailView(PortalPermissionMixin, View):
    required_permission = ('wallet.Wallet', 'view')

    def get(self, request, pk):
        from django.db.models import Sum
        wallet_obj = get_object_or_404(Wallet, pk=pk)
        transactions_qs = WalletTransaction.objects.filter(
            user=wallet_obj.user
        ).select_related('initiated_by').order_by('-timestamp')

        # Stats
        stats = transactions_qs.aggregate(
            total_credits=Sum('amount', filter=Q(transaction_type='credit')),
            total_debits=Sum('amount', filter=Q(transaction_type='debit')),
        )

        transactions = transactions_qs[:50]

        return render(request, 'custom_admin/wallet/detail.html', {
            'wallet': wallet_obj,
            'transactions': transactions,
            'total_credits': stats['total_credits'] or 0,
            'total_debits': stats['total_debits'] or 0,
            'tx_count': transactions_qs.count(),
        })


class TransactionListView(PortalPermissionMixin, View):
    required_permission = ('wallet.WalletTransaction', 'view')

    def get(self, request):
        qs = WalletTransaction.objects.all().select_related('user').order_by('-timestamp')

        tx_type = request.GET.get('type')
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(user__phone_number__icontains=search) |
                Q(description__icontains=search)
            )

        paginator = Paginator(qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'custom_admin/wallet/transactions.html', {
            'transactions': page_obj,
            'type_filter': tx_type or '',
            'search_query': search or ''
        })


class ManualTransactionView(PortalPermissionMixin, View):
    required_permission = ('wallet.WalletTransaction', 'adjust_wallet')

    def get(self, request):
        user_phone = request.GET.get('user', '')
        return render(request, 'custom_admin/wallet/manual_transaction.html', {'target_phone': user_phone})

    def post(self, request):
        phone = request.POST.get('phone_number', '').strip()
        tx_type = request.POST.get('transaction_type')  # credit / debit
        amount_str = request.POST.get('amount', '0').strip()
        description = request.POST.get('description', '').strip()
        admin_pin = request.POST.get('admin_pin', '').strip()

        if not admin_pin:
            return JsonResponse({'status': 'error', 'message': 'Admin Security PIN is required.'}, status=400)

        is_pin_valid = request.user.check_transaction_pin(admin_pin) or request.user.check_password(admin_pin)
        if not is_pin_valid:
            return JsonResponse({'status': 'error', 'message': 'Invalid Admin Security PIN.'}, status=403)

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            return JsonResponse({'status': 'error', 'message': 'Amount must be greater than 0.'}, status=400)

        if tx_type not in ['credit', 'debit']:
            return JsonResponse({'status': 'error', 'message': 'Invalid transaction type.'}, status=400)

        user_obj = User.objects.filter(phone_number=phone).first()
        if not user_obj:
            return JsonResponse({'status': 'error', 'message': f'User with phone {phone} not found.'}, status=404)

        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(user=user_obj)
            bal_before = wallet.balance

            if tx_type == 'debit' and bal_before < amount:
                return JsonResponse({'status': 'error', 'message': f'Insufficient wallet balance (Current: ₦{bal_before}).'}, status=400)

            bal_after = (bal_before + amount) if tx_type == 'credit' else (bal_before - amount)
            wallet.balance = bal_after
            wallet.save()

            ref_code = f"MANUAL-{tx_type.upper()}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

            tx_entry = WalletTransaction.objects.create(
                user=user_obj,
                wallet=wallet,
                transaction_type=tx_type,
                amount=amount,
                balance_before=bal_before,
                balance_after=bal_after,
                description=description or f"Manual {tx_type} by admin ({request.user.phone_number})",
                initiator='admin',
                initiated_by=request.user,
                reference=ref_code,
                status='success'
            )

            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type=f"MANUAL_{tx_type.upper()}_WALLET",
                target_model="Wallet",
                target_id=str(wallet.pk),
                description=f"Manual {tx_type} of ₦{amount} for user {user_obj.phone_number}."
            )

        return JsonResponse({
            'status': 'success',
            'message': f"Successfully {tx_type}ed ₦{amount} to {user_obj.phone_number}. New balance: ₦{bal_after}."
        })


class WalletUserLookupView(PortalPermissionMixin, View):
    required_permission = ('wallet.Wallet', 'view')

    def get(self, request):
        phone = request.GET.get('phone', '').strip() or request.GET.get('phone_number', '').strip()
        if not phone:
            return JsonResponse({'status': 'error', 'message': 'Phone number is required.'}, status=400)

        user_obj = User.objects.filter(phone_number=phone).first()
        if not user_obj:
            return JsonResponse({'status': 'error', 'message': f'User with phone number "{phone}" not found.'}, status=404)

        wallet, _ = Wallet.objects.get_or_create(user=user_obj)
        full_name_val = user_obj.full_name() if callable(getattr(user_obj, 'full_name', None)) else getattr(user_obj, 'full_name', f"{user_obj.first_name} {user_obj.last_name}".strip())

        return JsonResponse({
            'status': 'success',
            'user': {
                'id': user_obj.pk,
                'phone_number': user_obj.phone_number,
                'full_name': full_name_val or user_obj.phone_number,
                'email': user_obj.email or '',
                'wallet_balance': float(wallet.balance),
                'formatted_balance': f"₦{wallet.balance:,.2f}",
                'is_active': user_obj.is_active,
            }
        })

