from rest_framework import serializers

class AdminKYCActionRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False)

class AdminAgentUpgradeRequestSerializer(serializers.Serializer):
    commission_rate = serializers.FloatField(required=False, default=0.0)

class AdminDepositMarkSuccessRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="Manually confirmed by Admin")

class AdminWithdrawalActionRequestSerializer(serializers.Serializer):
    pin = serializers.CharField()
    reason = serializers.CharField(required=False)

class AdminCreatePurchaseRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    purchase_type = serializers.ChoiceField(choices=['data', 'airtime', 'electricity', 'tv', 'internet', 'education'])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    beneficiary = serializers.CharField()
    action = serializers.CharField()
    pin = serializers.CharField()
    plan_id = serializers.CharField(required=False)
    service_id = serializers.CharField(required=False)
    network_id = serializers.CharField(required=False)

class AdminErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()

class AdminPauseServiceRequestSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=['airtime', 'data', 'tv', 'electricity', 'education'])
    active = serializers.BooleanField()

class AdminStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()

class AutomationGlobalSettingsSerializer(serializers.Serializer):
    auto_retry_enabled = serializers.BooleanField()
    auto_refund_enabled = serializers.BooleanField()
    notify_admin_on_failure = serializers.BooleanField()
    delayed_tx_detection_enabled = serializers.BooleanField()
    delayed_tx_timeout_minutes = serializers.IntegerField(min_value=1)

class VariationPriceUpdateSerializer(serializers.Serializer):
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    agent_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    developer_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

class BulkVariationPriceItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    agent_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    developer_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

class BulkVariationPriceUpdateSerializer(serializers.Serializer):
    variations = BulkVariationPriceItemSerializer(many=True)

class VariationToggleSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()

class ServiceTypeToggleSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()

class ServiceRetryConfigSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    count = serializers.IntegerField(min_value=0, max_value=10)

class ServicePricingModeSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['fixed_margin', 'defined'])
    customer_margin = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    agent_margin = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

class AutomationOverviewResponseSerializer(serializers.Serializer):
    global_settings = AutomationGlobalSettingsSerializer()
    services = serializers.ListField(child=serializers.DictField())


class AdminActionLogSerializer(serializers.ModelSerializer):
    admin_phone = serializers.CharField(source='admin_user.phone_number', read_only=True)
    admin_name = serializers.CharField(source='admin_user.full_name', read_only=True)

    class Meta:
        from admin_api.models import AdminActionLog
        model = AdminActionLog
        fields = '__all__'
