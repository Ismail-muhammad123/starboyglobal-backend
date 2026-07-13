
from rest_framework import serializers

class DeveloperCategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    endpoint = serializers.CharField()

class DeveloperCategoryListResponseSerializer(serializers.Serializer):
    categories = DeveloperCategorySerializer(many=True)

class DeveloperAirtimeNetworkResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()
    min_amount = serializers.FloatField()
    max_amount = serializers.FloatField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField(allow_null=True)
    api_discount = serializers.FloatField(allow_null=True)

class DeveloperDataNetworkResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperDataPlanResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField(allow_null=True)
    api_discount = serializers.FloatField(allow_null=True)
    plan_type = serializers.CharField()
    last_updated = serializers.DateTimeField(allow_null=True)

class DeveloperTVServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperTVPackageResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField(allow_null=True)
    api_discount = serializers.FloatField(allow_null=True)
    last_updated = serializers.DateTimeField(allow_null=True)

class DeveloperElectricityServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperElectricityVariationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    min_amount = serializers.FloatField()
    max_amount = serializers.FloatField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField(allow_null=True)
    api_discount = serializers.FloatField(allow_null=True)
    last_updated = serializers.DateTimeField(allow_null=True)

class DeveloperInternetServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperInternetPlanResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField(allow_null=True)
    api_discount = serializers.FloatField(allow_null=True)
    last_updated = serializers.DateTimeField(allow_null=True)

class DeveloperEducationServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperEducationVariationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField(allow_null=True)
    api_discount = serializers.FloatField(allow_null=True)
    last_updated = serializers.DateTimeField(allow_null=True)
