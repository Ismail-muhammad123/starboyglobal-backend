from rest_framework import serializers
from orders.models import (
    DataService, DataVariation, AirtimeNetwork, ElectricityService, ElectricityVariation, 
    TVService, TVVariation, InternetService, InternetVariation, EducationService, EducationVariation, PromoCode
)

def resolve_price(obj, price_type, service_name):
    """
    Resolves the price for a variation/network based on ServiceRouting margin or defined pricing.
    price_type can be 'customer', 'agent', or 'developer'
    """
    from orders.models import ServiceRouting
    r = ServiceRouting.objects.filter(service=service_name).first()
    
    if r and r.pricing_mode == 'fixed_margin':
        margin = getattr(r, f"{price_type}_margin", 0)
        return float(obj.cost_price + margin)
    
    # defined pricing mode
    val = getattr(obj, f"{price_type}_price", 0)
    if price_type == 'developer':
        if not val or float(val) == 0.0:
            val = obj.selling_price
    elif price_type == 'agent':
        if not val or float(val) == 0.0:
            val = obj.selling_price
            
    return float(val)

class DataServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    class Meta:
        model = DataService
        fields = ['id', 'service_name', 'service_id', 'provider', 'provider_name', 'image', 'is_active']

class DataVariationSerializer(serializers.ModelSerializer):
    service = DataServiceSerializer(read_only=True)
    provider_name = serializers.CharField(source='service.provider.name', read_only=True)
    selling_price = serializers.SerializerMethodField()
    agent_price = serializers.SerializerMethodField()
    developer_price = serializers.SerializerMethodField()

    class Meta:
        model = DataVariation
        fields = ["id", "name", "service", "provider_name", "variation_id", "selling_price", "agent_price", "developer_price", "plan_type", "is_active"]

    def get_selling_price(self, obj):
        return resolve_price(obj, 'customer', 'data')

    def get_agent_price(self, obj):
        return resolve_price(obj, 'agent', 'data')

    def get_developer_price(self, obj):
        return resolve_price(obj, 'developer', 'data')

class AirtimeNetworkSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    selling_price = serializers.SerializerMethodField()
    agent_price = serializers.SerializerMethodField()
    developer_price = serializers.SerializerMethodField()

    class Meta: 
        model = AirtimeNetwork
        fields = ['id', 'service_name', 'service_id', 'provider', 'provider_name', 'min_amount', 'max_amount', 'discount', 'agent_discount', 'selling_price', 'agent_price', 'developer_price', 'image', 'is_active']

    def get_selling_price(self, obj):
        return resolve_price(obj, 'customer', 'airtime')

    def get_agent_price(self, obj):
        return resolve_price(obj, 'agent', 'airtime')

    def get_developer_price(self, obj):
        return resolve_price(obj, 'developer', 'airtime')

class ElectricityServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    class Meta: 
        model = ElectricityService
        fields = ['id', 'service_name', 'service_id', 'provider', 'provider_name', 'image', 'is_active']

class ElectricityVariationSerializer(serializers.ModelSerializer):
    service = ElectricityServiceSerializer(read_only=True)
    provider_name = serializers.CharField(source='service.provider.name', read_only=True)
    selling_price = serializers.SerializerMethodField()
    agent_price = serializers.SerializerMethodField()
    developer_price = serializers.SerializerMethodField()

    class Meta: 
        model = ElectricityVariation
        fields = ["id", "name", "service", "provider_name", "variation_id", "discount", "agent_discount", "selling_price", "agent_price", "developer_price", "plan_type", "is_active"]

    def get_selling_price(self, obj):
        return resolve_price(obj, 'customer', 'electricity')

    def get_agent_price(self, obj):
        return resolve_price(obj, 'agent', 'electricity')

    def get_developer_price(self, obj):
        return resolve_price(obj, 'developer', 'electricity')

class TVServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    class Meta: 
        model = TVService
        fields = ['id', 'service_name', 'service_id', 'provider', 'provider_name', 'image', 'is_active']

class TVVariationSerializer(serializers.ModelSerializer):
    service = TVServiceSerializer(read_only=True)
    provider_name = serializers.CharField(source='service.provider.name', read_only=True)
    selling_price = serializers.SerializerMethodField()
    agent_price = serializers.SerializerMethodField()
    developer_price = serializers.SerializerMethodField()

    class Meta: 
        model = TVVariation
        fields = ["id", "name", "service", "provider_name", "variation_id", "selling_price", "agent_price", "developer_price", "plan_type", "is_active"]

    def get_selling_price(self, obj):
        return resolve_price(obj, 'customer', 'tv')

    def get_agent_price(self, obj):
        return resolve_price(obj, 'agent', 'tv')

    def get_developer_price(self, obj):
        return resolve_price(obj, 'developer', 'tv')

class InternetServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    class Meta: 
        model = InternetService
        fields = ['id', 'service_name', 'service_id', 'provider', 'provider_name', 'image', 'is_active']

class InternetVariationSerializer(serializers.ModelSerializer):
    service = InternetServiceSerializer(read_only=True)
    provider_name = serializers.CharField(source='service.provider.name', read_only=True)
    selling_price = serializers.SerializerMethodField()
    agent_price = serializers.SerializerMethodField()
    developer_price = serializers.SerializerMethodField()

    class Meta: 
        model = InternetVariation
        fields = ["id", "name", "service", "provider_name", "variation_id", "selling_price", "agent_price", "developer_price", "plan_type", "is_active"]

    def get_selling_price(self, obj):
        return resolve_price(obj, 'customer', 'internet')

    def get_agent_price(self, obj):
        return resolve_price(obj, 'agent', 'internet')

    def get_developer_price(self, obj):
        return resolve_price(obj, 'developer', 'internet')

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta: 
        model = PromoCode
        fields = ['code', 'discount_amount', 'discount_percentage', 'expiry_date', 'is_active']

class EducationServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    class Meta: 
        model = EducationService
        fields = ['id', 'service_name', 'service_id', 'provider', 'provider_name', 'image', 'is_active']

class EducationVariationSerializer(serializers.ModelSerializer):
    service = EducationServiceSerializer(read_only=True)
    provider_name = serializers.CharField(source='service.provider.name', read_only=True)
    selling_price = serializers.SerializerMethodField()
    agent_price = serializers.SerializerMethodField()
    developer_price = serializers.SerializerMethodField()

    class Meta: 
        model = EducationVariation
        fields = ["id", "name", "service", "provider_name", "variation_id", "selling_price", "agent_price", "developer_price", "plan_type", "is_active"]

    def get_selling_price(self, obj):
        return resolve_price(obj, 'customer', 'education')

    def get_agent_price(self, obj):
        return resolve_price(obj, 'agent', 'education')

    def get_developer_price(self, obj):
        return resolve_price(obj, 'developer', 'education')
