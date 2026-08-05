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
        service_type = request.POST.get('service_type')
        cashback_type = request.POST.get('cashback_type', 'flat')
        try:
            cashback_value = float(request.POST.get('cashback_value', 0))
            min_purchase_amount = float(request.POST.get('min_purchase_amount', 0))
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid numeric values.'}, status=400)

        is_active = request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on'

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
