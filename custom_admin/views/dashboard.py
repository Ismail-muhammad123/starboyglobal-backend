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
    range_param = request.GET.get('range', '').strip().lower()
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()
    days_param = request.GET.get('days')

    now = timezone.now()
    today = now.date()

    start_dt = None
    end_dt = None
    active_label = "All Time"

    if date_from_str or date_to_str:
        range_param = 'custom'
        d_from = None
        d_to = None
        try:
            if date_from_str:
                d_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                start_dt = timezone.make_aware(datetime.combine(d_from, datetime.min.time()))
            if date_to_str:
                d_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
                end_dt = timezone.make_aware(datetime.combine(d_to, datetime.max.time()))

            if d_from and d_to:
                active_label = f"{d_from.strftime('%b %d, %Y')} – {d_to.strftime('%b %d, %Y')}"
            elif d_from:
                active_label = f"From {d_from.strftime('%b %d, %Y')}"
            elif d_to:
                active_label = f"Until {d_to.strftime('%b %d, %Y')}"
        except ValueError:
            pass

    elif range_param == 'today':
        start_dt = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        active_label = f"Today ({today.strftime('%b %d, %Y')})"

    elif range_param == 'this_week':
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        start_dt = timezone.make_aware(datetime.combine(monday, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(sunday, datetime.max.time()))
        active_label = f"This Week ({monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')})"

    elif range_param == 'this_month':
        first_day = today.replace(day=1)
        if today.month == 12:
            next_month_first = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month_first = today.replace(month=today.month + 1, day=1)
        last_day = next_month_first - timedelta(days=1)

        start_dt = timezone.make_aware(datetime.combine(first_day, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(last_day, datetime.max.time()))
        active_label = f"This Month ({today.strftime('%B %Y')})"

    elif range_param == 'this_year':
        first_day = today.replace(month=1, day=1)
        last_day = today.replace(month=12, day=31)
        start_dt = timezone.make_aware(datetime.combine(first_day, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(last_day, datetime.max.time()))
        active_label = f"This Year ({today.year})"

    elif days_param and days_param.isdigit():
        num_days = int(days_param)
        d_from = today - timedelta(days=num_days - 1)
        start_dt = timezone.make_aware(datetime.combine(d_from, datetime.min.time()))
        end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        active_label = f"Last {num_days} Days ({d_from.strftime('%b %d')} – {today.strftime('%b %d, %Y')})"
        range_param = f"{num_days}d"
    else:
        range_param = 'all'
        active_label = "All Time"

    return {
        'start_dt': start_dt,
        'end_dt': end_dt,
        'selected_range': range_param,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'active_filter_label': active_label,
    }


class DashboardView(PortalLoginRequired, View):
    def get(self, request):
        range_info = parse_date_range(request)
        stats = SummaryDashboard.summary(start=range_info['start_dt'], end=range_info['end_dt'])

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
            'selected_range': range_info['selected_range'],
            'date_from': range_info['date_from'],
            'date_to': range_info['date_to'],
            'active_filter_label': range_info['active_filter_label'],
        }
        return render(request, 'custom_admin/dashboard.html', context)


class RevenueChartDataView(PortalLoginRequired, View):
    def get(self, request):
        range_info = parse_date_range(request)
        start_dt = range_info['start_dt']
        end_dt = range_info['end_dt']

        now = timezone.now()
        today = now.date()

        if not start_dt:
            # Default to last 30 days if 'all' time selected without explicit bounds
            days = int(request.GET.get('days', 30))
            d_from = today - timedelta(days=days - 1)
            start_dt = timezone.make_aware(datetime.combine(d_from, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(today, datetime.max.time()))
            if range_info['selected_range'] == 'all':
                range_info['active_filter_label'] = f"Last {days} Days ({d_from.strftime('%b %d')} – {today.strftime('%b %d, %Y')})"

        start_date = start_dt.date()
        end_date = end_dt.date() if end_dt else today

        labels = []
        revenue_data = []
        profit_data = []

        curr_date = start_date
        while curr_date <= end_date:
            labels.append(curr_date.strftime('%b %d'))

            day_qs = Purchase.objects.filter(status='success', time__date=curr_date)
            vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
            prof = SummaryDashboard._calculate_profit(day_qs)

            revenue_data.append(vol)
            profit_data.append(prof)
            curr_date += timedelta(days=1)

        return JsonResponse({
            'labels': labels,
            'active_filter_label': range_info['active_filter_label'],
            'datasets': [
                {'label': 'Revenue (₦)', 'data': revenue_data, 'borderColor': '#3B82F6', 'backgroundColor': 'rgba(59, 130, 246, 0.15)'},
                {'label': 'Profit (₦)', 'data': profit_data, 'borderColor': '#10B981', 'backgroundColor': 'rgba(16, 185, 129, 0.15)'}
            ]
        })
