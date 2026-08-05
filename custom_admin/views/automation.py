from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from custom_admin.mixins import PortalPermissionMixin
from orders.models import AutoSyncSchedule, AutoSyncLog, VTUProviderConfig
from orders.utils.sync_runner import execute_sync_schedule


class SyncScheduleListView(PortalPermissionMixin, View):
    required_permission = ('orders.AutoSyncSchedule', 'view')

    def get(self, request):
        schedules = AutoSyncSchedule.objects.all().select_related('provider').order_by('-created_at')
        providers = VTUProviderConfig.objects.all()
        return render(request, 'custom_admin/automation/schedules.html', {
            'schedules': schedules,
            'providers': providers
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        provider_id = request.POST.get('provider_id')
        service_type = request.POST.get('service_type', 'all')
        frequency = request.POST.get('frequency', 'daily')

        provider = VTUProviderConfig.objects.filter(pk=provider_id).first() if provider_id else None

        schedule = AutoSyncSchedule.objects.create(
            name=name or f"Sync {service_type}",
            provider=provider,
            service_type=service_type,
            frequency=frequency,
            is_active=True
        )

        return JsonResponse({'status': 'success', 'message': f"Sync schedule '{schedule.name}' created."})


class SyncScheduleToggleView(PortalPermissionMixin, View):
    required_permission = ('orders.AutoSyncSchedule', 'change')

    def post(self, request, pk):
        schedule = get_object_or_404(AutoSyncSchedule, pk=pk)
        schedule.is_active = not schedule.is_active
        schedule.save(update_fields=['is_active'])
        return JsonResponse({
            'status': 'success',
            'message': f"Schedule '{schedule.name}' is now {'active' if schedule.is_active else 'inactive'}.",
            'is_active': schedule.is_active
        })


class SyncLogListView(PortalPermissionMixin, View):
    required_permission = ('orders.AutoSyncLog', 'view')

    def get(self, request):
        qs = AutoSyncLog.objects.all().order_by('-started_at')

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        paginator = Paginator(qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'custom_admin/automation/logs.html', {
            'logs': page_obj,
            'status_filter': status_filter or ''
        })


class ManualSyncTriggerView(PortalPermissionMixin, View):
    required_permission = ('orders.AutoSyncSchedule', 'change')

    def post(self, request):
        provider_id = request.POST.get('provider_id')
        service_type = request.POST.get('service_type', 'all')

        try:
            provider = VTUProviderConfig.objects.filter(pk=provider_id).first() if provider_id else None
            temp_schedule = AutoSyncSchedule.objects.create(
                name="Manual Sync Trigger",
                provider=provider,
                service_type=service_type,
                frequency="daily",
                is_active=True
            )
            execute_sync_schedule(temp_schedule.id)
            temp_schedule.delete()
            return JsonResponse({'status': 'success', 'message': 'Manual auto-sync executed.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Sync execution failed: {str(e)}'}, status=500)
