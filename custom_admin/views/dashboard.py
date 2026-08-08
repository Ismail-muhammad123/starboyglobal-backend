from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum
from custom_admin.mixins import PortalLoginRequired
from summary.models import SummaryDashboard
from orders.models import Purchase


class DashboardView(PortalLoginRequired, View):
    def get(self, request):
        stats = SummaryDashboard.summary()
        context = {
            'stats': stats,
            'financial': stats.get('financial', {}),
            'wallets': stats.get('wallets', {}),
            'purchases': stats.get('purchases', {}),
            'users': stats.get('users', {}),
            'vtu_providers': stats.get('vtu_providers', []),
            'service_health': stats.get('service_health', {}),
            'alerts': stats.get('alerts', {}),
            'finances': stats.get('finances', {}),
            'quick_actions': stats.get('quick_actions', {}),
        }
        return render(request, 'custom_admin/dashboard.html', context)


class RevenueChartDataView(PortalLoginRequired, View):
    def get(self, request):
        days = int(request.GET.get('days', 30))
        today = timezone.now().date()
        labels = []
        revenue_data = []
        profit_data = []

        for i in range(days - 1, -1, -1):
            date_val = today - timedelta(days=i)
            labels.append(date_val.strftime('%b %d'))

            day_qs = Purchase.objects.filter(status='success', time__date=date_val)
            vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
            prof = SummaryDashboard._calculate_profit(day_qs)

            revenue_data.append(vol)
            profit_data.append(prof)

        return JsonResponse({
            'labels': labels,
            'datasets': [
                {'label': 'Revenue (₦)', 'data': revenue_data, 'borderColor': '#3B82F6', 'backgroundColor': 'rgba(59, 130, 246, 0.15)'},
                {'label': 'Profit (₦)', 'data': profit_data, 'borderColor': '#10B981', 'backgroundColor': 'rgba(16, 185, 129, 0.15)'}
            ]
        })
