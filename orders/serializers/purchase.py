from rest_framework import serializers
from orders.models import Purchase

class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = [
            "id", "purchase_type", "reference", "amount", "beneficiary", 
            "status", "initiator", "time", "remarks",
            "airtime_service", "data_variation", "electricity_service", 
            "electricity_variation", "tv_variation", "internet_variation", 
            "education_variation", "token", "metadata"
        ]

class BasePurchaseRequestSerializer(serializers.Serializer):
    transaction_pin = serializers.CharField(max_length=4, write_only=True)
    promo_code = serializers.CharField(max_length=50, required=False, allow_null=True)

class DataPurchaseRequestSerializer(BasePurchaseRequestSerializer):
    plan_id = serializers.IntegerField(); phone_number = serializers.CharField(max_length=20)

class AirtimePurchaseRequestSerializer(BasePurchaseRequestSerializer):
    service_id = serializers.IntegerField()  # DB PK of the AirtimeNetwork record
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    phone_number = serializers.CharField(max_length=20)


class ElectricityPurchaseRequestSerializer(BasePurchaseRequestSerializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2); service_id = serializers.CharField(); variation_id = serializers.CharField(max_length=50); customer_id = serializers.CharField(max_length=20)

class TVPurchaseRequestSerializer(BasePurchaseRequestSerializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2); service_id = serializers.CharField(); customer_id = serializers.CharField(max_length=50); subscription_type = serializers.CharField(max_length=50); variation_id = serializers.CharField(max_length=50)

class InternetPurchaseRequestSerializer(BasePurchaseRequestSerializer):
    plan_id = serializers.IntegerField(); phone_number = serializers.CharField()

class EducationPurchaseRequestSerializer(BasePurchaseRequestSerializer):
    service_id = serializers.CharField()
    variation_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    phone_number = serializers.CharField(max_length=20)
