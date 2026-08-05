from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

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


from rest_framework import viewsets, filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from orders.models import ProviderServiceConfig, AutoSyncSchedule, AutoSyncLog
from admin_api.serializers import (
    ProviderServiceConfigSerializer, AutoSyncConfigSerializer,
    AutoSyncScheduleSerializer, AutoSyncLogSerializer
)

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


@extend_schema_view(
    list=extend_schema(tags=["Admin Automation"]),
    retrieve=extend_schema(tags=["Admin Automation"]),
    create=extend_schema(tags=["Admin Automation"]),
    update=extend_schema(tags=["Admin Automation"]),
    partial_update=extend_schema(tags=["Admin Automation"]),
    destroy=extend_schema(tags=["Admin Automation"]),
)
class AutoSyncScheduleViewSet(viewsets.ModelViewSet):
    """
    CRUD management for Auto Sync Jobs.
    Select service type (Airtime, Data, etc.), provider (Ketamency, FlowPay, etc. or All), frequency (daily, weekly, etc.), start time and enable/disable toggle.
    """
    queryset = AutoSyncSchedule.objects.all().order_by('-created_at')
    serializer_class = AutoSyncScheduleSerializer
    permission_classes = [CanManageSiteConfig]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'frequency', 'service_type', 'provider']
    search_fields = ['name']

    def perform_create(self, serializer):
        schedule = serializer.save()
        from orders.scheduler import update_schedule_job
        update_schedule_job(schedule.id)

    def perform_update(self, serializer):
        schedule = serializer.save()
        from orders.scheduler import update_schedule_job
        update_schedule_job(schedule.id)

    def perform_destroy(self, instance):
        schedule_id = instance.id
        instance.delete()
        from orders.scheduler import update_schedule_job
        update_schedule_job(schedule_id)

    @extend_schema(
        tags=["Admin Automation"],
        summary="Enable or disable a specific job schedule",
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle_schedule(self, request, pk=None):
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save(update_fields=['is_active'])

        from orders.scheduler import update_schedule_job
        update_schedule_job(schedule.id)

        status_text = "enabled" if schedule.is_active else "disabled"
        return Response({
            "status": "SUCCESS",
            "message": f"Job schedule '{schedule.name}' is now {status_text}.",
            "is_active": schedule.is_active
        })

    @extend_schema(
        tags=["Admin Automation"],
        summary="Trigger a job schedule run immediately",
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='run-now')
    def run_now(self, request, pk=None):
        schedule = self.get_object()
        from orders.utils.sync_runner import execute_sync_schedule
        execute_sync_schedule(schedule.id)

        latest_log = AutoSyncLog.objects.filter(schedule=schedule).first()
        log_serializer = AutoSyncLogSerializer(latest_log) if latest_log else None

        return Response({
            "status": "SUCCESS",
            "message": f"Immediate execution of schedule '{schedule.name}' triggered.",
            "execution_log": log_serializer.data if log_serializer else None
        })


@extend_schema_view(
    list=extend_schema(tags=["Admin Automation"]),
    retrieve=extend_schema(tags=["Admin Automation"]),
)
class AutoSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit log table of sync job runs.
    Entries are unmodifiable and non-deletable.
    """
    queryset = AutoSyncLog.objects.all().order_by('-started_at')
    serializer_class = AutoSyncLogSerializer
    permission_classes = [CanManageSiteConfig]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'service_type', 'provider_name', 'schedule']
    search_fields = ['schedule_name', 'provider_name', 'error_message']
    ordering_fields = ['started_at', 'duration_seconds', 'items_synced']



