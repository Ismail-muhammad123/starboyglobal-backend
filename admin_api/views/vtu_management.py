from rest_framework import viewsets, status, filters, serializers

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema_view, extend_schema
from users.models import User
from orders.models import (
    Purchase, VTUProviderConfig, ServiceRouting, 
    DataVariation, AirtimeNetwork, TVVariation, 
    InternetVariation, EducationVariation, ElectricityVariation,
    DataService, TVService, ElectricityService, InternetService, EducationService
)
from admin_api.serializers import (
    AdminPurchaseSerializer, VTUProviderConfigSerializer,
    ServiceRoutingSerializer, AdminCreatePurchaseRequestSerializer,
    AdminStatusResponseSerializer, AdminErrorResponseSerializer,
    VTUOverviewResponseSerializer, FetchFromProviderRequestSerializer,
    VariationPriceUpdateSerializer, BulkVariationPriceUpdateSerializer,
    VariationToggleSerializer, ServiceTypeToggleSerializer,
    ProviderFundingConfigSerializer, AvailableVTUProviderSerializer
)
from admin_api.permissions import CanManageVTU
from orders.router import ProviderRouter
from wallet.utils import fund_wallet
from django.db.models import Count, Avg, F
from django.db import transaction

@extend_schema_view(
    list=extend_schema(tags=["Admin Purchases"]),
    retrieve=extend_schema(tags=["Admin Purchases"]),
)
class AdminPurchaseViewSet(viewsets.ModelViewSet):
    """View and manage all purchases (VTU transactions) in the system."""
    queryset = Purchase.objects.select_related('user').all().order_by('-time')
    serializer_class = AdminPurchaseSerializer
    permission_classes = [CanManageVTU]

    def get_queryset(self):
        # Return all purchase records system-wide
        return self.queryset

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact', 'in'],
        'purchase_type': ['exact'],
        'time': ['exact', 'gte', 'lte', 'gt', 'lt'],
        'user': ['exact'],
    }
    search_fields = ['reference', 'beneficiary', 'user__email', 'user__phone_number']
    ordering_fields = ['time', 'amount']

    @extend_schema(
        tags=["Admin Purchases"],
        summary="Initiate a purchase for a user",
        request=AdminCreatePurchaseRequestSerializer,
        responses={200: AdminPurchaseSerializer}
    )
    def create(self, request, *args, **kwargs):
        from orders.utils.purchase_logic import process_vtu_purchase
        serializer = AdminCreatePurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        purchase_type = serializer.validated_data['purchase_type']
        amount = serializer.validated_data['amount']
        beneficiary = serializer.validated_data['beneficiary']
        action_name = serializer.validated_data['action']
        
        # New fields for granular control
        plan_id = serializer.validated_data.get('plan_id')
        service_id = serializer.validated_data.get('service_id')
        network_id = serializer.validated_data.get('network_id')
        pin = serializer.validated_data['pin']

        if not request.user.check_password(pin):
            return Response({"error": "Invalid authorization PIN"}, status=status.HTTP_403_FORBIDDEN)
        
        user = User.objects.get(id=user_id)
        
        purchase_kwargs = {}
        if plan_id: purchase_kwargs['plan_id'] = plan_id
        if service_id: purchase_kwargs['service_id'] = service_id
        if network_id: purchase_kwargs['network_id'] = network_id
        
        res = process_vtu_purchase(
            user=user,
            purchase_type=purchase_type,
            amount=amount,
            beneficiary=beneficiary,
            action=action_name,
            initiator='admin',
            initiated_by=request.user,
            **purchase_kwargs
        )
        return Response(res)

    @extend_schema(
        tags=["Admin Purchases"],
        summary="Retry a failed purchase",
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        pin = request.data.get('pin')
        if not request.user.check_password(pin):
            return Response({"error": "Invalid authorization PIN"}, status=403)

        purchase = self.get_object()
        if purchase.status != 'failed':
            return Response({"error": "Can only retry failed purchases"}, status=400)
        
        res = ProviderRouter.execute_with_fallback(purchase.purchase_type, f"buy_{purchase.purchase_type}", **purchase.provider_response.get('request_data', {}))
        if res['status'] == 'SUCCESS':
             purchase.status = 'success'
             purchase.save()
        return Response(res)

    @extend_schema(
        tags=["Admin Purchases"],
        summary="Refund a purchase to user wallet",
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        purchase = self.get_object()
        if purchase.status == 'refunded':
             return Response({"error": "Already refunded"}, status=400)
        
        fund_wallet(
            purchase.user.id, 
            purchase.amount, 
            description=f"Refund: Manual refund for purchase {purchase.reference}",
            initiator='admin',
            initiated_by=request.user
        )
        purchase.status = 'refunded'
        purchase.save(update_fields=["status"])
        return Response({"status": "SUCCESS", "message": "Purchase refunded to user wallet."})

    @extend_schema(
        tags=["Admin Purchases"],
        summary="Cancel a pending purchase",
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        pin = request.data.get('pin')
        if not request.user.check_password(pin):
            return Response({"error": "Invalid authorization PIN"}, status=403)

        purchase = self.get_object()
        if purchase.status != 'pending':
            return Response({"error": "Can only cancel pending purchases"}, status=400)
        
        purchase.status = 'refunded'
        purchase.save(update_fields=["status"])
        
        fund_wallet(
            purchase.user.id, 
            purchase.amount, 
            description=f"Refund: Purchase {purchase.reference} cancelled by Admin",
            initiator='admin',
            initiated_by=request.user
        )
        return Response({"status": "SUCCESS", "message": "Purchase cancelled and refunded."})

class VTUOverviewView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Get consolidated VTU services and providers overview",
        responses={200: VTUOverviewResponseSerializer}
    )
    def get(self, request):
        providers = VTUProviderConfig.objects.all()
        # Fetch actual balances for active providers
        provider_data = []
        for p in providers:
            balance = 0.0
            if p.is_active:
                impl = ProviderRouter.get_provider_implementation(p.name)
                if impl:
                    try:
                        balance = impl.get_wallet_balance()
                    except:
                        pass
            
            p_dict = VTUProviderConfigSerializer(p).data
            p_dict['balance'] = balance
            provider_data.append(p_dict)
            
        services_list = ['airtime', 'data', 'tv', 'electricity', 'internet', 'education']
        summary = []
        
        for st in services_list:
            routing = ServiceRouting.objects.filter(service=st).first()
            # Success rates from last 100 txs
            txs = list(Purchase.objects.filter(purchase_type=st).order_by('-time')[:100])
            success_rate = 0
            if len(txs) > 0:
                successes = sum(1 for tx in txs if tx.status == 'success')
                success_rate = successes / len(txs)
            
            summary.append({
                "service": st,
                "is_active": True, # Placeholder or from SiteConfig
                "routing": ServiceRoutingSerializer(routing).data if routing else None,
                "success_rate": success_rate,
                "total_variations": self._get_variation_count(st)
            })
            
        return Response({
            "providers": provider_data,
            "services_summary": summary
        })

    def _get_variation_count(self, service_type):
        models_map = {
            'data': DataVariation, 'airtime': AirtimeNetwork, 'tv': TVVariation,
            'electricity': ElectricityVariation, 'internet': InternetVariation, 'education': EducationVariation
        }
        model = models_map.get(service_type)
        return model.objects.count() if model else 0

class ProviderBalanceView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Fetch real-time balance for a specific provider",
        responses={200: {"balance": 0.0}}
    )
    def get(self, request, pk):
        try:
            provider = VTUProviderConfig.objects.get(pk=pk)
        except VTUProviderConfig.DoesNotExist:
            return Response({"error": "Provider not found"}, status=status.HTTP_404_NOT_FOUND)
        impl = ProviderRouter.get_provider_implementation(provider.name)
        if not impl:
            return Response({"error": "Implementation not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        balance = impl.get_wallet_balance()
        return Response({"balance": balance})

class FetchFromProviderView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Fetch services/variations from provider API and save to local DB",
        request=FetchFromProviderRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        serializer = FetchFromProviderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider_id = serializer.validated_data['provider_id']
        service_type = serializer.validated_data['service_type']
        
        provider = VTUProviderConfig.objects.get(id=provider_id)
        impl = ProviderRouter.get_provider_implementation(provider.name)
        if not impl:
            return Response({"error": "Implementation not found"}, status=400)
            
        count = 0
        if service_type == 'data': count = impl.sync_data()
        elif service_type == 'airtime': count = impl.sync_airtime()
        elif service_type == 'tv': count = impl.sync_cable()
        elif service_type == 'electricity': count = impl.sync_electricity()
        elif service_type == 'internet': count = impl.sync_internet()
        elif service_type == 'education': count = impl.sync_education()
        
        return Response({"status": "SUCCESS", "message": f"Successfully synced {count} {service_type} from {provider.name}"})


class LiveCataloguePreviewView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Preview live catalogue items from provider API with margin calculation per role",
        responses={200: serializers.ListField(child=serializers.DictField())}
    )
    def get(self, request):
        provider_id = request.query_params.get('provider_id')
        service_type = request.query_params.get('service_type')
        user_role = request.query_params.get('role', 'customer')

        if not provider_id or not service_type:
            return Response({"error": "provider_id and service_type query params are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider = VTUProviderConfig.objects.get(id=provider_id)
        except VTUProviderConfig.DoesNotExist:
            return Response({"error": "Provider not found"}, status=status.HTTP_404_NOT_FOUND)

        impl = ProviderRouter.get_provider_implementation(provider.name)
        if not impl:
            return Response({"error": "Provider implementation not found"}, status=status.HTTP_400_BAD_REQUEST)

        method_name = f"fetch_{service_type}_live"
        fetch_func = getattr(impl, method_name, None)
        if not fetch_func:
            return Response({"error": f"Live fetch not supported for service_type {service_type}"}, status=status.HTTP_400_BAD_REQUEST)

        from orders.utils.pricing import get_provider_service_config, resolve_margin_for_role, apply_margin
        config = get_provider_service_config(provider, service_type)
        margin_type, margin_value = resolve_margin_for_role(config, user_role)

        raw_items = fetch_func()
        priced_items = []
        for item in raw_items:
            item_copy = dict(item)
            cost_price = item_copy.get('cost_price', 0.0)
            selling_price = float(apply_margin(cost_price, margin_value, margin_type))
            item_copy['cost_price'] = float(cost_price)
            item_copy['selling_price'] = selling_price
            item_copy['customer_price'] = float(apply_margin(cost_price, config.get('customer_margin_value', 0), config.get('customer_margin_type', 'flat')))
            item_copy['agent_price'] = float(apply_margin(cost_price, config.get('agent_margin_value', 0), config.get('agent_margin_type', 'flat')))
            item_copy['developer_price'] = float(apply_margin(cost_price, config.get('developer_margin_value', 0), config.get('developer_margin_type', 'flat')))
            priced_items.append(item_copy)

        return Response({
            "provider": provider.get_name_display(),
            "service_type": service_type,
            "role_preview": user_role,
            "margin_applied": {"type": margin_type, "value": float(margin_value)},
            "total_items": len(priced_items),
            "items": priced_items
        })


class VariationUpdatePriceView(APIView):

    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Update pricing for a specific variation",
        request=VariationPriceUpdateSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, pk, service_type):
        models_map = {
            'data': DataVariation, 'airtime': AirtimeNetwork, 'tv': TVVariation,
            'electricity': ElectricityVariation, 'internet': InternetVariation, 'education': EducationVariation
        }
        model = models_map.get(service_type)
        if not model: return Response({"error": "Invalid service type"}, status=400)
        
        variation = model.objects.get(pk=pk)
        serializer = VariationPriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        for field in ['selling_price', 'agent_price', 'developer_price']:
            if field in serializer.validated_data:
                setattr(variation, field, serializer.validated_data[field])
        variation.save()
        
        return Response({"status": "SUCCESS", "message": "Price updated."})

class BulkVariationUpdatePriceView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Bulk update prices for multiple variations",
        request=BulkVariationPriceUpdateSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, service_type):
        models_map = {
            'data': DataVariation, 'airtime': AirtimeNetwork, 'tv': TVVariation,
            'electricity': ElectricityVariation, 'internet': InternetVariation, 'education': EducationVariation
        }
        model = models_map.get(service_type)
        if not model: return Response({"error": "Invalid service type"}, status=400)
        
        serializer = BulkVariationPriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            for item in serializer.validated_data['variations']:
                update_fields = {}
                for field in ['selling_price', 'agent_price', 'developer_price']:
                    if field in item:
                        update_fields[field] = item[field]
                if update_fields:
                    model.objects.filter(id=item['id']).update(**update_fields)
        
        return Response({"status": "SUCCESS", "message": f"Bulk update for {service_type} variations completed."})

class VariationToggleView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Enable/disable a specific variation",
        request=VariationToggleSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, pk, service_type):
        models_map = {
            'data': DataVariation, 'airtime': AirtimeNetwork, 'tv': TVVariation,
            'electricity': ElectricityVariation, 'internet': InternetVariation, 'education': EducationVariation
        }
        model = models_map.get(service_type)
        variation = model.objects.get(pk=pk)
        
        active = request.data.get('is_active', not variation.is_active)
        variation.is_active = active
        variation.save()
        
        return Response({"status": "SUCCESS", "message": f"Variation {'enabled' if active else 'disabled'}."})

class ServiceTypeToggleView(APIView):
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Control"],
        summary="Enable/disable an entire service type (e.g. data)",
        request=ServiceTypeToggleSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, service_type):
        from summary.models import SiteConfig
        config = SiteConfig.objects.first()
        
        active = request.data.get('is_active')
        field_map = {
            'airtime': 'airtime_active', 'data': 'data_active', 
            'tv': 'tv_active', 'electricity': 'electricity_active',
            'education': 'education_active'
        }
        field = field_map.get(service_type)
        if not field: return Response({"error": "Invalid service type"}, status=400)
        
        setattr(config, field, active)
        config.save()
        
        return Response({"status": "SUCCESS", "message": f"Service type {service_type} {'enabled' if active else 'disabled'}."})

