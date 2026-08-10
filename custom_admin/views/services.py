from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
import json
from custom_admin.mixins import PortalPermissionMixin
from orders.models import (
    AirtimeNetwork, DataService, DataVariation,
    TVService, TVVariation, ElectricityService, ElectricityVariation,
    InternetService, InternetVariation, EducationService, EducationVariation,
    VTUProviderConfig
)


def get_per_page(request, default=25):
    per_page = request.GET.get('per_page', default)
    try:
        per_page = int(per_page)
        if per_page not in [25, 50, 100, 200]:
            per_page = default
    except (ValueError, TypeError):
        per_page = default
    return per_page


# --- AIRTIME ---
class AirtimeNetworkListView(PortalPermissionMixin, View):
    required_permission = ('orders.AirtimeNetwork', 'view')

    def get(self, request):
        qs = AirtimeNetwork.objects.all().select_related('provider').annotate(sales_count=Count('sales'))

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(service_name__icontains=search) | Q(service_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        sort = request.GET.get('sort', 'name')
        sort_map = {
            'name': 'service_name', 'name_desc': '-service_name',
            'cost': 'cost_price', 'cost_desc': '-cost_price',
            'price': 'selling_price', 'price_desc': '-selling_price',
            'agent': 'agent_price', 'agent_desc': '-agent_price',
            'sales': 'sales_count', 'sales_desc': '-sales_count',
        }
        qs = qs.order_by(sort_map.get(sort, 'service_name'))

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/airtime/networks_list.html', {
            'networks': page_obj,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'name',
            'per_page': per_page,
        })


class AirtimeNetworkCreateView(PortalPermissionMixin, View):
    required_permission = ('orders.AirtimeNetwork', 'add')

    def post(self, request):
        service_name = request.POST.get('service_name', '').strip()
        service_id = request.POST.get('service_id', '').strip()
        provider_id = request.POST.get('provider_id')

        if not service_name or not service_id:
            return JsonResponse({'status': 'error', 'message': 'Service name and ID are required.'}, status=400)

        provider = VTUProviderConfig.objects.filter(pk=provider_id).first() if provider_id else None
        net = AirtimeNetwork.objects.create(
            service_name=service_name,
            service_id=service_id,
            provider=provider,
            is_active=request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on',
            discount=float(request.POST.get('discount', 0)),
            agent_discount=float(request.POST.get('agent_discount', 0)),
        )
        return JsonResponse({'status': 'success', 'message': f'Airtime network {net.service_name} created successfully.'})


class AirtimeNetworkDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.AirtimeNetwork', 'view')

    def get(self, request, pk):
        network = get_object_or_404(AirtimeNetwork, pk=pk)
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/airtime/network_detail.html', {
            'network': network,
            'providers': providers
        })

    def post(self, request, pk):
        network = get_object_or_404(AirtimeNetwork, pk=pk)
        network.service_name = request.POST.get('service_name', network.service_name).strip()
        network.service_id = request.POST.get('service_id', network.service_id).strip()
        provider_id = request.POST.get('provider_id')
        if provider_id:
            network.provider = VTUProviderConfig.objects.filter(pk=provider_id).first()
        network.is_active = request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on'
        try:
            network.discount = float(request.POST.get('discount', network.discount))
            network.agent_discount = float(request.POST.get('agent_discount', network.agent_discount))
        except ValueError: pass
        network.save()
        return JsonResponse({'status': 'success', 'message': f'Airtime network {network.service_name} updated successfully.'})


# --- DATA SERVICES & VARIATIONS ---
class DataServiceListView(PortalPermissionMixin, View):
    required_permission = ('orders.DataService', 'view')

    def get(self, request):
        qs = DataService.objects.all().select_related('provider')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(service_name__icontains=search) | Q(service_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        sort = request.GET.get('sort', 'service_name')
        if sort == 'service_name_desc':
            qs = qs.order_by('-service_name')
        else:
            qs = qs.order_by('service_name')

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/data/services_list.html', {
            'services': page_obj,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'service_name',
            'per_page': per_page,
        })


