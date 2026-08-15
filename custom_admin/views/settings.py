from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from custom_admin.mixins import PortalPermissionMixin
from summary.models import SiteConfig, ServiceCashback
from payments.models import PaystackConfig
from users.models import ReferralConfig, RoleUpgradeConfig
from wallet.models import BonusConfig
from orders.models import PromoCode
from admin_api.models import AdminActionLog


class SiteConfigView(PortalPermissionMixin, View):
    required_permission = ('summary.SiteConfig', 'view')

    def get(self, request):
        config, _ = SiteConfig.objects.get_or_create(pk=1)
        return render(request, 'custom_admin/settings/site_config.html', {'config': config})

    def post(self, request):
        config, _ = SiteConfig.objects.get_or_create(pk=1)
        config.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        config.airtime_active = request.POST.get('airtime_active') == 'on'
        config.data_active = request.POST.get('data_active') == 'on'
        config.tv_active = request.POST.get('tv_active') == 'on'
        config.electricity_active = request.POST.get('electricity_active') == 'on'
        config.education_active = request.POST.get('education_active') == 'on'
        config.automatic_withdrawal = request.POST.get('automatic_withdrawal') == 'on'
        config.withdrawals_enabled = request.POST.get('withdrawals_enabled') == 'on'
        config.deposit_charge_fixed = request.POST.get('deposit_charge_fixed', 0)
        config.deposit_charge_percentage = request.POST.get('deposit_charge_percentage', 0)
        config.withdrawal_charge_fixed = request.POST.get('withdrawal_charge_fixed', 0)
        config.withdrawal_charge_percentage = request.POST.get('withdrawal_charge_percentage', 0)
        config.save()

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type="UPDATE_SITE_CONFIG",
            target_model="SiteConfig",
            target_id="1",
            description="Site configuration updated."
        )

        return JsonResponse({'status': 'success', 'message': 'Site Configuration updated.'})


class PaystackConfigView(PortalPermissionMixin, View):
    required_permission = ('payments.PaystackConfig', 'view')

    def get(self, request):
        config = PaystackConfig.load()
        return render(request, 'custom_admin/settings/paystack.html', {'config': config})

    def post(self, request):
        config = PaystackConfig.load()
        config.is_active = request.POST.get('is_active') == 'on'
        config.public_key = request.POST.get('public_key', '').strip()
        config.secret_key = request.POST.get('secret_key', '').strip()
        config.save()

        return JsonResponse({'status': 'success', 'message': 'Paystack Configuration updated.'})


class ReferralConfigView(PortalPermissionMixin, View):
    required_permission = ('users.ReferralConfig', 'view')

    def get(self, request):
        config, _ = ReferralConfig.objects.get_or_create(pk=1)
        return render(request, 'custom_admin/settings/referrals.html', {'config': config})

    def post(self, request):
        config, _ = ReferralConfig.objects.get_or_create(pk=1)
        config.is_active = request.POST.get('is_active') == 'on'
        config.commission_type = request.POST.get('commission_type', 'flat')
        config.commission_value = request.POST.get('commission_value', 0)
        config.commission_mode = request.POST.get('commission_mode', 'signup')
        config.save()

        return JsonResponse({'status': 'success', 'message': 'Referral Configuration updated.'})


class RoleUpgradeConfigView(PortalPermissionMixin, View):
    required_permission = ('users.RoleUpgradeConfig', 'view')

    def get(self, request):
        config, _ = RoleUpgradeConfig.objects.get_or_create(pk=1)
        return render(request, 'custom_admin/settings/role_upgrades.html', {'config': config})

    def post(self, request):
        config, _ = RoleUpgradeConfig.objects.get_or_create(pk=1)
        config.is_active = request.POST.get('is_active') == 'on'
        config.customer_to_agent_fee = request.POST.get('customer_to_agent_fee', 0)
        config.customer_to_developer_fee = request.POST.get('customer_to_developer_fee', 0)
        config.agent_to_developer_fee = request.POST.get('agent_to_developer_fee', 0)
        config.save()

        return JsonResponse({'status': 'success', 'message': 'Role Upgrade Configuration updated.'})


class CashbackConfigView(PortalPermissionMixin, View):
    required_permission = ('summary.ServiceCashback', 'view')

    def get(self, request):
        cashbacks = ServiceCashback.objects.all()
        return render(request, 'custom_admin/settings/cashback.html', {
            'cashbacks': cashbacks,
            'service_choices': ServiceCashback.SERVICE_CHOICES,
            'cashback_types': ServiceCashback.CASHBACK_TYPE_CHOICES,
        })

    def post(self, request):
        # --- Delete action ---
        if request.POST.get('_delete') == '1':
            cashback_id = request.POST.get('cashback_id')
            try:
                cb = ServiceCashback.objects.get(pk=cashback_id)
                label = cb.get_service_type_display()
                cb.delete()
                return JsonResponse({'status': 'success', 'message': f'{label} cashback rule deleted.'})
            except ServiceCashback.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Cashback rule not found.'}, status=404)

        # --- Create / Edit ---
        try:
            cashback_value = float(request.POST.get('cashback_value', 0))
            min_purchase_amount = float(request.POST.get('min_purchase_amount', 0))
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid numeric values.'}, status=400)

        cashback_type = request.POST.get('cashback_type', 'flat')
        is_active = request.POST.get('is_active') in ('true', 'on')

        cashback_id = request.POST.get('cashback_id', '').strip()

        if cashback_id:
            # Edit existing rule by PK
            try:
                cb = ServiceCashback.objects.get(pk=cashback_id)
                cb.cashback_type = cashback_type
                cb.cashback_value = cashback_value
                cb.min_purchase_amount = min_purchase_amount
                cb.is_active = is_active
                cb.save()
                return JsonResponse({'status': 'success', 'message': f'Cashback rule for {cb.get_service_type_display()} updated successfully.'})
            except ServiceCashback.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Cashback rule not found.'}, status=404)
        else:
            # Create new rule (service_type is the unique key)
            service_type = request.POST.get('service_type')
            if not service_type:
                return JsonResponse({'status': 'error', 'message': 'Service type is required.'}, status=400)

            cb, created = ServiceCashback.objects.update_or_create(
                service_type=service_type,
                defaults={
                    'cashback_type': cashback_type,
                    'cashback_value': cashback_value,
                    'min_purchase_amount': min_purchase_amount,
                    'is_active': is_active,
                }
            )
            action = "created" if created else "updated"
            return JsonResponse({'status': 'success', 'message': f'Cashback rule for {cb.get_service_type_display()} {action} successfully.'})


