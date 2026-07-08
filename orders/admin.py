from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DataService, DataVariation, AirtimeNetwork, 
    ElectricityService, ElectricityVariation, 
    Purchase, TVService, TVVariation,
    InternetVariation, ServiceRouting, VTUProviderConfig, ServiceFallback,
    InternetService, EducationService, EducationVariation,
    DynamicVTUProvider, DynamicOperationConfig,
    DynamicProviderHeader, DynamicOperationHeader, DynamicOperationPayload
)
from django.db.models import Sum, Count, F
from django.contrib.admin import SimpleListFilter
from django.db import transaction as db_transaction
from wallet.utils import fund_wallet
from .router import ProviderRouter


class DynamicOperationHeaderInline(admin.TabularInline):
    model = DynamicOperationHeader
    extra = 1

class DynamicOperationPayloadInline(admin.TabularInline):
    model = DynamicOperationPayload
    extra = 1

class DynamicOperationConfigInline(admin.TabularInline):
    model = DynamicOperationConfig
    extra = 1

class DynamicProviderHeaderInline(admin.TabularInline):
    model = DynamicProviderHeader
    extra = 1

@admin.register(DynamicVTUProvider)
class DynamicVTUProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'base_url', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DynamicProviderHeaderInline, DynamicOperationConfigInline]

@admin.register(DynamicOperationConfig)
class DynamicOperationConfigAdmin(admin.ModelAdmin):
    list_display = ('provider', 'operation_type', 'endpoint_path', 'method')
    list_filter = ('provider', 'operation_type', 'method')
    inlines = [DynamicOperationHeaderInline, DynamicOperationPayloadInline]
    fieldsets = (
        (None, {
            'fields': ('provider', 'operation_type', 'endpoint_path', 'method', 'request_format')
        }),
        ('Mapping & Config', {
            'fields': ('request_params', 'static_params', 'success_mapping', 'failure_mapping', 'response_data_mapping'),
            'description': 'Use {variable} syntax in endpoints, headers, and payloads.'
        }),
    )


class ProviderSyncMixin:
    def sync_all_services(self, request, queryset):
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += sum([
                        impl.sync_airtime(), impl.sync_data(), impl.sync_cable(),
                        impl.sync_electricity(), impl.sync_internet(), impl.sync_education()
                    ])
            self.message_user(request, f"Successfully synced {total_synced} items from active providers")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_all_services.short_description = "Sync all services from Active Providers"

    def sync_airtime_services(self, request, queryset):
        from .router import ProviderRouter
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += impl.sync_airtime()
            self.message_user(request, f"Successfully synced {total_synced} airtime networks")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_airtime_services.short_description = "Sync Airtime from Active Providers"

    def sync_data_services(self, request, queryset):
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += impl.sync_data()
            self.message_user(request, f"Successfully synced {total_synced} data plans")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_data_services.short_description = "Sync Data from Active Providers"

    def sync_cable_services(self, request, queryset):
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += impl.sync_cable()
            self.message_user(request, f"Successfully synced {total_synced} cable packages")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_cable_services.short_description = "Sync Cable from Active Providers"

    def sync_electricity_services(self, request, queryset):
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += impl.sync_electricity()
            self.message_user(request, f"Successfully synced {total_synced} electricity discos")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_electricity_services.short_description = "Sync Electricity from Active Providers"

    def sync_internet_services(self, request, queryset):
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += impl.sync_internet()
            self.message_user(request, f"Successfully synced {total_synced} internet packages")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_internet_services.short_description = "Sync Internet from Active Providers"

    def sync_education_services(self, request, queryset):
        configs = VTUProviderConfig.objects.filter(is_active=True)
        total_synced = 0
        try:
            for config in configs:
                impl = ProviderRouter.get_provider_implementation(config.name)
                if impl:
                    total_synced += impl.sync_education()
            self.message_user(request, f"Successfully synced {total_synced} education pins")
        except Exception as e:
            self.message_user(request, f"An error occurred: {str(e)}", level='error')
    sync_education_services.short_description = "Sync Education from Active Providers"


