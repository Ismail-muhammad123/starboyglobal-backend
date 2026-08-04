from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from summary.models import SiteConfig
from orders.models import ServiceRouting, Purchase
from admin_api.serializers import (
    AutomationOverviewResponseSerializer,
    AutomationGlobalSettingsSerializer,
    ServiceAutomationConfigSerializer,
    ServiceRetryConfigSerializer,
    ServicePricingModeSerializer,
    AdminStatusResponseSerializer,
)
from admin_api.permissions import CanManageSiteConfig
from django.utils import timezone
from datetime import timedelta

class AutomationConfigView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Get global and per-service automation configuration",
        responses={200: AutomationOverviewResponseSerializer}
    )
    def get(self, request):
        config = SiteConfig.objects.first()
        services = ServiceRouting.objects.all()
        
        data = {
            "global_settings": {
                "auto_retry_enabled": config.auto_retry_enabled,
                "auto_refund_enabled": config.auto_refund_enabled,
                "notify_admin_on_failure": config.notify_admin_on_failure,
                "delayed_tx_detection_enabled": config.delayed_tx_detection_enabled,
                "delayed_tx_timeout_minutes": config.delayed_tx_timeout_minutes,
            },
            "services": ServiceAutomationConfigSerializer(services, many=True).data
        }
        return Response(data)

class AutomationGlobalSettingsView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Update global automation settings",
        request=AutomationGlobalSettingsSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        serializer = AutomationGlobalSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        config = SiteConfig.objects.first()
        for field, value in serializer.validated_data.items():
            setattr(config, field, value)
        config.save()
        
        return Response({"status": "SUCCESS", "message": "Global automation settings updated."})

class ServiceRetryConfigView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Update retry configuration for a specific service",
        request=ServiceRetryConfigSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, service):
        routing = ServiceRouting.objects.filter(service=service).first()
        if not routing:
            return Response({"error": "Service not found"}, status=404)
        
        serializer = ServiceRetryConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        routing.retry_enabled = serializer.validated_data['enabled']
        routing.retry_count = serializer.validated_data['count']
        routing.save()
        
        return Response({"status": "SUCCESS", "message": f"Retry config for {service} updated."})

class ServiceFallbackToggleView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Enable/disable fallback for a specific service",
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, service):
        routing = ServiceRouting.objects.filter(service=service).first()
        if not routing:
            return Response({"error": "Service not found"}, status=404)
        
        enabled = request.data.get('enabled', not routing.fallback_enabled)
        routing.fallback_enabled = enabled
        routing.save()
        
        status_text = "enabled" if enabled else "disabled"
        return Response({"status": "SUCCESS", "message": f"Fallback {status_text} for {service}."})

class ServiceAutoRefundView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Enable/disable auto-refund for a specific service",
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, service):
        routing = ServiceRouting.objects.filter(service=service).first()
        if not routing:
            return Response({"error": "Service not found"}, status=404)
        
        enabled = request.data.get('enabled', not routing.auto_refund_enabled)
        routing.auto_refund_enabled = enabled
        routing.save()
        
        status_text = "enabled" if enabled else "disabled"
        return Response({"status": "SUCCESS", "message": f"Auto-refund {status_text} for {service}."})

class ServicePricingModeView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Update pricing mode and margins for a service",
        request=ServicePricingModeSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request, service):
        routing = ServiceRouting.objects.filter(service=service).first()
        if not routing:
            return Response({"error": "Service not found"}, status=404)
        
        serializer = ServicePricingModeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mode = serializer.validated_data['mode']
        
        # User requirement: "not enabled unless those values are defined"
        if mode == 'fixed_margin':
            if 'customer_margin' not in serializer.validated_data or 'agent_margin' not in serializer.validated_data:
                return Response({"error": "Customer and Agent margins are required for fixed_margin mode"}, status=400)
            routing.customer_margin = serializer.validated_data['customer_margin']
            routing.agent_margin = serializer.validated_data['agent_margin']

        routing.pricing_mode = mode
        routing.save()
        
        return Response({"status": "SUCCESS", "message": f"Pricing mode for {service} set to {mode}."})

class DetectDelayedTransactionsView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Manually trigger detection of delayed transactions",
        responses={200: serializers.ListField(child=serializers.DictField())}
    )
    def post(self, request):
        config = SiteConfig.objects.first()
        timeout = config.delayed_tx_timeout_minutes
        cutoff_time = timezone.now() - timedelta(minutes=timeout)
        
        delayed = Purchase.objects.filter(
            status='pending',
            time__lt=cutoff_time
        )
        
        results = []
        for p in delayed:
            results.append({
                "id": p.id,
                "ref": p.reference,
                "type": p.purchase_type,
                "beneficiary": p.beneficiary,
                "time": p.time,
                "minutes_since": int((timezone.now() - p.time).total_seconds() / 60)
            })
            
        return Response(results)


from rest_framework import viewsets
from orders.models import ProviderServiceConfig
from admin_api.serializers import ProviderServiceConfigSerializer, AutoSyncConfigSerializer

class ProviderServiceConfigViewSet(viewsets.ModelViewSet):
    """Manage per-provider, per-service catalogue source and margins."""
    queryset = ProviderServiceConfig.objects.all()
    serializer_class = ProviderServiceConfigSerializer
    permission_classes = [CanManageSiteConfig]
    filterset_fields = ['provider', 'service_type', 'catalogue_source']


class AutoSyncConfigView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Get auto-sync configuration and status",
        responses={200: AutoSyncConfigSerializer}
    )
    def get(self, request):
        config, _ = SiteConfig.objects.get_or_create(pk=1)
        return Response(AutoSyncConfigSerializer(config).data)

    @extend_schema(
        tags=["Admin Automation"],
        summary="Update auto-sync configuration",
        request=AutoSyncConfigSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        config, _ = SiteConfig.objects.get_or_create(pk=1)
        serializer = AutoSyncConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update running scheduler dynamically
        from orders.scheduler import update_scheduler_config
        update_scheduler_config()

        return Response({"status": "SUCCESS", "message": "Auto-sync configuration updated."})


class AutoSyncRunNowView(APIView):
    permission_classes = [CanManageSiteConfig]

    @extend_schema(
        tags=["Admin Automation"],
        summary="Manually trigger immediate plans/networks sync for active providers",
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        from django.core.management import call_command
        try:
            call_command('sync_provider_plans')
            return Response({"status": "SUCCESS", "message": "Provider plans sync completed."})
        except Exception as e:
            return Response({"status": "FAILED", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

