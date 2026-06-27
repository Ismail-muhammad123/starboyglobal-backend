from rest_framework import serializers
from orders.models import Purchase

from orders.serializers.variations import (
    AirtimeNetworkSerializer, DataVariationSerializer, ElectricityServiceSerializer,
    ElectricityVariationSerializer, TVVariationSerializer, InternetVariationSerializer,
    EducationVariationSerializer
)

class PurchaseSerializer(serializers.ModelSerializer):
    airtime_service = AirtimeNetworkSerializer(read_only=True)
    data_variation = DataVariationSerializer(read_only=True)
    electricity_service = ElectricityServiceSerializer(read_only=True)
    electricity_variation = ElectricityVariationSerializer(read_only=True)
    tv_variation = TVVariationSerializer(read_only=True)
    internet_variation = InternetVariationSerializer(read_only=True)
    education_variation = EducationVariationSerializer(read_only=True)
    
    service_details = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            "id", "purchase_type", "reference", "amount", "beneficiary", 
            "status", "initiator", "time", "remarks",
            "airtime_service", "data_variation", "electricity_service", 
            "electricity_variation", "tv_variation", "internet_variation", 
            "education_variation", "token", "metadata", "service_details"
        ]

    def get_service_details(self, obj):
        if obj.purchase_type == 'airtime' and obj.airtime_service:
            return AirtimeNetworkSerializer(obj.airtime_service, context=self.context).data
        elif obj.purchase_type == 'data' and obj.data_variation:
            return DataVariationSerializer(obj.data_variation, context=self.context).data
        elif obj.purchase_type == 'electricity':
            if obj.electricity_variation:
                return ElectricityVariationSerializer(obj.electricity_variation, context=self.context).data
            elif obj.electricity_service:
                return ElectricityServiceSerializer(obj.electricity_service, context=self.context).data
        elif obj.purchase_type == 'tv' and obj.tv_variation:
            return TVVariationSerializer(obj.tv_variation, context=self.context).data
        elif obj.purchase_type == 'internet' and obj.internet_variation:
            return InternetVariationSerializer(obj.internet_variation, context=self.context).data
        elif obj.purchase_type == 'education' and obj.education_variation:
            return EducationVariationSerializer(obj.education_variation, context=self.context).data
        return None

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