class AdminAvailableVTUProvidersView(APIView):
    """
    Get the list of all officially supported VTU providers from the registry.
    Use this to populate dropdowns when adding new provider configurations.
    """
    permission_classes = [CanManageVTU]

    @extend_schema(
        tags=["Admin VTU Config"],
        summary="List all supported VTU providers from the registry",
        responses={200: AvailableVTUProviderSerializer(many=True)}
    )
    def get(self, request):
        from orders.providers.registry import AVAILABLE_PROVIDERS
        from orders.router import ProviderRouter
        
        data = []
        for p_id, p_name in AVAILABLE_PROVIDERS:
            p_class = ProviderRouter.FACTORIES.get(p_id)
            data.append({
                "id": p_id,
                "name": p_name,
                "supported_services": p_class.get_supported_services() if p_class else [],
                "config_requirements": p_class.get_config_requirements() if p_class else []
            })
        return Response(data)

@extend_schema_view(
    list=extend_schema(tags=["Admin VTU Config"]),
    retrieve=extend_schema(tags=["Admin VTU Config"]),
    create=extend_schema(tags=["Admin VTU Config"]),
    update=extend_schema(tags=["Admin VTU Config"]),
    partial_update=extend_schema(tags=["Admin VTU Config"]),
    destroy=extend_schema(tags=["Admin VTU Config"]),
    available_providers=extend_schema(tags=["Admin VTU Config"], summary="Get list of all supported providers for dropdown selection"),
)
class AdminVTUProviderConfigViewSet(viewsets.ModelViewSet):
    """Manage VTU provider configurations (API keys, base URLs, etc.)."""
    queryset = VTUProviderConfig.objects.all()
    serializer_class = VTUProviderConfigSerializer
    permission_classes = [CanManageVTU]

    def perform_create(self, serializer):
        provider = serializer.save()
        self._auto_create_beneficiary(provider, self.request.user)

    def perform_update(self, serializer):
        provider = serializer.save()
        self._auto_create_beneficiary(provider, self.request.user)

    def _auto_create_beneficiary(self, provider, admin_user):
        """Auto-create a TransferBeneficiary if the provider has complete bank info."""
        from wallet.models import TransferBeneficiary

        if all([provider.bank_name, provider.account_name, provider.account_number, provider.bank_code]):
            TransferBeneficiary.objects.update_or_create(
                user=admin_user,
                bank_code=provider.bank_code,
                account_number=provider.account_number,
                defaults={
                    'bank_name': provider.bank_name,
                    'account_name': provider.account_name,
                    'nickname': provider.get_name_display(),
                }
            )

    @extend_schema(summary="Get list of all supported providers for dropdown selection", responses={200: AvailableVTUProviderSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='available-providers')
    def available_providers(self, request):
        from orders.router import ProviderRouter
        choices = VTUProviderConfig.PROVIDER_CHOICES
        data = []
        for p_id, p_name in choices:
            p_class = ProviderRouter.FACTORIES.get(p_id)
            data.append({
                "id": p_id,
                "name": p_name,
                "supported_services": p_class.get_supported_services() if p_class else [],
                "config_requirements": p_class.get_config_requirements() if p_class else []
            })
        return Response(data)

    @extend_schema(summary="Update provider funding configuration")
    @action(detail=True, methods=['post'], url_path='funding-config')
    def set_funding_config(self, request, pk=None):
        provider = self.get_object()
        serializer = ProviderFundingConfigSerializer(provider, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "SUCCESS", "message": "Funding config updated."})

@extend_schema_view(
    list=extend_schema(tags=["Admin VTU Config"]),
    retrieve=extend_schema(tags=["Admin VTU Config"]),
    create=extend_schema(tags=["Admin VTU Config"]),
    update=extend_schema(tags=["Admin VTU Config"]),
    partial_update=extend_schema(tags=["Admin VTU Config"]),
    destroy=extend_schema(tags=["Admin VTU Config"]),
    available_providers=extend_schema(tags=["Admin VTU Config"], summary="Get list of all supported providers for dropdown selection"),
)
class AdminServiceRoutingViewSet(viewsets.ModelViewSet):
    """Manage service routing (primary provider & fallback chain per service type)."""
    queryset = ServiceRouting.objects.all()
    serializer_class = ServiceRoutingSerializer
    permission_classes = [CanManageVTU]
