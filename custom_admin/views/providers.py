from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.db.models import Q
from custom_admin.mixins import PortalPermissionMixin
from orders.models import VTUProviderConfig, ProviderServiceConfig, ServiceRouting, ServiceFallback
from orders.router import ProviderRouter

SERVICE_TYPES = [
    ('airtime', 'Airtime'),
    ('data', 'Data'),
    ('tv', 'Cable TV'),
    ('electricity', 'Electricity'),
    ('internet', 'Internet'),
    ('education', 'Education'),
]


def ensure_provider_service_configs(provider):
    configs = []
    for stype, slabel in SERVICE_TYPES:
        cfg, _ = ProviderServiceConfig.objects.get_or_create(
            provider=provider,
            service_type=stype
        )
        configs.append(cfg)
    return configs


class ProviderListView(PortalPermissionMixin, View):
    required_permission = ('orders.VTUProviderConfig', 'view')

    def get(self, request):
        qs = VTUProviderConfig.objects.all()

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(bank_name__icontains=search) |
                Q(account_number__icontains=search)
            )

        sort = request.GET.get('sort', 'name')
        if sort == 'name_desc':
            qs = qs.order_by('-name')
        elif sort == 'newest':
            qs = qs.order_by('-id')
        elif sort == 'oldest':
            qs = qs.order_by('id')
        else:
            qs = qs.order_by('name')

        provider_data = []
        for p in qs:
            balance = 0.0
            if p.is_active:
                try:
                    impl = ProviderRouter.get_provider_implementation(p.name)
                    if impl:
                        balance = impl.get_wallet_balance()
                except Exception:
                    pass
            provider_data.append({
                'obj': p,
                'balance': balance
            })

        return render(request, 'custom_admin/providers/list.html', {
            'providers': provider_data,
            'status_filter': status_filter or '',
            'search_query': search or '',
            'sort_query': sort or 'name',
        })


