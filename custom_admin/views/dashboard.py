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
    """
    Parses 'range', 'date_from', 'date_to' from request.GET
    Returns (start_dt, end_dt, range_type, active_label, date_from_str, date_to_str)
    """
    range_type = request.GET.get('range', 'all').strip().lower()
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    now = timezone.now()
    today = now.date()

    start_dt = None
    end_dt = None
    label = "All Time"

    if range_type == 'today':
        start_dt = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        label = f"Today ({today.strftime('%d %b %Y')})"

    elif range_type == 'this_week':
        monday = today - timedelta(days=today.weekday())
        start_dt = timezone.make_aware(datetime.combine(monday, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        label = f"This Week ({monday.strftime('%d %b')} – {today.strftime('%d %b %Y')})"

    elif range_type == 'this_month':
        first_day = today.replace(day=1)
        start_dt = timezone.make_aware(datetime.combine(first_day, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        label = f"This Month ({first_day.strftime('%d %b')} – {today.strftime('%d %b %Y')})"

    elif range_type == 'this_year':
        jan_first = today.replace(month=1, day=1)
        start_dt = timezone.make_aware(datetime.combine(jan_first, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        label = f"This Year ({jan_first.strftime('%d %b %Y')} – {today.strftime('%d %b %Y')})"

    elif range_type == 'custom':
        if date_from_str:
            try:
                df = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                start_dt = timezone.make_aware(datetime.combine(df, datetime.min.time()))
            except ValueError:
                pass
        if date_to_str:
            try:
                dt = datetime.strptime(date_to_str, '%Y-%m-%d').date()
                end_dt = timezone.make_aware(datetime.combine(dt, datetime.max.time()))
            except ValueError:
                pass

        if start_dt and end_dt:
            label = f"Custom Range ({start_dt.strftime('%d %b %Y')} – {end_dt.strftime('%d %b %Y')})"
        elif start_dt:
            label = f"From {start_dt.strftime('%d %b %Y')}"
        elif end_dt:
            label = f"Until {end_dt.strftime('%d %b %Y')}"
        else:
            label = "Custom Range (No dates selected)"

    else:
        range_type = 'all'
        label = "All Time"

    return start_dt, end_dt, range_type, label, date_from_str, date_to_str


class DashboardView(PortalLoginRequired, View):
    def get(self, request):
        start_dt, end_dt, range_type, active_label, date_from_str, date_to_str = parse_date_range(request)

        stats = SummaryDashboard.summary(start=start_dt, end=end_dt)
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

            # Date Filter Context
            'selected_range': range_type,
            'active_filter_label': active_label,
            'date_from': date_from_str,
            'date_to': date_to_str,
        }
        return render(request, 'custom_admin/dashboard.html', context)


class RevenueChartDataView(PortalLoginRequired, View):
    def get(self, request):
        start_dt, end_dt, range_type, active_label, _, _ = parse_date_range(request)

        now = timezone.now()
        today = now.date()

        if range_type == 'today':
            start_date = today
            end_date = today
        elif range_type == 'this_week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif range_type == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
        elif range_type == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif range_type == 'custom':
            start_date = start_dt.date() if start_dt else (today - timedelta(days=30))
            end_date = end_dt.date() if end_dt else today
        else:  # 'all'
            days = int(request.GET.get('days', 30))
            start_date = today - timedelta(days=days - 1)
            end_date = today

        labels = []
        revenue_data = []
        profit_data = []

        curr = start_date
        while curr <= end_date:
            labels.append(curr.strftime('%b %d'))
            day_qs = Purchase.objects.filter(status='success', time__date=curr)
            vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
            prof = SummaryDashboard._calculate_profit(day_qs)

            revenue_data.append(vol)
            profit_data.append(prof)

            curr += timedelta(days=1)

        return JsonResponse({
            'labels': labels,
            'datasets': [
                {'label': 'Revenue (₦)', 'data': revenue_data, 'borderColor': '#3B82F6', 'backgroundColor': 'rgba(59, 130, 246, 0.15)'},
                {'label': 'Profit (₦)', 'data': profit_data, 'borderColor': '#10B981', 'backgroundColor': 'rgba(16, 185, 129, 0.15)'}
            ]
        })