class DataServiceCreateView(PortalPermissionMixin, View):
    required_permission = ('orders.DataService', 'add')

    def post(self, request):
        service_name = request.POST.get('service_name', '').strip()
        service_id = request.POST.get('service_id', '').strip()
        provider_id = request.POST.get('provider_id')

        if not service_name or not service_id:
            return JsonResponse({'status': 'error', 'message': 'Service name and ID are required.'}, status=400)

        provider = VTUProviderConfig.objects.filter(pk=provider_id).first() if provider_id else None
        srv = DataService.objects.create(
            service_name=service_name,
            service_id=service_id,
            provider=provider,
            is_active=request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on',
        )
        return JsonResponse({'status': 'success', 'message': f'Data service {srv.service_name} created successfully.'})


class DataServiceDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.DataService', 'view')

    def get(self, request, pk):
        service = get_object_or_404(DataService, pk=pk)
        variations = DataVariation.objects.filter(service=service)
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/data/service_detail.html', {
            'service': service,
            'variations': variations,
            'providers': providers
        })

    def post(self, request, pk):
        service = get_object_or_404(DataService, pk=pk)
        service.service_name = request.POST.get('service_name', service.service_name).strip()
        service.service_id = request.POST.get('service_id', service.service_id).strip()
        provider_id = request.POST.get('provider_id')
        if provider_id:
            service.provider = VTUProviderConfig.objects.filter(pk=provider_id).first()
        service.is_active = request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on'
        service.save()
        return JsonResponse({'status': 'success', 'message': f'Data service {service.service_name} updated successfully.'})


class DataVariationListView(PortalPermissionMixin, View):
    required_permission = ('orders.DataVariation', 'view')

    def get(self, request):
        qs = DataVariation.objects.all().select_related('service', 'service__provider').annotate(sales_count=Count('sales'))

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(variation_id__icontains=search) | Q(service__service_name__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        service_filter = request.GET.get('service')
        if service_filter:
            qs = qs.filter(service_id=service_filter)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(service__provider_id=provider_filter)

        sort = request.GET.get('sort', 'name')
        sort_map = {
            'name': 'name', 'name_desc': '-name',
            'cost': 'cost_price', 'cost_desc': '-cost_price',
            'price': 'selling_price', 'price_desc': '-selling_price',
            'agent': 'agent_price', 'agent_desc': '-agent_price',
            'developer': 'developer_price', 'developer_desc': '-developer_price',
            'sales': 'sales_count', 'sales_desc': '-sales_count',
        }
        qs = qs.order_by(sort_map.get(sort, 'name'))

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        services = DataService.objects.all().select_related('provider')
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/data/variations_list.html', {
            'variations': page_obj,
            'services': services,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'service_filter': service_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'name',
            'per_page': per_page,
        })


class DataVariationCreateView(PortalPermissionMixin, View):
    required_permission = ('orders.DataVariation', 'add')

    def post(self, request):
        service_id = request.POST.get('service_id')
        name = request.POST.get('name', '').strip()
        variation_id = request.POST.get('variation_id', '').strip()

        if not service_id or not name or not variation_id:
            return JsonResponse({'status': 'error', 'message': 'Service, name, and variation ID are required.'}, status=400)

        service = get_object_or_404(DataService, pk=service_id)
        var_obj = DataVariation.objects.create(
            service=service,
            name=name,
            variation_id=variation_id,
            cost_price=float(request.POST.get('cost_price', 0)),
            selling_price=float(request.POST.get('selling_price', 0)),
            agent_price=float(request.POST.get('agent_price', 0)),
            developer_price=float(request.POST.get('developer_price', 0)),
            is_active=request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on',
        )
        return JsonResponse({'status': 'success', 'message': f'Data plan {var_obj.name} created successfully.'})


class DataVariationDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.DataVariation', 'view')

    def get(self, request, pk):
        variation = get_object_or_404(DataVariation, pk=pk)
        services = DataService.objects.all()
        return render(request, 'custom_admin/services/data/variation_detail.html', {
            'variation': variation,
            'services': services
        })

    def post(self, request, pk):
        variation = get_object_or_404(DataVariation, pk=pk)
        variation.name = request.POST.get('name', variation.name).strip()
        variation.variation_id = request.POST.get('variation_id', variation.variation_id).strip()
        try:
            variation.cost_price = float(request.POST.get('cost_price', variation.cost_price))
            variation.selling_price = float(request.POST.get('selling_price', variation.selling_price))
            variation.agent_price = float(request.POST.get('agent_price', variation.agent_price))
            variation.developer_price = float(request.POST.get('developer_price', variation.developer_price))
        except ValueError: pass
        variation.is_active = request.POST.get('is_active') == 'true' or request.POST.get('is_active') == 'on'
        variation.save()
        return JsonResponse({'status': 'success', 'message': f'Data plan {variation.name} updated successfully.'})


# --- TV SERVICES & VARIATIONS ---
class TVServiceListView(PortalPermissionMixin, View):
    required_permission = ('orders.TVService', 'view')

    def get(self, request):
        qs = TVService.objects.all().select_related('provider')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(service_name__icontains=search) | Q(service_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/tv/services_list.html', {
            'services': page_obj,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'per_page': per_page,
        })


class TVServiceDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.TVService', 'view')

    def get(self, request, pk):
        service = get_object_or_404(TVService, pk=pk)
        variations = TVVariation.objects.filter(service=service)
        return render(request, 'custom_admin/services/tv/service_detail.html', {
            'service': service,
            'variations': variations
        })


class TVVariationListView(PortalPermissionMixin, View):
    required_permission = ('orders.TVVariation', 'view')

    def get(self, request):
        qs = TVVariation.objects.all().select_related('service', 'service__provider').annotate(sales_count=Count('sales'))

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(variation_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        service_filter = request.GET.get('service')
        if service_filter:
            qs = qs.filter(service_id=service_filter)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(service__provider_id=provider_filter)

        sort = request.GET.get('sort', 'name')
        sort_map = {
            'name': 'name', 'name_desc': '-name',
            'cost': 'cost_price', 'cost_desc': '-cost_price',
            'price': 'selling_price', 'price_desc': '-selling_price',
            'agent': 'agent_price', 'agent_desc': '-agent_price',
            'developer': 'developer_price', 'developer_desc': '-developer_price',
            'sales': 'sales_count', 'sales_desc': '-sales_count',
        }
        qs = qs.order_by(sort_map.get(sort, 'name'))

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        services = TVService.objects.all().select_related('provider')
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/tv/variations_list.html', {
            'variations': page_obj,
            'services': services,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'service_filter': service_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'name',
            'per_page': per_page,
        })


class TVVariationDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.TVVariation', 'view')

    def get(self, request, pk):
        variation = get_object_or_404(TVVariation, pk=pk)
        return render(request, 'custom_admin/services/tv/variation_detail.html', {'variation': variation})


# --- ELECTRICITY SERVICES & VARIATIONS ---
class ElectricityServiceListView(PortalPermissionMixin, View):
    required_permission = ('orders.ElectricityService', 'view')

    def get(self, request):
        qs = ElectricityService.objects.all().select_related('provider')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(service_name__icontains=search) | Q(service_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/electricity/services_list.html', {
            'services': page_obj,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'per_page': per_page,
        })


class ElectricityServiceDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.ElectricityService', 'view')

    def get(self, request, pk):
        service = get_object_or_404(ElectricityService, pk=pk)
        variations = ElectricityVariation.objects.filter(service=service)
        return render(request, 'custom_admin/services/electricity/service_detail.html', {
            'service': service,
            'variations': variations
        })


