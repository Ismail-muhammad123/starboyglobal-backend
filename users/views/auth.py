from django.contrib.auth import get_user_model, logout, authenticate
from rest_framework import status, generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from users.models import OTP, Referral
from users.utils import send_otp_code
from users.serializers import (
    LoginSerializer, SignupSerializer, GoogleAuthSerializer, 
    Verify2FASerializer, ProfileSerializer
)

User = get_user_model()

class LoginView(APIView):
    @extend_schema(
        tags=["Account - Auth"],
        request=LoginSerializer,
        responses={
            200: inline_serializer(name="LoginResponse", fields={
                "refresh": serializers.CharField(),
                "access": serializers.CharField(),
                "user": ProfileSerializer()
            }),
            202: inline_serializer(name="Login2FARequired", fields={
                "requires_2fa": serializers.BooleanField(),
                "message": serializers.CharField(),
                "identifier": serializers.CharField(),
            }),
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]
        pin = serializer.validated_data["pin"]
        user = authenticate(username=phone, password=pin)
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"error": "Account not active"}, status=status.HTTP_403_FORBIDDEN)
        
        # 2FA check — only for regular users (not staff/admin)
        if user.is_2fa_enabled and not user.is_staff and not user.is_superuser:
            send_otp_code(user, "2fa")
            return Response({
                "requires_2fa": True,
                "message": "A verification code has been sent to your registered channels.",
                "identifier": user.phone_number,
            }, status=status.HTTP_202_ACCEPTED)
        
        from developer_api.models import ensure_developer_profile
        ensure_developer_profile(user)
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token), "user": ProfileSerializer(user).data})

class RefreshTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    @extend_schema(tags=["Account - Auth"], request=inline_serializer("RefreshTokenRequest", fields={"refresh": serializers.CharField()}), responses={200: inline_serializer("RefreshTokenResponse", fields={"access": serializers.CharField()})})
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(refresh_token)
            return Response({"access": str(refresh.access_token)}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)

class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    @extend_schema(tags=["Account - Auth"], request=GoogleAuthSerializer, responses={200: inline_serializer("GoogleAuthResponse", fields={"refresh": serializers.CharField(), "access": serializers.CharField(), "user": ProfileSerializer()})})
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["id_token"]
        phone_number = serializer.validated_data.get("phone_number")
        referral_code = serializer.validated_data.get("referral_code")
        try:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
            email, google_id = idinfo['email'], idinfo['sub']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            user = User.objects.filter(google_id=google_id).first() or User.objects.filter(email=email).first()
            is_new_user = False
            
            if not user:
                is_new_user = True
                if not phone_number:
                    return Response({
                        "error": "Phone number required", 
                        "code": "PHONE_NUMBER_REQUIRED", 
                        "google_data": idinfo,
                        "is_new_user": True
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user = User.objects.create_user(
                    phone_number=phone_number, 
                    email=email, 
                    google_id=google_id, 
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True, 
                    email_verified=True, 
                    is_verified=True
                )
                if referral_code:
                    try:
                        referrer = User.objects.get(referral_code=referral_code)
                        Referral.objects.create(referrer=referrer, referred=user)
                    except User.DoesNotExist: pass
            else:
                updated = False
                if not user.google_id:
                    user.google_id = google_id
                    updated = True
                if not user.first_name and first_name:
                    user.first_name = first_name
                    updated = True
                if not user.last_name and last_name:
                    user.last_name = last_name
                    updated = True
                if updated:
                    user.save()
            
            # 2FA check for Google auth too (regular users only)
            if user.is_2fa_enabled and not user.is_staff and not user.is_superuser:
                send_otp_code(user, "2fa")
                return Response({
                    "requires_2fa": True,
                    "message": "A verification code has been sent to your registered channels.",
                    "identifier": user.phone_number,
                }, status=status.HTTP_202_ACCEPTED)
            
            from developer_api.models import ensure_developer_profile
            ensure_developer_profile(user)
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh), 
                "access": str(refresh.access_token), 
                "user": ProfileSerializer(user).data,
                "is_new_user": is_new_user
            })
        except ValueError:
            return Response({"error": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

class Verify2FAView(APIView):
    permission_classes = [permissions.AllowAny]
    @extend_schema(
        tags=["Account - 2FA"],
        summary="Verify 2FA code to complete login",
        description="After receiving a 202 response from login, submit the OTP code here to get your auth tokens.",
        request=Verify2FASerializer,
        responses={200: inline_serializer("Verify2FAResponse", fields={"refresh": serializers.CharField(), "access": serializers.CharField(), "user": ProfileSerializer()})}
    )
    def post(self, request):
        serializer = Verify2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        
        try:
            user = User.objects.get(email=identifier) if "@" in identifier else User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        otp = OTP.objects.filter(
            user=user, code=serializer.validated_data["otp_code"], 
            purpose="2fa", is_used=False
        ).order_by('-created_at').first()
        
        if not otp:
            return Response({"error": "Invalid or expired OTP code."}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils import timezone
        if otp.expires_at < timezone.now():
            return Response({"error": "OTP has expired. Please login again."}, status=status.HTTP_400_BAD_REQUEST)
        
        otp.is_used = True
        otp.save()
        from developer_api.models import ensure_developer_profile
        ensure_developer_profile(user)
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token), "user": ProfileSerializer(user).data})