@admin.register(DataService)
class DataServiceAdmin(admin.ModelAdmin, ProviderSyncMixin):
    list_display= ["network_image", "service_name", "service_id", "provider", "is_active", "data_plans_count"]
    list_display_links = ["service_name", "network_image"]
    list_filter = ["provider", "is_active"]
    actions = ["sync_data_services", "sync_all_services"]
    
    def network_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="150" style="object-fit: cover; border-radius: 6px;" />',
                obj.image.url
            )
        return "#"
    network_image.short_description = "Preview"

    def data_plans_count(self, obj):
        from django.urls import reverse
        count = obj.variations.count()
        url = reverse('admin:orders_datavariation_changelist') + f'?service__id__exact={obj.id}'
        return format_html('<a href="{}">{} Plans</a>', url, count)
    data_plans_count.short_description = "Packages"


@admin.register(DataVariation)
class DataVariationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "service",
        "selling_price",
        "agent_price",
        "developer_price",
        "is_active",
        "sales_count",
        "updated_at",
    ]

    list_filter = ["service", "is_active", "updated_at"]
    ordering = ["service__service_name", "selling_price"]
    search_fields = ["name", "service__service_name"]
    list_per_page = 50

    def sales_count(self, obj):
        from django.urls import reverse
        count = obj.sales.count()
        url = reverse('admin:orders_purchase_changelist') + f'?data_variation__id__exact={obj.id}'
        return format_html('<a href="{}">{} Purchases</a>', url, count)
    sales_count.short_description = "Purchases"
    
    actions = ["make_as_active"]

    def make_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} plan(s) marked as active.")
    make_as_active.short_description = "Mark selected plans as active"


@admin.register(ElectricityService)
class ElectricityServiceAdmin(admin.ModelAdmin, ProviderSyncMixin):
    list_display= [
        "service_name", 
        "service_id", 
        "provider",
        "is_active",
        "variation_count",
    ]
    list_display_links = ["service_name"]
    list_filter = ["provider", "is_active"]
    list_per_page= 100
    actions = ["sync_electricity_services", "sync_all_services"]

    def variation_count(self, obj):
        from django.urls import reverse
        count = obj.variations.count()
        url = reverse('admin:orders_electricityvariation_changelist') + f'?service__id__exact={obj.id}'
        return format_html('<a href="{}">{} Types</a>', url, count)
    variation_count.short_description = "Disco Types"

@admin.register(ElectricityVariation)
class ElectricityVariationAdmin(admin.ModelAdmin):
    list_display = ["name", "service", "variation_id", "selling_price", "agent_price", "developer_price", "is_active", "sales_count"]
    list_filter = ["service", "is_active"]
    list_per_page = 50

    def sales_count(self, obj):
        from django.urls import reverse
        count = obj.sales.count()
        url = reverse('admin:orders_purchase_changelist') + f'?electricity_variation__id__exact={obj.id}'
        return format_html('<a href="{}">{} Purchases</a>', url, count)
    sales_count.short_description = "Purchases"


@admin.register(TVService)
class TVServiceAdmin(admin.ModelAdmin, ProviderSyncMixin):
    list_display= [
        "service_name", 
        "service_id", 
        "provider",
        "is_active",
        "variation_count",
    ]
    list_display_links = ["service_name"]
    list_filter = ["provider", "is_active"]
    list_per_page= 100
    actions = ["sync_cable_services", "sync_all_services"]

    def variation_count(self, obj):
        from django.urls import reverse
        count = obj.variations.count()
        url = reverse('admin:orders_tvvariation_changelist') + f'?service__id__exact={obj.id}'
        return format_html('<a href="{}">{} Packages</a>', url, count)
    variation_count.short_description = "Packages"


@admin.register(TVVariation)
class TVVariationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "service",
        "variation_id",
        "selling_price",
        "agent_price",
        "developer_price",
        "is_active",
        "sales_count",
        "created_at",
        "updated_at",
    ]

    list_filter = ["service", "is_active"]
    ordering = ["service__service_name", "name", "selling_price"]
    list_per_page = 50

    def sales_count(self, obj):
        from django.urls import reverse
        count = obj.sales.count()
        url = reverse('admin:orders_purchase_changelist') + f'?tv_variation__id__exact={obj.id}'
        return format_html('<a href="{}">{} Purchases</a>', url, count)
    sales_count.short_description = "Purchases"
    
    actions = ["make_as_active"]

    def make_as_active(self, request, queryset):
        updated =queryset.update(is_active=True)
        self.message_user(request, f"{updated} plan(s) marked as active.")
    make_as_active.short_description = "Mark selected plans as active"


