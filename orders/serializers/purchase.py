from rest_framework import serializers
from orders.models import Purchase


class PurchaseSerializer(serializers.ModelSerializer):
    service_details = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            "id", "purchase_type", "reference", "amount", "beneficiary",
            "status", "initiator", "time", "remarks",
            "token", "metadata", "service_details"
        ]

    def get_service_details(self, obj):
        request = self.context.get('request')

        def abs_url(image_field):
            if not image_field:
                return None
            if request:
                return request.build_absolute_uri(image_field.url)
            return image_field.url

        if obj.purchase_type == 'airtime' and obj.airtime_service:
            svc = obj.airtime_service
            return {
                "service_name": svc.service_name,
                "plan_name": None,
                "image": abs_url(svc.image),
            }
        elif obj.purchase_type == 'data' and obj.data_variation:
            var = obj.data_variation
            return {
                "service_name": var.service.service_name if var.service else None,
                "plan_name": var.name,
                "image": abs_url(var.service.image) if var.service else None,
            }
        elif obj.purchase_type == 'electricity':
            if obj.electricity_variation and obj.electricity_variation.service:
                svc = obj.electricity_variation.service
                return {
                    "service_name": svc.service_name,
                    "plan_name": obj.electricity_variation.name,
                    "image": abs_url(svc.image),
                }
            elif obj.electricity_service:
                svc = obj.electricity_service
                return {
                    "service_name": svc.service_name,
                    "plan_name": None,
                    "image": abs_url(svc.image),
                }
        elif obj.purchase_type == 'tv' and obj.tv_variation:
            var = obj.tv_variation
            return {
                "service_name": var.service.service_name if var.service else None,
                "plan_name": var.name,
                "image": abs_url(var.service.image) if var.service else None,
            }
        elif obj.purchase_type == 'internet' and obj.internet_variation:
            var = obj.internet_variation
            return {
                "service_name": var.service.service_name if var.service else None,
                "plan_name": var.name,
                "image": abs_url(var.service.image) if var.service else None,
            }
        elif obj.purchase_type == 'education' and obj.education_variation:
            var = obj.education_variation
            return {
                "service_name": var.service.service_name if var.service else None,
                "plan_name": var.name,
                "image": abs_url(var.service.image) if var.service else None,
            }
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