class ProviderCreateView(PortalPermissionMixin, View):
    required_permission = ('orders.VTUProviderConfig', 'add')

    def get(self, request):
        provider_choices = VTUProviderConfig.PROVIDER_CHOICES
        return render(request, 'custom_admin/providers/create.html', {
            'provider_choices': provider_choices,
            'service_types': SERVICE_TYPES,
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Provider name/slug is required.'}, status=400)

        if VTUProviderConfig.objects.filter(name=name).exists():
            return JsonResponse({'status': 'error', 'message': f'Provider with name {name} already exists.'}, status=400)

        provider = VTUProviderConfig.objects.create(
            name=name,
            is_active=request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true',
            api_key=request.POST.get('api_key', '').strip(),
            user_id=request.POST.get('user_id', '').strip(),
            session_id=request.POST.get('session_id', '').strip(),
            secret_key=request.POST.get('secret_key', '').strip(),
            base_url=request.POST.get('base_url', '').strip(),
            account_name=request.POST.get('account_name', '').strip(),
            bank_name=request.POST.get('bank_name', '').strip(),
            account_number=request.POST.get('account_number', '').strip(),
            max_retries=int(request.POST.get('max_retries', 3)),
            auto_refund_on_failure=request.POST.get('auto_refund_on_failure') == 'true' or request.POST.get('auto_refund_on_failure') == 'on',
        )

        for stype, _ in SERVICE_TYPES:
            cfg, _ = ProviderServiceConfig.objects.get_or_create(provider=provider, service_type=stype)
            cfg.catalogue_source = request.POST.get(f'catalogue_source_{stype}', 'db')
            cfg.customer_margin_type = request.POST.get(f'customer_margin_type_{stype}', 'flat')
            try:
                cfg.customer_margin_value = float(request.POST.get(f'customer_margin_value_{stype}', 0.0))
            except ValueError: pass
            cfg.agent_margin_type = request.POST.get(f'agent_margin_type_{stype}', 'flat')
            try:
                cfg.agent_margin_value = float(request.POST.get(f'agent_margin_value_{stype}', 0.0))
            except ValueError: pass
            cfg.developer_margin_type = request.POST.get(f'developer_margin_type_{stype}', 'flat')
            try:
                cfg.developer_margin_value = float(request.POST.get(f'developer_margin_value_{stype}', 0.0))
            except ValueError: pass
            cfg.save()

        return JsonResponse({
            'status': 'success',
            'message': f'Provider {provider.get_name_display()} created successfully.',
            'redirect_url': f'/portal/providers/{provider.pk}/'
        })


class ProviderDetailView(PortalPermissionMixin, View):
    required_permission = ('orders.VTUProviderConfig', 'view')

    def get(self, request, pk):
        provider = get_object_or_404(VTUProviderConfig, pk=pk)
        service_configs = ensure_provider_service_configs(provider)
        return render(request, 'custom_admin/providers/detail.html', {
            'provider': provider,
            'service_configs': service_configs
        })

    def post(self, request, pk):
        provider = get_object_or_404(VTUProviderConfig, pk=pk)
        provider.is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
        provider.api_key = request.POST.get('api_key', '').strip()
        provider.user_id = request.POST.get('user_id', '').strip()
        provider.session_id = request.POST.get('session_id', '').strip()
        provider.secret_key = request.POST.get('secret_key', '').strip()
        provider.base_url = request.POST.get('base_url', '').strip()
        provider.account_name = request.POST.get('account_name', '').strip()
        provider.bank_name = request.POST.get('bank_name', '').strip()
        provider.account_number = request.POST.get('account_number', '').strip()
        try:
            provider.max_retries = int(request.POST.get('max_retries', provider.max_retries))
        except ValueError: pass
        provider.auto_refund_on_failure = request.POST.get('auto_refund_on_failure') == 'on' or request.POST.get('auto_refund_on_failure') == 'true'
        provider.save()

        # Update inline service configs & margins
        for stype, _ in SERVICE_TYPES:
            cfg, _ = ProviderServiceConfig.objects.get_or_create(provider=provider, service_type=stype)
            if f'catalogue_source_{stype}' in request.POST:
                cfg.catalogue_source = request.POST.get(f'catalogue_source_{stype}', 'db')
                cfg.customer_margin_type = request.POST.get(f'customer_margin_type_{stype}', 'flat')
                try:
                    cfg.customer_margin_value = float(request.POST.get(f'customer_margin_value_{stype}', 0.0))
                except ValueError: pass
                cfg.agent_margin_type = request.POST.get(f'agent_margin_type_{stype}', 'flat')
                try:
                    cfg.agent_margin_value = float(request.POST.get(f'agent_margin_value_{stype}', 0.0))
                except ValueError: pass
                cfg.developer_margin_type = request.POST.get(f'developer_margin_type_{stype}', 'flat')
                try:
                    cfg.developer_margin_value = float(request.POST.get(f'developer_margin_value_{stype}', 0.0))
                except ValueError: pass
                cfg.save()

        return JsonResponse({'status': 'success', 'message': f'Provider {provider.get_name_display()} updated successfully.'})


class ProviderServiceConfigListView(PortalPermissionMixin, View):
    required_permission = ('orders.ProviderServiceConfig', 'view')

    def get(self, request):
        configs = ProviderServiceConfig.objects.all().select_related('provider')
        return render(request, 'custom_admin/providers/margins.html', {'configs': configs})

    def post(self, request, pk):
        config = get_object_or_404(ProviderServiceConfig, pk=pk)
        config.customer_margin_value = request.POST.get('customer_margin_value', 0)
        config.agent_margin_value = request.POST.get('agent_margin_value', 0)
        config.developer_margin_value = request.POST.get('developer_margin_value', 0)
        config.catalogue_source = request.POST.get('catalogue_source', 'db')
        config.save()
        return JsonResponse({'status': 'success', 'message': 'Margin updated.'})


class ServiceRoutingListView(PortalPermissionMixin, View):
    required_permission = ('orders.ServiceRouting', 'view')

    def get(self, request):
        routings = ServiceRouting.objects.all().prefetch_related('fallbacks')
        all_providers = VTUProviderConfig.objects.filter(is_active=True)
        return render(request, 'custom_admin/providers/routing.html', {
            'routings': routings,
            'providers': all_providers
        })

    def post(self, request, pk):
        routing = get_object_or_404(ServiceRouting, pk=pk)
        primary_id = request.POST.get('primary_provider_id')
        if primary_id:
            routing.primary_provider = VTUProviderConfig.objects.filter(pk=primary_id).first()

        routing.pricing_mode = request.POST.get('pricing_mode', 'defined')
        routing.customer_margin = request.POST.get('customer_margin', 0)
        routing.agent_margin = request.POST.get('agent_margin', 0)
        routing.developer_margin = request.POST.get('developer_margin', 0)
        routing.save()

        return JsonResponse({'status': 'success', 'message': f'Routing for {routing.get_service_display()} updated.'})


class ProviderSyncTriggerView(PortalPermissionMixin, View):
    required_permission = ('orders.VTUProviderConfig', 'change')

    def post(self, request, pk):
        provider = get_object_or_404(VTUProviderConfig, pk=pk)
        service_type = request.POST.get('service_type', 'all')

        from orders.utils.sync_runner import SERVICE_SYNC_METHODS
        impl = ProviderRouter.get_provider_implementation(provider.name)
        if not impl:
            return JsonResponse({'status': 'error', 'message': f"Provider implementation '{provider.name}' is not registered."}, status=400)

        service_types = [service_type] if service_type and service_type != 'all' else list(SERVICE_SYNC_METHODS.keys())
        total_synced = 0
        results = []

        for st in service_types:
            method_name = SERVICE_SYNC_METHODS.get(st)
            if not method_name:
                continue
            sync_func = getattr(impl, method_name, None)
            if sync_func:
                try:
                    count = sync_func()
                    c = count if isinstance(count, int) else 0
                    total_synced += c
                    results.append(f"{st.upper()}: {c} synced")
                except Exception as e:
                    results.append(f"{st.upper()}: error ({str(e)})")
            else:
                results.append(f"{st.upper()}: sync not supported")

        res_str = ", ".join(results)
        return JsonResponse({
            'status': 'success',
            'message': f"Sync executed for {provider.get_name_display()}: {res_str}"
        })