@admin.register(InternetService)
class InternetServiceAdmin(admin.ModelAdmin, ProviderSyncMixin):
    list_display = ["service_name", "service_id", "provider", "is_active"]
    list_filter = ["provider", "is_active"]
    actions = ["sync_internet_services", "sync_all_services"]

@admin.register(InternetVariation)
class InternetVariationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "service",
        "variation_id",
        "selling_price",
        "agent_price",
        "developer_price",
        "is_active",
        "sales_count",
        "created_at",
        "updated_at",
    ]

    list_filter = ["service", "is_active"]
    ordering = ["name", "selling_price"]
    list_per_page = 50
    actions = ["make_as_active", "sync_internet_services", "sync_all_services"]

    def sales_count(self, obj):
        from django.urls import reverse
        count = obj.sales.count()
        url = reverse('admin:orders_purchase_changelist') + f'?internet_variation__id__exact={obj.id}'
        return format_html('<a href="{}">{} Purchases</a>', url, count)
    sales_count.short_description = "Purchases"

    def make_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} plan(s) marked as active.")
    make_as_active.short_description = "Mark selected plans as active"


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        "purchase_type",
        "user",
        "service_name",
        "reference",
        "amount",
        "beneficiary",
        "status",
        "provider",
        "initiator",
        "time",
    ]
    
    readonly_fields = [
        "user", "purchase_type", "amount", "beneficiary", 
        "status", "reference", "time", 
        "initiator", "initiated_by", "airtime_service",
        "data_variation", "electricity_service", "tv_variation",
        "internet_variation", "provider", "provider_response"
    ]
    fieldsets = [
        ("Purchase Details", {
            "fields": ("user", "purchase_type", "amount", "beneficiary", "service_name", "time")
        }),
        ("Transaction Status", {
            "fields": ("status", "reference", "provider", "initiator", "initiated_by")
        }),
        ("Service Data", {
            "fields": ("airtime_service", "data_variation", "electricity_service", "tv_variation", "internet_variation")
        }),
        ("API Response", {
            "fields": ("provider_response",),
            "classes": ("collapse",)
        }),
    ]
    list_filter = ["purchase_type", "status", "provider", "initiator", "time"]
    search_fields = ["user__email", "user__phone_number", "reference", "beneficiary"]
    list_per_page = 100    
    change_list_template = "admin/orders/purchase/change_list.html"

    actions = ["query_status", "mark_as_failed_and_refund"]

    def mark_as_failed_and_refund(self, request, queryset):
        for purchase in queryset:
            if purchase.status == "refunded":
                self.message_user(request, f"Purchase {purchase.reference} is already refunded.", level='warning')
                continue

            try:
                with db_transaction.atomic():
                    purchase.status = "refunded"
                    purchase.save(update_fields=["status"])

                    fund_wallet(
                        user_id=purchase.user.id,
                        amount=purchase.amount,
                        description=f"Refund: Admin marked {purchase.purchase_type} purchase failed ({purchase.reference})",
                        initiator="admin",
                        initiated_by=request.user
                    )
                
                self.message_user(request, f"Successfully refunded {purchase.reference}")
            except Exception as e:
                self.message_user(request, f"Error processing {purchase.reference}: {str(e)}", level='error')

    mark_as_failed_and_refund.short_description = "Mark as Failed and Refund"

    def query_status(self, request, queryset):
        from .router import ProviderRouter
        success_count = 0
        failed_count = 0
        
        for purchase in queryset:
            if not purchase.provider:
                self.message_user(request, f"Purchase {purchase.reference} has no known provider to query.", level='warning')
                continue
                
            try:
                impl = ProviderRouter.get_provider_implementation(purchase.provider.name)
                if not impl:
                    self.message_user(request, f"Provider {purchase.provider.name} implementation not found.", level='warning')
                    continue

                resp = impl.query_transaction(reference=purchase.reference)
                
                # Update purchase details safely
                if isinstance(purchase.provider_response, dict):
                    purchase.provider_response["query_response"] = resp
                else:
                    purchase.provider_response = {"query_response": resp}

                new_status = resp.get("status")
                
                terminal_fail = False
                if new_status == "SUCCESS":
                    purchase.status = "success"
                    success_count += 1
                elif new_status == "FAILED":
                    if purchase.status != "refunded":
                        purchase.status = "refunded"
                        terminal_fail = True
                        failed_count += 1
                
                with db_transaction.atomic():
                    purchase.save()
                    if terminal_fail:
                        fund_wallet(
                            user_id=purchase.user.id,
                            amount=purchase.amount,
                            description=f"Refund: Query returned failed for {purchase.purchase_type} ({purchase.reference})",
                            initiator="admin",
                            initiated_by=request.user
                        )
                
                self.message_user(request, f"Updated {purchase.reference}: {purchase.status}")
            
            except NotImplementedError:
                self.message_user(request, f"Provider {purchase.provider.name} does not support query_transaction.", level='warning')
            except Exception as e:
                self.message_user(request, f"Error querying {purchase.reference}: {str(e)}", level='error')

        self.message_user(request, f"Query completed. Found {success_count} success and {failed_count} new terminal failures.")

    query_status.short_description = "Recheck Status from Provider"

    def service_name(self, obj):
        if obj.airtime_service:
            return obj.airtime_service.service_name
        elif obj.electricity_service:
            return obj.electricity_service.service_name
        elif obj.tv_variation:
            return obj.tv_variation.service.service_name
        elif obj.internet_variation:
            return "Internet Subscription"
        elif obj.data_variation:
            return obj.data_variation.service.service_name
        return "-"
    service_name.short_description = "Service Name"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_admin_purchase_link'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return True # We will use a custom view for adding
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('admin-purchase/', self.admin_site.admin_view(self.admin_purchase_view), name='orders-admin-purchase'),
        ]
        return custom_urls + urls

    def admin_purchase_view(self, request):
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from users.models import User
        from orders.utils.purchase_logic import process_vtu_purchase
        import uuid

        if request.method == "POST":
            user_id = request.POST.get("user")
            purchase_type = request.POST.get("purchase_type")
            beneficiary = request.POST.get("beneficiary")
            
            try:
                user = User.objects.get(id=user_id)
                
                if purchase_type == "AIRTIME":
                    network_id = request.POST.get("network")
                    amount = float(request.POST.get("amount"))
                    network = AirtimeNetwork.objects.get(id=network_id)
                    
                    ref = f"ADM-AIR-{uuid.uuid4().hex[:8].upper()}"
                    res = process_vtu_purchase(
                        user=user,
                        purchase_type="airtime",
                        amount=amount,
                        beneficiary=beneficiary,
                        action="buy_airtime",
                        initiator="admin",
                        initiated_by=request.user,
                        service_name=f"{network.service_name} Airtime",
                        reference=ref,
                        phone=beneficiary,
                        network=network.service_id,
                        airtime_service=network
                    )
                    if res.get('status') == 'failed':
                        messages.error(request, f"Purchase Failed: {res.get('error', res.get('res', {}).get('message', 'Unknown Error'))}")
                    else:
                        messages.success(request, "Airtime purchase successful")

                elif purchase_type == "DATA":
                    variation_id = request.POST.get("variation")
                    variation = DataVariation.objects.get(id=variation_id)
                    amount = float(variation.selling_price)
                    
                    ref = f"ADM-DAT-{uuid.uuid4().hex[:8].upper()}"
                    res = process_vtu_purchase(
                        user=user,
                        purchase_type="data",
                        amount=amount,
                        beneficiary=beneficiary,
                        action="buy_data",
                        initiator="admin",
                        initiated_by=request.user,
                        service_name=f"{variation.name} Data",
                        reference=ref,
                        phone=beneficiary,
                        network=variation.service.service_id,
                        plan_id=variation.variation_id,
                        data_variation=variation
                    )
                    if res.get('status') == 'failed':
                        messages.error(request, f"Purchase Failed: {res.get('error', res.get('res', {}).get('message', 'Unknown Error'))}")
                    else:
                        messages.success(request, "Data purchase successful")
                
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            
            return redirect("..")

        # GET request: Show form
        context = {
            **self.admin_site.each_context(request),
            "users": User.objects.all(),
            "networks": AirtimeNetwork.objects.all(),
            "variations": DataVariation.objects.filter(is_active=True).select_related('service'),
            "title": "Perform Admin VTU Purchase"
        }
        return render(request, "admin/orders/admin_purchase.html", context)

    def has_change_permission(self, request, obj = ...):
        return False


