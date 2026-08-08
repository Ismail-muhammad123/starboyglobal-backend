from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum
from custom_admin.mixins import PortalLoginRequired
from summary.models import SummaryDashboard
from orders.models import Purchase


def parse_date_range(request):
    range_opt = request.GET.get('range', 'all').strip().lower()
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    now = timezone.now()
    today = now.date()

    start, end = None, None
    active_label = "All Time"

    if date_from_str or date_to_str:
        range_opt = 'custom'
        if date_from_str:
            try:
                dt = datetime.strptime(date_from_str, '%Y-%m-%d')
                start = timezone.make_aware(dt)
            except ValueError:
                pass
        if date_to_str:
            try:
                dt = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                end = timezone.make_aware(dt)
            except ValueError:
                pass
        active_label = f"{date_from_str or 'Beginning'} to {date_to_str or 'Present'}"

    elif range_opt == 'today':
        start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        active_label = f"Today ({today.strftime('%b %d, %Y')})"

    elif range_opt == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        start = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        active_label = f"This Week ({start_of_week.strftime('%b %d')} - {today.strftime('%b %d, %Y')})"

    elif range_opt == 'this_month':
        start_of_month = today.replace(day=1)
        start = timezone.make_aware(datetime.combine(start_of_month, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        active_label = f"This Month ({today.strftime('%B %Y')})"

    elif range_opt == 'this_year':
        start_of_year = today.replace(month=1, day=1)
        start = timezone.make_aware(datetime.combine(start_of_year, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        active_label = f"This Year ({today.year})"

    else:
        range_opt = 'all'
        active_label = "All Time"

    return start, end, range_opt, active_label, date_from_str, date_to_str


class DashboardView(PortalLoginRequired, View):
    def get(self, request):
        start, end, selected_range, active_label, date_from, date_to = parse_date_range(request)
        stats = SummaryDashboard.summary(start=start, end=end)
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
            'selected_range': selected_range,
            'active_filter_label': active_label,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, 'custom_admin/dashboard.html', context)


class RevenueChartDataView(PortalLoginRequired, View):
    def get(self, request):
        start, end, selected_range, active_label, date_from, date_to = parse_date_range(request)
        if start and end:
            days = max(1, (end.date() - start.date()).days + 1)
            end_date = end.date()
        else:
            days = int(request.GET.get('days', 30))
            end_date = timezone.now().date()

        labels = []
        revenue_data = []
        profit_data = []

        for i in range(days - 1, -1, -1):
            date_val = end_date - timedelta(days=i)
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