class PromoCodesView(PortalPermissionMixin, View):
    required_permission = ('orders.PromoCode', 'view')

    def get(self, request):
        codes = PromoCode.objects.all().order_by('-expiry_date')
        return render(request, 'custom_admin/settings/promo_codes.html', {'codes': codes})

    def post(self, request):
        code = request.POST.get('code', '').strip().upper()
        discount_amount = request.POST.get('discount_amount', 0)
        max_uses = request.POST.get('max_uses', 100)
        expiry_date = request.POST.get('expiry_date')

        PromoCode.objects.create(
            code=code,
            discount_amount=discount_amount,
            max_uses=max_uses,
            expiry_date=expiry_date,
            is_active=True
        )

        return JsonResponse({'status': 'success', 'message': f"Promo code '{code}' created."})


from wallet.models import TransactionCharge

class TransactionChargesView(PortalPermissionMixin, View):
    required_permission = ('wallet.TransactionCharge', 'view')

    def get(self, request):
        charges = TransactionCharge.objects.all().order_by('transaction_type', '-created_at')
        return render(request, 'custom_admin/settings/transaction_charges.html', {
            'charges': charges,
            'transaction_types': TransactionCharge.TRANSACTION_TYPES,
            'charge_types': TransactionCharge.CHARGE_TYPES,
        })

    def post(self, request):
        # --- Delete action ---
        if request.POST.get('_delete') == '1':
            charge_id = request.POST.get('charge_id')
            try:
                charge = TransactionCharge.objects.get(pk=charge_id)
                name = charge.name
                charge.delete()
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type="DELETE_TRANSACTION_CHARGE",
                    target_model="TransactionCharge",
                    target_id=str(charge_id),
                    description=f"Deleted transaction charge: {name}"
                )
                return JsonResponse({'status': 'success', 'message': f"Charge rule '{name}' deleted."})
            except TransactionCharge.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Charge rule not found.'}, status=404)

        # --- Create / Edit action ---
        name = request.POST.get('name', '').strip()
        transaction_type = request.POST.get('transaction_type', '').strip()
        charge_type = request.POST.get('charge_type', 'flat').strip()
        
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Name is required.'}, status=400)
        if not transaction_type:
            return JsonResponse({'status': 'error', 'message': 'Transaction type is required.'}, status=400)

        try:
            amount = float(request.POST.get('amount', 0))
            if amount < 0:
                return JsonResponse({'status': 'error', 'message': 'Amount cannot be negative.'}, status=400)
            if charge_type == 'percentage' and (amount < 0 or amount > 100):
                return JsonResponse({'status': 'error', 'message': 'Percentage rate must be between 0 and 100.'}, status=400)

            cap_raw = request.POST.get('cap', '').strip()
            cap = float(cap_raw) if cap_raw and charge_type == 'percentage' else None

            min_raw = request.POST.get('min_transaction_amount', '').strip()
            min_amt = float(min_raw) if min_raw else 0.0

            max_raw = request.POST.get('max_transaction_amount', '').strip()
            max_amt = float(max_raw) if max_raw else None

            if max_amt is not None and max_amt < min_amt:
                return JsonResponse({'status': 'error', 'message': 'Maximum transaction amount cannot be less than minimum amount.'}, status=400)

        except (ValueError, TypeError) as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid numeric value: {str(e)}'}, status=400)

        block_if_insufficient = request.POST.get('block_if_insufficient') in ('true', 'on', '1')
        is_active = request.POST.get('is_active') in ('true', 'on', '1')

        charge_id = request.POST.get('charge_id', '').strip()

        if charge_id:
            try:
                charge = TransactionCharge.objects.get(pk=charge_id)
                charge.name = name
                charge.transaction_type = transaction_type
                charge.charge_type = charge_type
                charge.amount = amount
                charge.cap = cap
                charge.min_transaction_amount = min_amt
                charge.max_transaction_amount = max_amt
                charge.block_if_insufficient = block_if_insufficient
                charge.is_active = is_active
                charge.save()
                action_desc = "updated"
            except TransactionCharge.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Charge rule not found.'}, status=404)
        else:
            charge = TransactionCharge.objects.create(
                name=name,
                transaction_type=transaction_type,
                charge_type=charge_type,
                amount=amount,
                cap=cap,
                min_transaction_amount=min_amt,
                max_transaction_amount=max_amt,
                block_if_insufficient=block_if_insufficient,
                is_active=is_active
            )
            action_desc = "created"

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type=f"{action_desc.upper()}_TRANSACTION_CHARGE",
            target_model="TransactionCharge",
            target_id=str(charge.pk),
            description=f"{action_desc.capitalize()} transaction charge: {charge.name} ({charge.get_transaction_type_display()})"
        )

        return JsonResponse({'status': 'success', 'message': f"Transaction charge rule '{charge.name}' {action_desc} successfully."})

