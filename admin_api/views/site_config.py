from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema_view, extend_schema
from summary.models import SiteConfig, ServiceCashback
from admin_api.serializers import AdminSiteConfigSerializer, ServiceCashbackSerializer
from admin_api.permissions import CanManageSiteConfig, IsSuperUserOnly
from admin_api.utils import log_admin_action

@extend_schema_view(
    list=extend_schema(tags=["Admin Site Configuration"]),
    retrieve=extend_schema(tags=["Admin Site Configuration"]),
    create=extend_schema(tags=["Admin Site Configuration"]),
    update=extend_schema(tags=["Admin Site Configuration"]),
    partial_update=extend_schema(tags=["Admin Site Configuration"]),
)
class AdminSiteConfigViewSet(viewsets.ModelViewSet):
    """
    Manage global site configurations including charges, referrals, and bonuses.
    """
    queryset = SiteConfig.objects.all()
    serializer_class = AdminSiteConfigSerializer
    permission_classes = [CanManageSiteConfig]

    def get_object(self):
        # Override to always return the singleton object
        obj, created = SiteConfig.objects.get_or_create(pk=1)
        return obj

    @extend_schema(
        summary="Fetch Global Site Config",
        description="Returns the singleton SiteConfig instance."
    )
    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_admin_action(
            user=self.request.user,
            action_type="UPDATE_SITE_CONFIG",
            description=f"Updated global site configuration.",
            target=instance,
            metadata=serializer.data
        )

@extend_schema_view(
    list=extend_schema(tags=["Admin Site Configuration"]),
    retrieve=extend_schema(tags=["Admin Site Configuration"]),
    create=extend_schema(tags=["Admin Site Configuration"]),
    update=extend_schema(tags=["Admin Site Configuration"]),
    partial_update=extend_schema(tags=["Admin Site Configuration"]),
)
class AdminServiceCashbackViewSet(viewsets.ModelViewSet):
    """
    Manage service-specific cashback rules.
    """
    queryset = ServiceCashback.objects.all()
    serializer_class = ServiceCashbackSerializer
    permission_classes = [CanManageSiteConfig]


from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from wallet.models import TransactionCharge
from wallet.utils import calculate_total_charges
from admin_api.serializers import (
    TransactionChargeSerializer,
    TransactionChargeCalculateRequestSerializer,
    TransactionChargeCalculateResponseSerializer,
    AdminErrorResponseSerializer
)

@extend_schema_view(
    list=extend_schema(tags=["Admin Site Configuration"]),
    retrieve=extend_schema(tags=["Admin Site Configuration"]),
    create=extend_schema(tags=["Admin Site Configuration"]),
    update=extend_schema(tags=["Admin Site Configuration"]),
    partial_update=extend_schema(tags=["Admin Site Configuration"]),
    destroy=extend_schema(tags=["Admin Site Configuration"]),
)
class AdminTransactionChargeViewSet(viewsets.ModelViewSet):
    """
    Manage fee and charge rules for transactions (deposit, withdrawal, transfers).
    """
    queryset = TransactionCharge.objects.all().order_by('transaction_type', '-created_at')
    serializer_class = TransactionChargeSerializer
    permission_classes = [CanManageSiteConfig]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'charge_type', 'is_active', 'block_if_insufficient']
    search_fields = ['name', 'transaction_type']
    ordering_fields = ['created_at', 'amount', 'min_transaction_amount']

    @extend_schema(
        tags=["Admin Site Configuration"],
        summary="Calculate and preview charges",
        description="Calculate and preview applicable charges for a given transaction type and amount.",
        request=TransactionChargeCalculateRequestSerializer,
        responses={200: TransactionChargeCalculateResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate(self, request):
        serializer = TransactionChargeCalculateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        txn_type = serializer.validated_data['transaction_type']
        amount = serializer.validated_data['amount']

        total_charge, breakdown = calculate_total_charges(txn_type, amount)
        net_amount = amount - total_charge if txn_type == 'withdrawal' else amount + total_charge

        return Response({
            "transaction_type": txn_type,
            "amount": amount,
            "charges": breakdown,
            "total_charge": total_charge,
            "net_amount": net_amount
        })

    def perform_create(self, serializer):
        instance = serializer.save()
        log_admin_action(
            user=self.request.user,
            action_type="CREATE_TRANSACTION_CHARGE",
            description=f"Created transaction charge rule: {instance.name} for {instance.transaction_type}",
            target=instance,
            metadata=serializer.data
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_admin_action(
            user=self.request.user,
            action_type="UPDATE_TRANSACTION_CHARGE",
            description=f"Updated transaction charge rule: {instance.name}",
            target=instance,
            metadata=serializer.data
        )

    def perform_destroy(self, instance):
        name = instance.name
        instance.delete()
        log_admin_action(
            user=self.request.user,
            action_type="DELETE_TRANSACTION_CHARGE",
            description=f"Deleted transaction charge rule: {name}",
            target=None
        )

