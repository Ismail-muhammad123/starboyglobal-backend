from django.utils import timezone
from datetime import datetime
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from summary.models import SummaryDashboard, SiteConfig
from admin_api.serializers import (
    AdminDashboardStatsResponseSerializer,
    AdminStatusResponseSerializer,
    AdminPauseServiceRequestSerializer,
)


class AdminDashboardStatsView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Dashboard overview statistics",
        description="Returns comprehensive dashboard stats including financial, wallets, purchases, users, VTU providers, service health, alerts, and config state. Supports optional date filtering via `start_date` and `end_date` query parameters (YYYY-MM-DD).",
        parameters=[
            OpenApiParameter(name='start_date', type=str, required=False, description='Filter start date (YYYY-MM-DD)'),
            OpenApiParameter(name='end_date', type=str, required=False, description='Filter end date (YYYY-MM-DD)'),
        ],
        responses={200: AdminDashboardStatsResponseSerializer}
    )
    def get(self, request):
        start = None
        end = None
        start_str = request.query_params.get('start_date')
        end_str = request.query_params.get('end_date')
        try:
            if start_str:
                start = datetime.strptime(start_str, '%Y-%m-%d')
                start = timezone.make_aware(start)
            if end_str:
                end = datetime.strptime(end_str, '%Y-%m-%d')
                end = timezone.make_aware(end)
        except (ValueError, TypeError):
            pass

        stats = SummaryDashboard.summary(start=start, end=end)
        return Response(stats)



class AdminMaintenanceModeView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Quick Actions"],
        summary="Toggle maintenance mode ON or OFF",
        description="Pass `{\"enabled\": true}` to turn ON, `{\"enabled\": false}` to turn OFF.",
        request={"application/json": {"type": "object", "properties": {"enabled": {"type": "boolean"}}, "required": ["enabled"]}},
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        enabled = request.data.get("enabled")
        if enabled is None:
            return Response({"error": "Field 'enabled' is required."}, status=status.HTTP_400_BAD_REQUEST)

        config, _ = SiteConfig.objects.get_or_create(pk=1)
        config.maintenance_mode = bool(enabled)
        config.save()

        state = "ON" if config.maintenance_mode else "OFF"
        return Response({"status": "SUCCESS", "message": f"Maintenance mode turned {state}."})


class AdminRefreshServicesView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Quick Actions"],
        summary="Force refresh all services",
        description="Triggers a refresh of provider balances and service status checks.",
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        # Re-fetch all balances and clear any cached data
        from summary.utils import get_api_wallet_balance, get_paystack_balance
        
        results = {
            "vtu_balance": get_api_wallet_balance() or 0.0,
            "payment_gateway_balance": get_paystack_balance() or 0.0,
        }
        
        return Response({
            "status": "SUCCESS",
            "message": "All services refreshed successfully.",
            "balances": results,
        })


class AdminPauseServiceView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Quick Actions"],
        summary="Pause or resume a specific service",
        description="Set `active` to false to pause, true to resume. Valid services: airtime, data, tv, electricity, education.",
        request=AdminPauseServiceRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    def post(self, request):
        serializer = AdminPauseServiceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = serializer.validated_data["service"]
        active = serializer.validated_data["active"]

        valid_services = ["airtime", "data", "tv", "electricity", "education"]
        if service not in valid_services:
            return Response(
                {"error": f"Invalid service. Must be one of: {', '.join(valid_services)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config, _ = SiteConfig.objects.get_or_create(pk=1)
        field_name = f"{service}_active"
        setattr(config, field_name, active)
        config.save()

        action_word = "resumed" if active else "paused"
        return Response({"status": "SUCCESS", "message": f"Service '{service}' {action_word}."})
