import logging
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from custom_admin.mixins import PortalPermissionMixin
from users.models import User
from orders.models import (
    Purchase, AirtimeNetwork, DataService, DataVariation, TVService, TVVariation,
    ElectricityService, ElectricityVariation, InternetService, InternetVariation,
    EducationService, EducationVariation
)
from orders.utils.purchase_logic import (
    purchase_airtime, purchase_data, purchase_tv, purchase_electricity,
    purchase_internet, purchase_education
)
from orders.views.utility_views import generate_request_id
from orders.router import ProviderRouter
from wallet.models import Wallet, WalletTransaction
from admin_api.models import AdminActionLog

logger = logging.getLogger(__name__)


class PurchaseListView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'view')

    def get(self, request):
        from orders.models import VTUProviderConfig

        qs = Purchase.objects.all().select_related('user', 'provider')

        purchase_type = request.GET.get('type')
        if purchase_type:
            qs = qs.filter(purchase_type=purchase_type.lower())

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.lower())

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        start_date = request.GET.get('start_date', '').strip()
        if start_date:
            qs = qs.filter(time__date__gte=start_date)

        end_date = request.GET.get('end_date', '').strip()
        if end_date:
            qs = qs.filter(time__date__lte=end_date)

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(beneficiary__icontains=search) |
                Q(user__phone_number__icontains=search)
            )

        sort = request.GET.get('sort', 'date_desc')
        sort_map = {
            'date': 'time', 'date_desc': '-time',
            'amount': 'amount', 'amount_desc': '-amount',
            'profit': 'profit', 'profit_desc': '-profit',
        }
        qs = qs.order_by(sort_map.get(sort, '-time'))

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

        providers = VTUProviderConfig.objects.all()

        return render(request, 'custom_admin/purchases/list.html', {
            'purchases': page_obj,
            'providers': providers,
            'search_query': search or '',
            'type_filter': purchase_type or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'start_date': start_date or '',
            'end_date': end_date or '',
            'sort_query': sort or 'date_desc',
            'per_page': per_page,
        })


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


