from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import Referral, ReferralConfig

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    pin = serializers.CharField()

class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(help_text="Google ID token")
    phone_number = serializers.CharField(required=False, help_text="Required for new signups")
    referral_code = serializers.CharField(required=False, allow_blank=True, help_text="Optional referral code for signups")

class Verify2FASerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="User phone number or email")
    otp_code = serializers.CharField(help_text="6-digit OTP code")

class SignupSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True, min_length=4, max_length=6)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "phone_country_code", "phone_number", "email", "pin",
            "first_name", "last_name", "middle_name",
            "referral_code",
        ]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "middle_name": {"required": False},
            "email": {"required": False},
        }

    def validate_referral_code(self, value):
        if value:
            if not User.objects.filter(referral_code=value).exists():
                return ""
        return value

    def validate_email(self, value):
        if not value:
            return value
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def create(self, validated_data):
        pin = validated_data.pop("pin")
        referral_code_input = validated_data.pop("referral_code", None)

        user = User.objects.create_user(**validated_data, password=pin)
        user.is_active = True
        user.save()

        if referral_code_input:
            try:
                referrer = User.objects.get(referral_code=referral_code_input)
                referral = Referral.objects.create(referrer=referrer, referred=user)
                config = ReferralConfig.objects.first()
                if config and config.is_active and config.commission_mode == 'signup':
                    from wallet.utils import fund_wallet
                    from django.db.models import F
                    bonus = config.commission_value
                    fund_wallet(referrer.id, float(bonus), description=f"Referral bonus: {user.phone_number} signed up with your code")
                    referral.bonus_paid = True
                    referral.bonus_amount = bonus
                    referral.save()
                    referrer.referral_earnings_count = F('referral_earnings_count') + 1
                    referrer.referral_earnings_amount = F('referral_earnings_amount') + bonus
                    referrer.save(update_fields=['referral_earnings_count', 'referral_earnings_amount'])
            except User.DoesNotExist:
                pass
        return user
