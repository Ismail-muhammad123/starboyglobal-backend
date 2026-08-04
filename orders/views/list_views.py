from rest_framework import generics, permissions
from rest_framework.response import Response
from django.db.models import Q
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from orders.models import (
    DataService, DataVariation, AirtimeNetwork, 
    ElectricityService, ElectricityVariation, TVService, TVVariation, 
    InternetService, InternetVariation, EducationService, EducationVariation,
    ServiceRouting
)
from orders.serializers import (
    DataServiceSerializer, DataVariationSerializer,
    AirtimeNetworkSerializer, TVServiceSerializer,
    TVVariationSerializer, InternetServiceSerializer, InternetVariationSerializer,
    EducationServiceSerializer, EducationVariationSerializer,
    ElectricityServiceSerializer, ElectricityVariationSerializer
)
from orders.router import ProviderRouter
from orders.utils.pricing import get_provider_service_config, resolve_margin_for_role, apply_margin


def _active_services_with_routing_fallback(model, service_type):
    """
    Prefer active services for the routed provider.
    If no rows exist for that provider, gracefully fall back to all active services.
    """
    active_qs = model.objects.filter(is_active=True).order_by('id')
    routing = ServiceRouting.objects.filter(service=service_type).first()
    if routing and routing.primary_provider:
        routed_qs = active_qs.filter(provider=routing.primary_provider)
        if routed_qs.exists():
            return routed_qs
    return active_qs


def _filter_variations_by_service_param(queryset, service_param):
    """
    Accept both internal PK (`service.id`) and provider service code (`service.service_id`)
    for compatibility with different clients.
    """
    if not service_param:
        return queryset
    return queryset.filter(Q(service__id=service_param) | Q(service__service_id=service_param))


def _fetch_live_catalogue_if_enabled(request, service_type, is_variation=False):
    """
    Checks if primary provider has catalogue_source == 'live' for this service_type.
    If so, fetches live data from provider API, applies margin for request.user.role, caches, and returns.
    Returns (True, response_data) if handled live, or (False, None) if DB should be used.
    """
    routing = ServiceRouting.objects.filter(service=service_type).first()
    if not routing or not routing.primary_provider or not routing.primary_provider.is_active:
        return False, None

    provider = routing.primary_provider
    config = get_provider_service_config(provider, service_type)
    if config.get('catalogue_source') != 'live':
        return False, None

    bypass_cache = request.query_params.get('bypass_cache') == '1'
    user = getattr(request, 'user', None)
    role = getattr(user, 'role', 'customer') if user and user.is_authenticated else 'customer'
    cache_ttl = config.get('live_cache_ttl_seconds', 300)
    cache_key = f"live_cat:{provider.id}:{service_type}:{is_variation}:{role}"

    if not bypass_cache and cache_ttl > 0:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return True, cached_data

    impl = ProviderRouter.get_provider_implementation(provider.name)
    if not impl:
        return False, None

    method_name = f"fetch_{service_type}_live"
    fetch_func = getattr(impl, method_name, None)
    if not fetch_func:
        return False, None

    raw_items = fetch_func()
    margin_type, margin_value = resolve_margin_for_role(config, role)

    priced_items = []
    for item in raw_items:
        item_copy = dict(item)
        cost_price = item_copy.get('cost_price', 0.0)
        selling_price = float(apply_margin(cost_price, margin_value, margin_type))
        item_copy['cost_price'] = float(cost_price)
        item_copy['selling_price'] = selling_price
        item_copy['agent_price'] = float(apply_margin(cost_price, config.get('agent_margin_value', 0), config.get('agent_margin_type', 'flat')))
        item_copy['developer_price'] = float(apply_margin(cost_price, config.get('developer_margin_value', 0), config.get('developer_margin_type', 'flat')))
        priced_items.append(item_copy)

    if not bypass_cache and cache_ttl > 0:
        cache.set(cache_key, priced_items, cache_ttl)

    return True, priced_items


@extend_schema(tags=["Orders - Data"])
class DataServicesListView(generics.ListAPIView):
    """List available data networks/services for the active provider."""
    serializer_class = DataServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'data', is_variation=False)
        if handled:
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return _active_services_with_routing_fallback(DataService, 'data')


@extend_schema(tags=["Orders - Data"])
class DataVariationsListView(generics.ListAPIView):
    """List available data plans/variations. Filter by service_id query param or network_id in URL."""
    serializer_class = DataVariationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'data', is_variation=True)
        if handled:
            # Filter live variation data if service_id / network_id param is passed
            service_id = self.kwargs.get("network_id") or request.query_params.get("service_id")
            if service_id:
                data = [item for item in data if str(item.get("service_id")) == str(service_id)]
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = DataVariation.objects.filter(is_active=True).order_by('id')
        network_id = self.kwargs.get("network_id")
        if network_id:
            return queryset.filter(service__id=network_id)
        service_id = self.request.query_params.get("service_id")
        return _filter_variations_by_service_param(queryset, service_id)