class ManualPurchaseView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'manual_purchase')

    def get(self, request):
        target_phone = request.GET.get('user', '')
        services = [
            {'code': 'airtime', 'name': 'Airtime Top-up'},
            {'code': 'data', 'name': 'Data Bundle'},
            {'code': 'tv', 'name': 'Cable TV Subscription'},
            {'code': 'electricity', 'name': 'Electricity Token / Bill'},
            {'code': 'internet', 'name': 'Internet Data'},
            {'code': 'education', 'name': 'Education Pin (WAEC/JAMB)'},
        ]
        return render(request, 'custom_admin/purchases/manual_purchase.html', {
            'target_phone': target_phone,
            'services': services
        })

    def post(self, request):
        try:
            admin_pin = request.POST.get('admin_pin', '').strip()
            if not admin_pin:
                return JsonResponse({'status': 'error', 'message': 'Admin Security PIN is required.'}, status=400)

            is_pin_valid = request.user.check_transaction_pin(admin_pin) or request.user.check_password(admin_pin)
            if not is_pin_valid:
                return JsonResponse({'status': 'error', 'message': 'Invalid Admin Security PIN.'}, status=403)

            source_phone = request.POST.get('phone_number', '').strip()
            purchase_type = request.POST.get('purchase_type', '').strip().lower()
            service_id = request.POST.get('service_id')
            variation_id = request.POST.get('variation_id')
            beneficiary = request.POST.get('beneficiary', '').strip()
            amount_str = request.POST.get('amount', '0').strip()

            user_obj = User.objects.filter(phone_number=source_phone).first()
            if not user_obj:
                return JsonResponse({'status': 'error', 'message': f'Source user with phone {source_phone} not found.'}, status=404)

            if not purchase_type:
                return JsonResponse({'status': 'error', 'message': 'Please select a service type.'}, status=400)

            if not beneficiary:
                return JsonResponse({'status': 'error', 'message': 'Recipient identifier (phone/meter/smartcard number) is required.'}, status=400)

            try:
                amount = Decimal(amount_str)
                if amount <= 0:
                    raise ValueError
            except (ValueError, InvalidOperation):
                return JsonResponse({'status': 'error', 'message': 'Amount must be greater than 0.'}, status=400)

            reference = generate_request_id()
            result = None

            if purchase_type == 'airtime':
                if not service_id:
                    return JsonResponse({'status': 'error', 'message': 'Please select a network provider.'}, status=400)
                try:
                    network_obj = AirtimeNetwork.objects.get(pk=service_id, is_active=True)
                except AirtimeNetwork.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Selected airtime network not found or is inactive.'}, status=400)
                result = purchase_airtime(
                    user=user_obj,
                    network=network_obj,
                    phone=beneficiary,
                    amount=amount,
                    reference=reference,
                    initiator='admin',
                    initiated_by=request.user,
                )

            elif purchase_type == 'data':
                if not variation_id:
                    return JsonResponse({'status': 'error', 'message': 'Please select a data plan.'}, status=400)
                try:
                    data_var = DataVariation.objects.get(pk=variation_id, is_active=True)
                except DataVariation.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Selected data plan not found or is inactive.'}, status=400)
                result = purchase_data(
                    user=user_obj,
                    plan=data_var,
                    phone=beneficiary,
                    reference=reference,
                    initiator='admin',
                    initiated_by=request.user,
                )

            elif purchase_type == 'tv':
                if not variation_id:
                    return JsonResponse({'status': 'error', 'message': 'Please select a TV package.'}, status=400)
                try:
                    tv_var = TVVariation.objects.get(pk=variation_id, is_active=True)
                except TVVariation.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Selected TV package not found or is inactive.'}, status=400)
                result = purchase_tv(
                    user=user_obj,
                    tv_variation=tv_var,
                    customer_id=beneficiary,
                    reference=reference,
                    initiator='admin',
                    initiated_by=request.user,
                )

            elif purchase_type == 'electricity':
                if not service_id:
                    return JsonResponse({'status': 'error', 'message': 'Please select an electricity disco provider.'}, status=400)
                # Resolve variation: prefer selected, else first for disco
                elec_var = None
                if variation_id:
                    elec_var = ElectricityVariation.objects.filter(pk=variation_id, is_active=True).first()
                if not elec_var:
                    elec_var = ElectricityVariation.objects.filter(service_id=service_id, is_active=True).first()
                if not elec_var:
                    return JsonResponse({'status': 'error', 'message': 'No active electricity variation found for this provider.'}, status=400)
                result = purchase_electricity(
                    user=user_obj,
                    electricity_variation=elec_var,
                    meter_number=beneficiary,
                    amount=amount,
                    reference=reference,
                    initiator='admin',
                    initiated_by=request.user,
                )

            elif purchase_type == 'internet':
                if not variation_id:
                    return JsonResponse({'status': 'error', 'message': 'Please select an internet plan.'}, status=400)
                try:
                    net_var = InternetVariation.objects.get(pk=variation_id, is_active=True)
                except InternetVariation.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Selected internet plan not found or is inactive.'}, status=400)
                result = purchase_internet(
                    user=user_obj,
                    internet_variation=net_var,
                    phone=beneficiary,
                    reference=reference,
                    initiator='admin',
                    initiated_by=request.user,
                )

            elif purchase_type == 'education':
                if not variation_id:
                    return JsonResponse({'status': 'error', 'message': 'Please select an education package.'}, status=400)
                try:
                    edu_var = EducationVariation.objects.get(pk=variation_id, is_active=True)
                except EducationVariation.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Selected education package not found or is inactive.'}, status=400)
                result = purchase_education(
                    user=user_obj,
                    education_variation=edu_var,
                    phone=beneficiary,
                    quantity=int(request.POST.get('quantity', 1)),
                    reference=reference,
                    initiator='admin',
                    initiated_by=request.user,
                )

            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid purchase type.'}, status=400)

            res_status = result.get('status')
            if res_status in ['success', 'SUCCESS', 'ORDER_RECEIVED']:
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type=f"MANUAL_{purchase_type.upper()}_PURCHASE",
                    target_model="Purchase",
                    target_id=str(result.get('purchase_id', '')),
                    description=f"Manual {purchase_type} purchase of \u20a6{amount} for user {user_obj.phone_number} (Beneficiary: {beneficiary})."
                )
                return JsonResponse({
                    'status': 'success',
                    'message': f"Manual {purchase_type.capitalize()} purchase of \u20a6{amount:,.2f} completed successfully for {beneficiary}."
                })
            else:
                err_msg = result.get('error') or result.get('message') or 'Manual purchase failed.'
                return JsonResponse({'status': 'error', 'message': err_msg}, status=400)

        except Exception as e:
            logger.exception("ManualPurchaseView: unexpected server error — %s", e)
            return JsonResponse(
                {'status': 'error', 'message': f'Server error: {str(e)}'},
                status=500
            )


