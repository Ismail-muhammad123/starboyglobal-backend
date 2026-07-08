from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, serializers, status
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer

from users.models import RoleUpgradeConfig, RoleUpgradeLog

# Allowed upgrade paths: (from_role, to_role)
ALLOWED_UPGRADES = {
    ('customer', 'agent'),
    ('customer', 'developer'),
    ('agent', 'developer'),
}


@extend_schema(tags=["Account - Role Upgrade"])
class RoleUpgradeFeesView(APIView):
    """
    GET /users/upgrade/fees/
    Returns the current fees for all allowed role upgrades, and whether the
    self-service upgrade program is active.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={
            200: inline_serializer("RoleUpgradeFeesResponse", fields={
                "is_active": serializers.BooleanField(),
                "current_role": serializers.CharField(),
                "available_upgrades": serializers.ListField(
                    child=inline_serializer("UpgradePath", fields={
                        "to_role": serializers.CharField(),
                        "fee": serializers.DecimalField(max_digits=10, decimal_places=2),
                        "kyc_required": serializers.BooleanField(default=False),
                    })
                ),
            })
        }
    )
    def get(self, request):
        from summary.models import SiteConfig
        site_config = SiteConfig.objects.first()
        
        config = RoleUpgradeConfig.objects.first()
        user_role = request.user.role
        available = []

        # 1. Check legacy RoleUpgradeConfig
        if config and config.is_active:
            for (from_r, to_r) in ALLOWED_UPGRADES:
                if from_r == user_role:
                    fee = config.get_upgrade_fee(from_r, to_r)
                    if fee is not None:
                        available.append({
                            "to_role": to_r, 
                            "fee": fee,
                            "kyc_required": False # Legacy config doesn't have KYC field yet
                        })

        # 2. Check new SiteConfig Agent Upgrade (if not already added or if we want to override)
        if user_role == 'customer' and site_config:
            # Check if 'agent' is already in available, if so we might want to prioritize SiteConfig or just add it
            if not any(u['to_role'] == 'agent' for u in available):
                available.append({
                    "to_role": 'agent',
                    "fee": site_config.agent_upgrade_fee,
                    "kyc_required": site_config.agent_upgrade_kyc_required
                })

        return Response({
            "is_active": (config and config.is_active) or (site_config is not None),
            "current_role": user_role,
            "available_upgrades": available,
        })


@extend_schema(tags=["Account - Role Upgrade"])
class RoleUpgradeView(APIView):
    """
    POST /users/upgrade/
    Upgrades the authenticated user's role. Charges their wallet if a fee applies.

    Body:
        { "to_role": "agent" | "developer" }
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=inline_serializer("RoleUpgradeRequest", fields={
            "to_role": serializers.ChoiceField(choices=["agent", "developer"]),
        }),
        responses={
            200: inline_serializer("RoleUpgradeResponse", fields={
                "message": serializers.CharField(),
                "new_role": serializers.CharField(),
                "fee_charged": serializers.DecimalField(max_digits=10, decimal_places=2),
            }),
            400: inline_serializer("RoleUpgradeError", fields={"error": serializers.CharField()}),
        }
    )
    def post(self, request):
        to_role = request.data.get("to_role", "").lower()
        user = request.user
        from_role = user.role

        # Validate target role
        if not to_role:
            return Response({"error": "to_role is required."}, status=status.HTTP_400_BAD_REQUEST)

        if (from_role, to_role) not in ALLOWED_UPGRADES:
            return Response(
                {"error": f"Upgrade from '{from_role}' to '{to_role}' is not permitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        config = RoleUpgradeConfig.objects.first()
        if not config or not config.is_active:
            return Response(
                {"error": "Self-service role upgrades are currently disabled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        fee = config.get_upgrade_fee(from_role, to_role)
        if fee is None:
            return Response(
                {"error": "No fee configured for this upgrade path."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                if fee > 0:
                    from wallet.models import Wallet
                    from wallet.utils import deduct_wallet

                    wallet = Wallet.objects.select_for_update().filter(user=user).first()
                    if not wallet or wallet.balance < fee:
                        return Response(
                            {"error": f"Insufficient wallet balance. Required: ₦{fee:,.2f}."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    deduct_wallet(
                        user_id=user.id,
                        amount=fee,
                        description=f"Role upgrade: {from_role} → {to_role}",
                    )

                # Apply upgrade
                user.role = to_role
                user.upgraded_at = timezone.now()
                user.save(update_fields=['role', 'upgraded_at'])

                RoleUpgradeLog.objects.create(
                    user=user,
                    from_role=from_role,
                    to_role=to_role,
                    fee_charged=fee,
                )

                if to_role == 'developer':
                    from developer_api.models import DeveloperProfile, APIKey
                    import secrets
                    profile, _ = DeveloperProfile.objects.get_or_create(user=user)
                    if not APIKey.objects.filter(profile=profile, mode='live').exists():
                        APIKey.objects.create(
                            profile=profile,
                            key=APIKey.generate_key(mode='live'),
                            mode='live',
                            is_active=True
                        )
                    if not APIKey.objects.filter(profile=profile, mode='sandbox').exists():
                        APIKey.objects.create(
                            profile=profile,
                            key=APIKey.generate_key(mode='sandbox'),
                            mode='sandbox',
                            is_active=True
                        )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": f"Successfully upgraded to {to_role}.",
            "new_role": to_role,
            "fee_charged": fee,
        })


@extend_schema(tags=["Account - Role Upgrade"])
class AgentUpgradeView(APIView):
    """
    POST /users/upgrade/agent/
    Upgrades the authenticated user's role to Agent using the fees and KYC settings
    configured in the Global Site Configuration (SiteConfig).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Upgrade to Agent (Global Config)",
        description="Upgrades the user to Agent role using settings from the Global Site Configuration.",
        responses={
            200: inline_serializer("AgentUpgradeResponse", fields={
                "message": serializers.CharField(),
                "new_role": serializers.CharField(),
                "fee_charged": serializers.DecimalField(max_digits=12, decimal_places=2),
            }),
            400: inline_serializer("AgentUpgradeError", fields={"error": serializers.CharField()}),
        }
    )
    def post(self, request):
        user = request.user
        if user.role == "agent":
            return Response({"error": "You are already an agent."}, status=status.HTTP_400_BAD_REQUEST)

        from summary.models import SiteConfig
        config = SiteConfig.objects.first()
        if not config:
            return Response({"error": "Site configuration not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        fee = config.agent_upgrade_fee
        kyc_required = config.agent_upgrade_kyc_required

        if kyc_required and not user.is_kyc_verified:
            return Response(
                {"error": "KYC verification is required for this upgrade. Please complete your KYC first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                if fee > 0:
                    from wallet.models import Wallet
                    from wallet.utils import deduct_wallet

                    wallet = Wallet.objects.select_for_update().filter(user=user).first()
                    if not wallet or wallet.balance < fee:
                        return Response(
                            {"error": f"Insufficient wallet balance. Required: ₦{fee:,.2f}."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    deduct_wallet(
                        user_id=user.id,
                        amount=fee,
                        description="Agent upgrade fee",
                    )

                # Apply upgrade
                from_role = user.role
                user.role = "agent"
                user.upgraded_at = timezone.now()
                user.save(update_fields=["role", "upgraded_at"])

                RoleUpgradeLog.objects.create(
                    user=user,
                    from_role=from_role,
                    to_role="agent",
                    fee_charged=fee,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Successfully upgraded to Agent status.",
            "new_role": "agent",
            "fee_charged": fee,
        })