@extend_schema(tags=["Orders - Airtime"])
class AirtimeNetworkListView(generics.ListAPIView):
    """List available airtime networks for the active provider."""
    serializer_class = AirtimeNetworkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'airtime', is_variation=False)
        if handled:
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return _active_services_with_routing_fallback(AirtimeNetwork, 'airtime')


@extend_schema(tags=["Orders - Electricity"])
class ElectricityServiceListView(generics.ListAPIView):
    """List available electricity distribution companies (DISCOs)."""
    serializer_class = ElectricityServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'electricity', is_variation=False)
        if handled:
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return _active_services_with_routing_fallback(ElectricityService, 'electricity')


@extend_schema(tags=["Orders - Electricity"])
class ElectricityVariationListView(generics.ListAPIView):
    """List available electricity plans/variations. Filter by service_id query param or network_id in URL."""
    serializer_class = ElectricityVariationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'electricity', is_variation=True)
        if handled:
            service_id = self.kwargs.get("network_id") or request.query_params.get("service_id")
            if service_id:
                data = [item for item in data if str(item.get("service_id")) == str(service_id)]
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ElectricityVariation.objects.filter(is_active=True).order_by('id')
        network_id = self.kwargs.get("network_id")
        if network_id:
            return queryset.filter(service__id=network_id)
        service_id = self.request.query_params.get("service_id")
        return _filter_variations_by_service_param(queryset, service_id)


@extend_schema(tags=["Orders - Cable TV"])
class TVServicesListView(generics.ListAPIView):
    """List available Cable TV services (DSTV, GOTV, Startimes)."""
    serializer_class = TVServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'tv', is_variation=False)
        if handled:
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return _active_services_with_routing_fallback(TVService, 'tv')


@extend_schema(tags=["Orders - Cable TV"])
class TVPackagesListView(generics.ListAPIView):
    """List available TV bouquet packages. Filter by service_id query param or network_id in URL."""
    serializer_class = TVVariationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'tv', is_variation=True)
        if handled:
            service_id = self.kwargs.get("network_id") or request.query_params.get("service_id")
            if service_id:
                data = [item for item in data if str(item.get("service_id")) == str(service_id)]
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = TVVariation.objects.filter(is_active=True).order_by('id')
        network_id = self.kwargs.get("network_id")
        if network_id:
            return queryset.filter(service__id=network_id)
        service_id = self.request.query_params.get("service_id")
        return _filter_variations_by_service_param(queryset, service_id)


@extend_schema(tags=["Orders - Internet"])
class InternetServicesListView(generics.ListAPIView):
    """List available Internet services (Smile, Spectranet, etc.)."""
    serializer_class = InternetServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'internet', is_variation=False)
        if handled:
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return _active_services_with_routing_fallback(InternetService, 'internet')


@extend_schema(tags=["Orders - Internet"])
class InternetPackagesListView(generics.ListAPIView):
    """List available Internet data packages. Filter by service_id query param or network_id in URL."""
    serializer_class = InternetVariationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'internet', is_variation=True)
        if handled:
            service_id = self.kwargs.get("network_id") or request.query_params.get("service_id")
            if service_id:
                data = [item for item in data if str(item.get("service_id")) == str(service_id)]
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = InternetVariation.objects.filter(is_active=True).order_by('id')
        network_id = self.kwargs.get("network_id")
        if network_id:
            return queryset.filter(service__id=network_id)
        service_id = self.request.query_params.get("service_id")
        return _filter_variations_by_service_param(queryset, service_id)


@extend_schema(tags=["Orders - Education"])
class EducationServiceListView(generics.ListAPIView):
    """List available education services (WAEC, NECO, etc.)."""
    serializer_class = EducationServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'education', is_variation=False)
        if handled:
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return _active_services_with_routing_fallback(EducationService, 'education')


@extend_schema(tags=["Orders - Education"])
class EducationVariationListView(generics.ListAPIView):
    """List available education PIN variations. Filter by service_id query param or network_id in URL."""
    serializer_class = EducationVariationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        handled, data = _fetch_live_catalogue_if_enabled(request, 'education', is_variation=True)
        if handled:
            service_id = self.kwargs.get("network_id") or request.query_params.get("service_id")
            if service_id:
                data = [item for item in data if str(item.get("service_id")) == str(service_id)]
            return Response(data)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = EducationVariation.objects.filter(is_active=True).order_by('id')
        network_id = self.kwargs.get("network_id")
        if network_id:
            return queryset.filter(service__id=network_id)
        service_id = self.request.query_params.get("service_id")
        return _filter_variations_by_service_param(queryset, service_id)