class ElectricityVariationListView(PortalPermissionMixin, View):
    required_permission = ('orders.ElectricityVariation', 'view')

    def get(self, request):
        qs = ElectricityVariation.objects.all().select_related('service', 'service__provider').annotate(sales_count=Count('sales'))

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(variation_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        service_filter = request.GET.get('service')
        if service_filter:
            qs = qs.filter(service_id=service_filter)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(service__provider_id=provider_filter)

        sort = request.GET.get('sort', 'name')
        sort_map = {
            'name': 'name', 'name_desc': '-name',
            'cost': 'cost_price', 'cost_desc': '-cost_price',
            'price': 'selling_price', 'price_desc': '-selling_price',
            'agent': 'agent_price', 'agent_desc': '-agent_price',
            'developer': 'developer_price', 'developer_desc': '-developer_price',
            'sales': 'sales_count', 'sales_desc': '-sales_count',
        }
        qs = qs.order_by(sort_map.get(sort, 'name'))

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        services = ElectricityService.objects.all().select_related('provider')
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/electricity/variations_list.html', {
            'variations': page_obj,
            'services': services,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'service_filter': service_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'name',
            'per_page': per_page,
        })


class ElectricityVariationDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.ElectricityVariation', 'view')

    def get(self, request, pk):
        variation = get_object_or_404(ElectricityVariation, pk=pk)
        return render(request, 'custom_admin/services/electricity/variation_detail.html', {'variation': variation})


# --- INTERNET SERVICES & VARIATIONS ---
class InternetServiceListView(PortalPermissionMixin, View):
    required_permission = ('orders.InternetService', 'view')

    def get(self, request):
        qs = InternetService.objects.all().select_related('provider')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(service_name__icontains=search) | Q(service_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/internet/services_list.html', {
            'services': page_obj,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'per_page': per_page,
        })


class InternetServiceDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.InternetService', 'view')

    def get(self, request, pk):
        service = get_object_or_404(InternetService, pk=pk)
        variations = InternetVariation.objects.filter(service=service)
        return render(request, 'custom_admin/services/internet/service_detail.html', {
            'service': service,
            'variations': variations
        })


class InternetVariationListView(PortalPermissionMixin, View):
    required_permission = ('orders.InternetVariation', 'view')

    def get(self, request):
        qs = InternetVariation.objects.all().select_related('service', 'service__provider').annotate(sales_count=Count('sales'))

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(variation_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        service_filter = request.GET.get('service')
        if service_filter:
            qs = qs.filter(service_id=service_filter)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(service__provider_id=provider_filter)

        sort = request.GET.get('sort', 'name')
        sort_map = {
            'name': 'name', 'name_desc': '-name',
            'cost': 'cost_price', 'cost_desc': '-cost_price',
            'price': 'selling_price', 'price_desc': '-selling_price',
            'agent': 'agent_price', 'agent_desc': '-agent_price',
            'developer': 'developer_price', 'developer_desc': '-developer_price',
            'sales': 'sales_count', 'sales_desc': '-sales_count',
        }
        qs = qs.order_by(sort_map.get(sort, 'name'))

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        services = InternetService.objects.all().select_related('provider')
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/internet/variations_list.html', {
            'variations': page_obj,
            'services': services,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'service_filter': service_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'name',
            'per_page': per_page,
        })


class InternetVariationDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.InternetVariation', 'view')

    def get(self, request, pk):
        variation = get_object_or_404(InternetVariation, pk=pk)
        return render(request, 'custom_admin/services/internet/variation_detail.html', {'variation': variation})


# --- EDUCATION SERVICES & VARIATIONS ---
class EducationServiceListView(PortalPermissionMixin, View):
    required_permission = ('orders.EducationService', 'view')

    def get(self, request):
        qs = EducationService.objects.all().select_related('provider')

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(service_name__icontains=search) | Q(service_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(provider_id=provider_filter)

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/education/services_list.html', {
            'services': page_obj,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'provider_filter': provider_filter or '',
            'per_page': per_page,
        })


class EducationServiceDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.EducationService', 'view')

    def get(self, request, pk):
        service = get_object_or_404(EducationService, pk=pk)
        variations = EducationVariation.objects.filter(service=service)
        return render(request, 'custom_admin/services/education/service_detail.html', {
            'service': service,
            'variations': variations
        })


class EducationVariationListView(PortalPermissionMixin, View):
    required_permission = ('orders.EducationVariation', 'view')

    def get(self, request):
        qs = EducationVariation.objects.all().select_related('service', 'service__provider').annotate(sales_count=Count('sales'))

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(variation_id__icontains=search))

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        service_filter = request.GET.get('service')
        if service_filter:
            qs = qs.filter(service_id=service_filter)

        provider_filter = request.GET.get('provider')
        if provider_filter:
            qs = qs.filter(service__provider_id=provider_filter)

        sort = request.GET.get('sort', 'name')
        sort_map = {
            'name': 'name', 'name_desc': '-name',
            'cost': 'cost_price', 'cost_desc': '-cost_price',
            'price': 'selling_price', 'price_desc': '-selling_price',
            'agent': 'agent_price', 'agent_desc': '-agent_price',
            'developer': 'developer_price', 'developer_desc': '-developer_price',
            'sales': 'sales_count', 'sales_desc': '-sales_count',
        }
        qs = qs.order_by(sort_map.get(sort, 'name'))

        per_page = get_per_page(request)
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get('page'))

        services = EducationService.objects.all().select_related('provider')
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/services/education/variations_list.html', {
            'variations': page_obj,
            'services': services,
            'providers': providers,
            'search_query': search or '',
            'status_filter': status_filter or '',
            'service_filter': service_filter or '',
            'provider_filter': provider_filter or '',
            'sort_query': sort or 'name',
            'per_page': per_page,
        })


class EducationVariationDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.EducationVariation', 'view')

    def get(self, request, pk):
        variation = get_object_or_404(EducationVariation, pk=pk)
        return render(request, 'custom_admin/services/education/variation_detail.html', {'variation': variation})


class BulkVariationActionView(PortalPermissionMixin, View):
    required_permission = ('orders.DataVariation', 'change')

    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = request.POST

        item_type = body.get('item_type')
        action = body.get('action')
        raw_ids = body.get('ids', [])

        if isinstance(raw_ids, str):
            ids = [int(i.strip()) for i in raw_ids.split(',') if i.strip().isdigit()]
        elif isinstance(raw_ids, list):
            ids = [int(i) for i in raw_ids if str(i).isdigit()]
        else:
            ids = []

        if not item_type or not action or not ids:
            return JsonResponse({'status': 'error', 'message': 'Invalid item type, action, or IDs provided.'}, status=400)

        model_map = {
            'data_variation': DataVariation,
            'tv_variation': TVVariation,
            'electricity_variation': ElectricityVariation,
            'internet_variation': InternetVariation,
            'education_variation': EducationVariation,
            'airtime_network': AirtimeNetwork,
            'data_service': DataService,
            'tv_service': TVService,
            'electricity_service': ElectricityService,
            'internet_service': InternetService,
            'education_service': EducationService,
        }

        model_cls = model_map.get(item_type)
        if not model_cls:
            return JsonResponse({'status': 'error', 'message': f'Unsupported item type "{item_type}".'}, status=400)

        qs = model_cls.objects.filter(pk__in=ids)
        count = qs.count()

        if count == 0:
            return JsonResponse({'status': 'error', 'message': 'No items found matching the selected IDs.'}, status=404)

        if action == 'activate':
            qs.update(is_active=True)
            msg = f'Successfully activated {count} item(s).'
        elif action == 'deactivate':
            qs.update(is_active=False)
            msg = f'Successfully deactivated {count} item(s).'
        elif action == 'delete':
            qs.delete()
            msg = f'Successfully deleted {count} item(s).'
        else:
            return JsonResponse({'status': 'error', 'message': f'Invalid action "{action}".'}, status=400)

        return JsonResponse({'status': 'success', 'message': msg, 'count': count})