class Resend2FACodeView(APIView):
    """Resend the 2FA OTP code if the user didn't receive it."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Account - 2FA"],
        summary="Resend 2FA verification code",
        request=inline_serializer("Resend2FARequest", fields={
            "identifier": serializers.CharField(help_text="Phone number or email"),
            "channel": serializers.ChoiceField(choices=['sms', 'whatsapp', 'email'], required=False,
                                                help_text="Preferred delivery channel. Defaults to user's 2FA method.")
        }),
        responses={200: inline_serializer("MessageResponse", fields={"message": serializers.CharField()})}
    )
    def post(self, request):
        identifier = request.data.get("identifier")
        channel = request.data.get("channel")
        
        try:
            user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.is_2fa_enabled:
            return Response({"error": "2FA is not enabled for this account."}, status=status.HTTP_400_BAD_REQUEST)
        
        send_otp_code(user, "2fa", preferred_channel=channel)
        return Response({"message": "Verification code resent."})


class Reset2FAView(APIView):
    """
    Reset (disable) 2FA for a user who has lost access to their 2FA channels.
    POST: Request a reset code via an alternative channel.
    PUT: Submit the code to disable 2FA.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Account - 2FA"],
        summary="Request 2FA reset code via alternative channel",
        description="Sends a reset code via a specified alternative channel (sms, whatsapp, email). "
                    "Use this when the user cannot receive codes on their primary 2FA channel.",
        request=inline_serializer("Request2FAResetRequest", fields={
            "identifier": serializers.CharField(help_text="Phone number"),
            "channel": serializers.ChoiceField(choices=['sms', 'whatsapp', 'email'],
                                                help_text="Alternative channel to receive the reset code")
        }),
        responses={200: inline_serializer("MessageResponse", fields={"message": serializers.CharField()})}
    )
    def post(self, request):
        identifier = request.data.get("identifier")
        channel = request.data.get("channel")
        
        try:
            user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if not user.is_2fa_enabled:
            return Response({"error": "2FA is not enabled for this account."}, status=status.HTTP_400_BAD_REQUEST)
        
        if channel == 'email' and not user.email:
            return Response({"error": "No email address on file. Please contact support."}, status=status.HTTP_400_BAD_REQUEST)
        
        send_otp_code(user, "2fa", preferred_channel=channel)
        return Response({"message": f"Reset code sent via {channel}. Use it to disable 2FA."})

    @extend_schema(
        tags=["Account - 2FA"],
        summary="Confirm 2FA reset and disable 2FA",
        description="Submit the reset code to disable 2FA on the account. "
                    "The user can then login normally and re-enable 2FA if desired.",
        request=inline_serializer("Confirm2FAResetRequest", fields={
            "identifier": serializers.CharField(help_text="Phone number"),
            "otp_code": serializers.CharField(help_text="The reset OTP code"),
        }),
        responses={200: inline_serializer("MessageResponse", fields={"message": serializers.CharField()})}
    )
    def put(self, request):
        identifier = request.data.get("identifier")
        otp_code = request.data.get("otp_code")
        
        try:
            user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        otp = OTP.objects.filter(
            user=user, code=otp_code, purpose="2fa", is_used=False
        ).order_by('-created_at').first()
        
        if not otp:
            return Response({"error": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils import timezone
        if otp.expires_at < timezone.now():
            return Response({"error": "Code has expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        otp.is_used = True
        otp.save()
        
        # Disable 2FA
        user.is_2fa_enabled = False
        user.two_factor_method = 'none'
        user.save(update_fields=['is_2fa_enabled', 'two_factor_method'])
        
        return Response({"message": "2FA has been disabled. You can now login normally."})


@extend_schema(tags=["Account - Auth"])
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    
    @extend_schema(tags=["Account - Auth"], request=SignupSerializer, responses={201: SignupSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class ResendActivationCodeView(APIView):
    @extend_schema(tags=["Account - Auth"], responses={200: inline_serializer("MessageResponse", fields={"message": serializers.CharField()})})
    def post(self, request):
        identifier, channel = request.data.get("identifier"), request.data.get("channel")
        user = User.objects.get(phone_number=identifier)
        if user.is_verified: return Response({"error": "Already verified"}, status=400)
        send_otp_code(user, "activation", preferred_channel=channel)
        return Response({"message": "Code resent"})

class ActivateAccountView(APIView):
    @extend_schema(tags=["Account - Auth"], responses={200: inline_serializer("MessageResponse", fields={"message": serializers.CharField()})})
    def post(self, request):
        user = User.objects.get(phone_number=request.data.get("identifier"))
        otp = OTP.objects.get(user=user, code=request.data.get("otp"), purpose="activation", is_used=False)
        user.is_active = user.is_verified = True
        if otp.channel == "email": user.email_verified = True
        elif otp.channel in ["sms", "whatsapp"]: user.phone_number_verified = True
        user.save()
        otp.is_used = True
        otp.save()
        from summary.models import SiteConfig
        from wallet.utils import fund_wallet, process_referral_reward
        config = SiteConfig.objects.first()
        if config and config.signup_bonus_enabled:
            fund_wallet(user.id, float(config.signup_bonus_amount), description="Signup Bonus")
        process_referral_reward(user, trigger_event='signup')
        return Response({"message": "Activated"})

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(tags=["Account - Auth"], responses={200: inline_serializer("MessageResponse", fields={"message": serializers.CharField()})})
    def post(self, request):
        try: RefreshToken(request.data.get("refresh")).blacklist()
        except: pass
        logout(request)
        return Response({"message": "Logged out"})