@admin.register(AirtimeNetwork)
class AirtimeNetworkAdmin(admin.ModelAdmin, ProviderSyncMixin):
    list_display= [
        "network_image",
        "service_name", 
        "service_id", 
        "provider",
        "selling_price",
        "agent_price",
        "developer_price",
        "is_active",
        "sales_count",
    ]

    list_display_links = ["network_image","service_name"]
    list_filter = ["provider", "is_active"]
    actions = ["sync_airtime_services", "sync_all_services"]

    def network_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="150" style="object-fit: cover; border-radius: 6px;" />',
                obj.image.url
            )
        return "#"
    network_image.short_description = "Preview"

    def sales_count(self, obj):
        from django.urls import reverse
        count = obj.sales.count()
        url = reverse('admin:orders_purchase_changelist') + f'?airtime_service__id__exact={obj.id}'
        return format_html('<a href="{}">{} Sales</a>', url, count)
    sales_count.short_description = "Sales"

    list_per_page= 100

@admin.register(EducationService)
class EducationServiceAdmin(admin.ModelAdmin, ProviderSyncMixin):
    list_display = ["service_name", "service_id", "provider", "is_active", "variation_count"]
    list_display_links = ["service_name"]
    list_filter = ["provider", "is_active"]
    list_per_page = 100
    actions = ["sync_education_services", "sync_all_services"]

    def variation_count(self, obj):
        from django.urls import reverse
        count = obj.variations.count()
        url = reverse('admin:orders_educationvariation_changelist') + f'?service__id__exact={obj.id}'
        return format_html('<a href="{}">{} Plans</a>', url, count)
    variation_count.short_description = "Packages"

