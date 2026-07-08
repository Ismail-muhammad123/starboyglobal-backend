from rest_framework import status, generics, permissions, serializers
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from summary.models import SiteConfig
from ..models import DeveloperProfile, APIKey
from developer_api.authentication import APIKeyAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from users.views.auth import LoginView

User = get_user_model()

class DeveloperProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeveloperProfile
        fields = ['webhook_url', 'webhook_secret', 'created_at']

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['key', 'mode', 'is_active', 'created_at', 'last_used']

class DeveloperLoginView(LoginView):
    """
    POST /login/
    Proxies to standard JWT Login logic.
    """
    pass

class UpgradeToDeveloperView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.role == 'developer' and hasattr(user, 'developer_profile'):
            return Response({"error": "You are already a developer."}, status=status.HTTP_400_BAD_REQUEST)

        config = SiteConfig.objects.first()
        fee = config.developer_upgrade_fee if config else 0

        from wallet.models import Wallet
        wallet = Wallet.objects.filter(user=user).first()
        if not wallet or wallet.balance < fee:
            return Response({"error": f"Insufficient balance. Upgrade fee is ₦{fee:,.2f}."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                if fee > 0:
                    from wallet.utils import deduct_wallet
                    deduct_wallet(
                        user_id=user.id,
                        amount=fee,
                        description="Developer API Upgrade Fee",
                    )
                
                # Apply upgrade
                from_role = user.role
                user.role = 'developer'
                user.upgraded_at = timezone.now()
                user.save(update_fields=['role', 'upgraded_at'])
                
                profile, _ = DeveloperProfile.objects.get_or_create(user=user)
                
                if not APIKey.objects.filter(profile=profile, mode='live').exists():
                    APIKey.objects.create(profile=profile, key=APIKey.generate_key(mode='live'), mode='live', is_active=True)
                if not APIKey.objects.filter(profile=profile, mode='sandbox').exists():
                    APIKey.objects.create(profile=profile, key=APIKey.generate_key(mode='sandbox'), mode='sandbox', is_active=True)
                
                from users.models import RoleUpgradeLog
                RoleUpgradeLog.objects.create(
                    user=user,
                    from_role=from_role,
                    to_role='developer',
                    fee_charged=fee,
                )

            return Response({
                "message": "Successfully upgraded to developer.",
                "fee_deducted": float(fee)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeveloperDetailsView(generics.RetrieveAPIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = user.developer_profile
        except DeveloperProfile.DoesNotExist:
            return Response({"error": "Developer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        keys = APIKey.objects.filter(profile=profile)
        
        return Response({
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            },
            "wallet_balance": float(user.wallet.balance) if hasattr(user, 'wallet') else 0.0,
            "developer_profile": {
                "webhook_url": profile.webhook_url,
                "webhook_secret": profile.webhook_secret,
                "is_active": profile.is_active,
                "created_at": profile.created_at,
            },
            "api_keys": APIKeySerializer(keys, many=True).data
        })

class WalletFundingDetailsView(generics.RetrieveAPIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        config = SiteConfig.objects.first()
        if not config:
            return Response({"error": "Site configuration not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            "bank_name": config.vtu_funding_bank_name,
            "account_number": config.vtu_funding_account_number,
            "account_name": config.vtu_funding_account_name,
        })

class RegenerateAPIKeyView(generics.CreateAPIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        mode = request.data.get('mode', 'live')
        if mode not in ['live', 'sandbox']:
            return Response({"error": "Invalid mode. Must be 'live' or 'sandbox'."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            profile = request.user.developer_profile
            APIKey.objects.filter(profile=profile, mode=mode, is_active=True).update(is_active=False)
            new_key = APIKey.objects.create(
                profile=profile, 
                key=APIKey.generate_key(mode=mode), 
                mode=mode,
                is_active=True
            )
            return Response(APIKeySerializer(new_key).data)
        except DeveloperProfile.DoesNotExist:
            return Response({"error": "Developer profile not found."}, status=status.HTTP_403_FORBIDDEN)

class DeveloperWebhookUpdateView(generics.UpdateAPIView):
    authentication_classes = [JWTAuthentication, APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        webhook_url = request.data.get('webhook_url')
        if webhook_url is None:
            return Response({"error": "webhook_url is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if webhook_url != "":
            if not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
                return Response({"error": "Invalid URL format. Must start with http:// or https://."}, status=status.HTTP_400_BAD_REQUEST)
                
        try:
            profile = request.user.developer_profile
            profile.webhook_url = webhook_url
            profile.save(update_fields=['webhook_url'])
            return Response({
                "message": "Webhook URL updated successfully.",
                "webhook_url": profile.webhook_url,
                "webhook_secret": profile.webhook_secret
            }, status=status.HTTP_200_OK)
        except DeveloperProfile.DoesNotExist:
            return Response({"error": "Developer profile not found."}, status=status.HTTP_403_FORBIDDEN)
