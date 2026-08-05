from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from orders.models import (
    VTUProviderConfig, ServiceRouting, ServiceFallback, DataService, DataVariation, 
    AirtimeNetwork, TVService, TVVariation, InternetService, InternetVariation, 
    EducationService, EducationVariation, ElectricityService, ElectricityVariation,
    ProviderServiceConfig, AutoSyncSchedule, AutoSyncLog
)

from summary.models import SiteConfig


class InlineProviderServiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderServiceConfig
        fields = [
            'id', 'service_type',
            'catalogue_source', 'live_cache_ttl_seconds',
            'customer_margin_type', 'customer_margin_value',
            'agent_margin_type', 'agent_margin_value',
            'developer_margin_type', 'developer_margin_value',
        ]


class VTUProviderConfigSerializer(serializers.ModelSerializer):
    webhook_url = serializers.ReadOnlyField()
    callback_url = serializers.ReadOnlyField()
    supported_services = serializers.SerializerMethodField()
    config_requirements = serializers.SerializerMethodField()
    service_configs = InlineProviderServiceConfigSerializer(many=True, required=False)

    class Meta:
        model = VTUProviderConfig
        fields = [
            'id', 'name', 'is_active', 'api_key', 'user_id', 'session_id', 
            'secret_key', 'public_key', 'base_url', 'webhook_url', 'callback_url', 
            'max_retries', 'auto_refund_on_failure', 'account_name', 'bank_name', 
            'account_number', 'bank_code', 'min_funding_balance', 'auto_funding_enabled',
            'supported_services', 'config_requirements', 'service_configs'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_supported_services(self, obj):
        from orders.router import ProviderRouter
        p_class = ProviderRouter.FACTORIES.get(obj.name.lower())
        return p_class.get_supported_services() if p_class else []

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_config_requirements(self, obj):
        from orders.router import ProviderRouter
        p_class = ProviderRouter.FACTORIES.get(obj.name.lower())
        return p_class.get_config_requirements() if p_class else []

    def validate_service_configs(self, value):
        service_types = [item.get('service_type') for item in value if item.get('service_type')]
        if len(service_types) != len(set(service_types)):
            raise serializers.ValidationError("A provider can only have a maximum of 1 configuration per service type.")
        return value

    def create(self, validated_data):
        service_configs_data = validated_data.pop('service_configs', [])
        provider = super().create(validated_data)
        for cfg in service_configs_data:
            ProviderServiceConfig.objects.create(provider=provider, **cfg)
        return provider

    def update(self, instance, validated_data):
        service_configs_data = validated_data.pop('service_configs', None)
        provider = super().update(instance, validated_data)
        if service_configs_data is not None:
            for cfg in service_configs_data:
                stype = cfg.get('service_type')
                if stype:
                    ProviderServiceConfig.objects.update_or_create(
                        provider=provider,
                        service_type=stype,
                        defaults=cfg
                    )
        return provider


class ServiceFallbackSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_name_display', read_only=True)
    class Meta: model = ServiceFallback; fields = ["id", "provider", "provider_name", "priority"]

class ServiceRoutingSerializer(serializers.ModelSerializer):
    fallbacks = ServiceFallbackSerializer(source='servicefallback_set', many=True, read_only=True)
    primary_provider_name = serializers.CharField(source='primary_provider.get_name_display', read_only=True)
    class Meta: model = ServiceRouting; fields = ["id", "service", "primary_provider", "primary_provider_name", "fallbacks"]

class VTUProviderOverviewSerializer(serializers.ModelSerializer):
    balance = serializers.FloatField(required=False)
    class Meta:
        model = VTUProviderConfig
        fields = ['id', 'name', 'is_active', 'balance', 'account_name', 'bank_name', 'account_number', 'bank_code', 'min_funding_balance', 'auto_funding_enabled']

class AvailableVTUProviderSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    supported_services = serializers.ListField(child=serializers.CharField(), read_only=True)
    config_requirements = serializers.ListField(child=serializers.DictField(), read_only=True)

class ServiceAutomationConfigSerializer(serializers.ModelSerializer):
    primary_provider_name = serializers.CharField(source='primary_provider.get_name_display', read_only=True)
    class Meta:
        model = ServiceRouting
        fields = ['id', 'service', 'primary_provider', 'primary_provider_name', 'retry_enabled', 'retry_count', 'auto_refund_enabled', 'fallback_enabled', 'pricing_mode', 'customer_margin', 'agent_margin']

class FetchFromProviderRequestSerializer(serializers.Serializer):
    provider_id = serializers.IntegerField()
    service_type = serializers.ChoiceField(choices=['airtime', 'data', 'tv', 'electricity', 'internet', 'education'])

class ProviderFundingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = VTUProviderConfig
        fields = ['min_funding_balance', 'auto_funding_enabled', 'account_name', 'bank_name', 'account_number', 'bank_code']

class ServiceSummaryItemSerializer(serializers.Serializer):
    service = serializers.CharField()
    is_active = serializers.BooleanField()
    routing = ServiceRoutingSerializer(allow_null=True)
    success_rate = serializers.FloatField()
    total_variations = serializers.IntegerField()

class VTUOverviewResponseSerializer(serializers.Serializer):
    providers = VTUProviderOverviewSerializer(many=True)
    services_summary = ServiceSummaryItemSerializer(many=True)

class AdminAirtimeNetworkSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='provider.name')
    class Meta: model = AirtimeNetwork; fields = '__all__'

class AdminDataServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='provider.name')
    class Meta: model = DataService; fields = '__all__'

class AdminDataVariationSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='service.provider.name')
    service_details = AdminDataServiceSerializer(source='service', read_only=True)
    class Meta: model = DataVariation; fields = '__all__'

class AdminTVServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='provider.name')
    class Meta: model = TVService; fields = '__all__'

class AdminTVVariationSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='service.provider.name')
    service_details = AdminTVServiceSerializer(source='service', read_only=True)
    class Meta: model = TVVariation; fields = '__all__'

class AdminInternetServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='provider.name')
    class Meta: model = InternetService; fields = '__all__'

class AdminInternetVariationSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='service.provider.name')
    service_details = AdminInternetServiceSerializer(source='service', read_only=True)
    class Meta: model = InternetVariation; fields = '__all__'

class AdminEducationServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='provider.name')
    class Meta: model = EducationService; fields = '__all__'

class AdminEducationVariationSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='service.provider.name')
    service_details = AdminEducationServiceSerializer(source='service', read_only=True)
    class Meta: model = EducationVariation; fields = '__all__'

class AdminElectricityServiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='provider.name')
    class Meta: model = ElectricityService; fields = '__all__'

class AdminElectricityVariationSerializer(serializers.ModelSerializer):
    provider_name = serializers.ReadOnlyField(source='service.provider.name')
    service_details = AdminElectricityServiceSerializer(source='service', read_only=True)
    class Meta: model = ElectricityVariation; fields = '__all__'


class ProviderServiceConfigSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_name_display', read_only=True)

    class Meta:
        model = ProviderServiceConfig
        fields = [
            'id', 'provider', 'provider_name', 'service_type',
            'catalogue_source', 'live_cache_ttl_seconds',
            'customer_margin_type', 'customer_margin_value',
            'agent_margin_type', 'agent_margin_value',
            'developer_margin_type', 'developer_margin_value',
        ]


class AutoSyncConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = [
            'auto_sync_enabled', 'auto_sync_frequency', 'auto_sync_time',
            'auto_sync_last_run', 'auto_sync_next_run'
        ]
        read_only_fields = ['auto_sync_last_run', 'auto_sync_next_run']


class AutoSyncScheduleSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source='provider.get_name_display', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)

    class Meta:
        model = AutoSyncSchedule
        fields = [
            'id', 'name', 'provider', 'provider_display',
            'service_type', 'service_type_display',
            'frequency', 'frequency_display',
            'start_date_time', 'is_active',
            'last_run', 'next_run', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_run', 'next_run', 'created_at', 'updated_at']


class AutoSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoSyncLog
        fields = [
            'id', 'schedule', 'schedule_name', 'provider_name',
            'service_type', 'status', 'items_synced',
            'details', 'error_message', 'started_at',
            'finished_at', 'duration_seconds'
        ]
        read_only_fields = fields