class ManualPurchaseOptionsView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'view')

    def get(self, request):
        from orders.models import ServiceRouting, ServiceFallback
        purchase_type = request.GET.get('purchase_type', '').strip().lower()
        service_id = request.GET.get('service_id')

        providers = []
        variations = []

        def _get_name(obj):
            return getattr(obj, 'service_name', getattr(obj, 'name', str(obj)))

        def _routed_provider_ids(service_key):
            """
            Return set of VTUProviderConfig PKs in the active routing chain
            (primary + enabled fallbacks) for the given service.
            Returns None when no routing exists so callers can skip filtering.
            """
            routing = ServiceRouting.objects.filter(service=service_key).first()
            if not routing:
                return None
            ids = set()
            if routing.primary_provider_id and routing.primary_provider.is_active:
                ids.add(routing.primary_provider_id)
            if routing.fallback_enabled:
                fb_ids = (
                    ServiceFallback.objects
                    .filter(service_routing=routing, provider__is_active=True)
                    .values_list('provider_id', flat=True)
                )
                ids.update(fb_ids)
            return ids

        if purchase_type == 'airtime':
            routed_ids = _routed_provider_ids('airtime')
            qs = AirtimeNetwork.objects.filter(is_active=True)
            if routed_ids is not None:
                qs = qs.filter(provider_id__in=routed_ids)
            providers = [{'id': obj.id, 'name': _get_name(obj)} for obj in qs]

        elif purchase_type == 'data':
            if service_id:
                vars_qs = DataVariation.objects.filter(service_id=service_id, is_active=True)
                variations = [{'id': v.id, 'name': f"{v.name} - \u20a6{v.selling_price:,.2f}", 'price': float(v.selling_price)} for v in vars_qs]
            else:
                routed_ids = _routed_provider_ids('data')
                qs = DataService.objects.filter(is_active=True)
                if routed_ids is not None:
                    qs = qs.filter(provider_id__in=routed_ids)
                providers = [{'id': obj.id, 'name': _get_name(obj)} for obj in qs]

        elif purchase_type == 'tv':
            if service_id:
                vars_qs = TVVariation.objects.filter(service_id=service_id, is_active=True)
                variations = [{'id': v.id, 'name': f"{v.name} - \u20a6{v.selling_price:,.2f}", 'price': float(v.selling_price)} for v in vars_qs]
            else:
                routed_ids = _routed_provider_ids('tv')
                qs = TVService.objects.filter(is_active=True)
                if routed_ids is not None:
                    qs = qs.filter(provider_id__in=routed_ids)
                providers = [{'id': obj.id, 'name': _get_name(obj)} for obj in qs]

        elif purchase_type == 'electricity':
            if service_id:
                vars_qs = ElectricityVariation.objects.filter(service_id=service_id, is_active=True)
                variations = [{'id': v.id, 'name': v.name, 'price': float(v.selling_price) if v.selling_price > 0 else 0} for v in vars_qs]
            else:
                routed_ids = _routed_provider_ids('electricity')
                qs = ElectricityService.objects.filter(is_active=True)
                if routed_ids is not None:
                    qs = qs.filter(provider_id__in=routed_ids)
                providers = [{'id': obj.id, 'name': _get_name(obj)} for obj in qs]

        elif purchase_type == 'internet':
            if service_id:
                vars_qs = InternetVariation.objects.filter(service_id=service_id, is_active=True)
                variations = [{'id': v.id, 'name': f"{v.name} - \u20a6{v.selling_price:,.2f}", 'price': float(v.selling_price)} for v in vars_qs]
            else:
                routed_ids = _routed_provider_ids('internet')
                qs = InternetService.objects.filter(is_active=True)
                if routed_ids is not None:
                    qs = qs.filter(provider_id__in=routed_ids)
                providers = [{'id': obj.id, 'name': _get_name(obj)} for obj in qs]

        elif purchase_type == 'education':
            if service_id:
                vars_qs = EducationVariation.objects.filter(service_id=service_id, is_active=True)
                variations = [{'id': v.id, 'name': f"{v.name} - \u20a6{v.selling_price:,.2f}", 'price': float(v.selling_price)} for v in vars_qs]
            else:
                routed_ids = _routed_provider_ids('education')
                qs = EducationService.objects.filter(is_active=True)
                if routed_ids is not None:
                    qs = qs.filter(provider_id__in=routed_ids)
                providers = [{'id': obj.id, 'name': _get_name(obj)} for obj in qs]

        return JsonResponse({
            'status': 'success',
            'providers': providers,
            'variations': variations
        })



class ManualRecipientVerifyView(PortalPermissionMixin, View):
    required_permission = ('orders.Purchase', 'view')

    def get(self, request):
        purchase_type = request.GET.get('purchase_type', '').strip().lower()
        service_id = request.GET.get('service_id', '')
        customer_id = request.GET.get('customer_id', '').strip()

        if not customer_id:
            return JsonResponse({'status': 'error', 'message': 'Recipient customer ID is required.'}, status=400)

        service_name = ''
        if purchase_type == 'tv' and service_id:
            s_obj = TVService.objects.filter(id=service_id).first()
            if s_obj: service_name = s_obj.name
        elif purchase_type == 'electricity' and service_id:
            s_obj = ElectricityService.objects.filter(id=service_id).first()
            if s_obj: service_name = s_obj.name

        try:
            if purchase_type == 'tv':
                action = 'validate_cable_id'
                kwargs = {'card_number': customer_id, 'service': service_name or service_id}
            elif purchase_type == 'electricity':
                action = 'validate_meter'
                kwargs = {'meter_number': customer_id, 'service': service_name or service_id}
            elif purchase_type == 'internet':
                action = 'verify_internet'
                kwargs = {'accountID': customer_id}
            else:
                return JsonResponse({'status': 'success', 'name': customer_id})

            res = ProviderRouter.execute_with_fallback(purchase_type, action, **kwargs)
            if res.get('status') in ['SUCCESS', 'ORDER_RECEIVED']:
                account_name = res.get('account_name') or res.get('customer_name') or res.get('name') or 'Verified Customer'
                return JsonResponse({'status': 'success', 'name': account_name, 'raw': res})
            else:
                err = res.get('message') or res.get('error') or 'Could not verify recipient details.'
                return JsonResponse({'status': 'error', 'message': err}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Verification error: {str(e)}'}, status=400)