@admin.register(EducationVariation)
class EducationVariationAdmin(admin.ModelAdmin):
    list_display = [
        "name", 
        "service_name", 
        "variation_id", 
        "selling_price", 
        "agent_price",
        "developer_price",
        "is_active",
        "sales_count"
    ]
    list_filter = ["service", "is_active"]
    ordering = ["name", "selling_price"]
    list_per_page = 50

    def service_name(self, obj):
        return obj.service.service_name
    service_name.short_description = "Service"

    def sales_count(self, obj):
        from django.urls import reverse
        count = obj.sales.count()
        url = reverse('admin:orders_purchase_changelist') + f'?education_variation__id__exact={obj.id}'
        return format_html('<a href="{}">{} Sales</a>', url, count)
    sales_count.short_description = "Sales"


# ─── VTU Routing Admin ───

class ServiceFallbackInline(admin.TabularInline):
    model = ServiceFallback
    extra = 1

@admin.register(VTUProviderConfig)
class VTUProviderConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'max_retries', 'auto_refund_on_failure', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    fieldsets = (
        ("Provider Status", {
            "fields": ("name", "is_active")
        }),
        ("API Configuration", {
            "fields": ("api_key", "secret_key", "public_key", "user_id", "session_id", "base_url"),
            "description": 'Enter the raw API credentials provided by the VTU service.'
        }),
        ("Failover Behavior", {
            "fields": ("max_retries", "auto_refund_on_failure"),
        }),
    )

@admin.register(ServiceRouting)
class ServiceRoutingAdmin(admin.ModelAdmin):
    list_display = ('service', 'primary_provider_name', 'pricing_mode', 'customer_margin', 'agent_margin', 'developer_margin')
    inlines = [ServiceFallbackInline]
    
    def primary_provider_name(self, obj):
        return obj.primary_provider.get_name_display() if obj.primary_provider else "None"
    primary_provider_name.short_description = "Primary Provider"
