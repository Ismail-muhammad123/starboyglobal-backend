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

    if not range_param and not date_from_str and not date_to_str and not days_param:
        range_param = 'this_month'

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
        # Render HTML template instantly without blocking on heavy DB aggregations or external provider API calls.
        # All heavy stats and charts load dynamically via JS.
        return render(request, 'custom_admin/dashboard.html')


class DashboardStatsApiView(PortalLoginRequired, View):
    """Independent API for Stats Cards Section filtering."""
    def get(self, request):
        range_info = parse_date_range(request)
        stats = SummaryDashboard.summary(start=range_info['start_dt'], end=range_info['end_dt'])
        purchases = stats.get('purchases', {})
        financial = stats.get('financial', {})
        wallets = stats.get('wallets', {})
        users = stats.get('users', {})
        vtu_providers = stats.get('vtu_providers', [])

        vtu_balance_sum = sum(float(p.get('balance', 0) or 0) for p in vtu_providers if p.get('is_active'))

        return JsonResponse({
            'status': 'success',
            'active_filter_label': range_info['active_filter_label'],
            'data': {
                'total_volume': purchases.get('total_volume', 0),
                'profit': purchases.get('profit_periods', {}).get('monthly', 0),
                'wallets_balance': wallets.get('total_balance', 0),
                'total_deposits': financial.get('total_deposits', 0),
                'paystack_balance': financial.get('paystack_balance', 0),
                'vtu_balance': vtu_balance_sum,
                'total_withdrawals': financial.get('total_withdrawals', 0),
                'total_users': users.get('total', 0),
            }
        })


class DashboardServiceStatsApiView(PortalLoginRequired, View):
    """Independent API for Service Volume Share & Transaction Status Section filtering."""
    def get(self, request):
        range_info = parse_date_range(request)
        stats = SummaryDashboard.summary(start=range_info['start_dt'], end=range_info['end_dt'])
        purchases = stats.get('purchases', {})

        return JsonResponse({
            'status': 'success',
            'active_filter_label': range_info['active_filter_label'],
            'data': {
                'totals_by_service': purchases.get('totals_by_service', {}),
                'success_count': purchases.get('success_count', 0),
                'failed_count': purchases.get('failed_count', 0),
                'pending_count': purchases.get('pending_count', 0),
            }
        })


class DashboardProvidersApiView(PortalLoginRequired, View):
    """API for loading VTU provider cards dynamically."""
    def get(self, request):
        stats = SummaryDashboard.summary()
        return JsonResponse({
            'status': 'success',
            'vtu_providers': stats.get('vtu_providers', [])
        })


class DashboardOverviewExtraApiView(PortalLoginRequired, View):
    """API for loading User Base Stats, Network Health, and Recent Failed Transactions Alerts dynamically."""
    def get(self, request):
        stats = SummaryDashboard.summary()
        return JsonResponse({
            'status': 'success',
            'users': stats.get('users', {}),
            'service_health': stats.get('service_health', {}),
            'alerts': stats.get('alerts', {})
        })


class RevenueChartDataView(PortalLoginRequired, View):
    def get(self, request):
        range_param = request.GET.get('range', '').strip().lower()
        date_from_str = request.GET.get('date_from', '').strip()
        date_to_str = request.GET.get('date_to', '').strip()
        days_param = request.GET.get('days')

        today = timezone.now().date()
        labels = []
        revenue_data = []
        cost_data = []
        profit_data = []

        # ── 1. CUSTOM DATE RANGE (Max 30 days) ──────────────────────
        if date_from_str or date_to_str:
            try:
                d_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                d_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
                if d_to < d_from:
                    return JsonResponse({'error': 'End date cannot be earlier than Start date.'}, status=400)
                
                num_days = (d_to - d_from).days + 1
                if num_days > 30:
                    return JsonResponse({'error': 'Custom date range cannot exceed 30 days max.'}, status=400)

                for i in range(num_days):
                    date_val = d_from + timedelta(days=i)
                    labels.append(date_val.strftime('%b %d'))

                    day_qs = Purchase.objects.filter(status='success', time__date=date_val)
                    vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
                    prof = float(day_qs.aggregate(s=Sum('profit'))['s'] or 0)
                    if prof == 0 and vol > 0:
                        prof = SummaryDashboard._calculate_profit(day_qs)
                    cost = float(day_qs.aggregate(s=Sum('cost_price'))['s'] or 0)
                    if cost == 0 and vol > 0:
                        cost = max(0.0, vol - prof)

                    revenue_data.append(vol)
                    cost_data.append(cost)
                    profit_data.append(prof)

            except ValueError:
                return JsonResponse({'error': 'Invalid date format.'}, status=400)

        # ── 2. TODAY (Group by Hours: 00:00 to 23:00) ───────────────
        elif range_param == 'today':
            for h in range(24):
                labels.append(f"{h:02d}:00")
                hour_qs = Purchase.objects.filter(status='success', time__date=today, time__hour=h)
                vol = float(hour_qs.aggregate(s=Sum('amount'))['s'] or 0)
                prof = float(hour_qs.aggregate(s=Sum('profit'))['s'] or 0)
                if prof == 0 and vol > 0:
                    prof = SummaryDashboard._calculate_profit(hour_qs)
                cost = float(hour_qs.aggregate(s=Sum('cost_price'))['s'] or 0)
                if cost == 0 and vol > 0:
                    cost = max(0.0, vol - prof)

                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 3. THIS WEEK (Group by Days: Monday to Sunday) ──────────
        elif range_param == 'this_week':
            monday = today - timedelta(days=today.weekday())
            for i in range(7):
                date_val = monday + timedelta(days=i)
                labels.append(date_val.strftime('%a %b %d'))

                day_qs = Purchase.objects.filter(status='success', time__date=date_val)
                vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
                prof = float(day_qs.aggregate(s=Sum('profit'))['s'] or 0)
                if prof == 0 and vol > 0:
                    prof = SummaryDashboard._calculate_profit(day_qs)
                cost = float(day_qs.aggregate(s=Sum('cost_price'))['s'] or 0)
                if cost == 0 and vol > 0:
                    cost = max(0.0, vol - prof)

                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 4. THIS YEAR (Group by Months: Jan to Dec) ──────────────
        elif range_param == 'this_year':
            year = today.year
            for m in range(1, 13):
                labels.append(datetime(year, m, 1).strftime('%b'))
                m_qs = Purchase.objects.filter(status='success', time__year=year, time__month=m)
                vol = float(m_qs.aggregate(s=Sum('amount'))['s'] or 0)
                prof = float(m_qs.aggregate(s=Sum('profit'))['s'] or 0)
                if prof == 0 and vol > 0:
                    prof = SummaryDashboard._calculate_profit(m_qs)
                cost = float(m_qs.aggregate(s=Sum('cost_price'))['s'] or 0)
                if cost == 0 and vol > 0:
                    cost = max(0.0, vol - prof)

                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 5. THIS MONTH (Default: Group by Days of current month) ──
        else:
            # Handle legacy days parameter if provided
            if days_param and days_param.isdigit() and int(days_param) != 30:
                num_days = min(int(days_param), 30)
                for i in range(num_days - 1, -1, -1):
                    date_val = today - timedelta(days=i)
                    labels.append(date_val.strftime('%b %d'))

                    day_qs = Purchase.objects.filter(status='success', time__date=date_val)
                    vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
                    prof = float(day_qs.aggregate(s=Sum('profit'))['s'] or 0)
                    if prof == 0 and vol > 0:
                        prof = SummaryDashboard._calculate_profit(day_qs)
                    cost = float(day_qs.aggregate(s=Sum('cost_price'))['s'] or 0)
                    if cost == 0 and vol > 0:
                        cost = max(0.0, vol - prof)

                    revenue_data.append(vol)
                    cost_data.append(cost)
                    profit_data.append(prof)
            else:
                first_day = today.replace(day=1)
                if today.month == 12:
                    next_month_first = today.replace(year=today.year + 1, month=1, day=1)
                else:
                    next_month_first = today.replace(month=today.month + 1, day=1)
                last_day = next_month_first - timedelta(days=1)
                total_days = (last_day - first_day).days + 1

                for i in range(total_days):
                    date_val = first_day + timedelta(days=i)
                    labels.append(date_val.strftime('%b %d'))

                    day_qs = Purchase.objects.filter(status='success', time__date=date_val)
                    vol = float(day_qs.aggregate(s=Sum('amount'))['s'] or 0)
                    prof = float(day_qs.aggregate(s=Sum('profit'))['s'] or 0)
                    if prof == 0 and vol > 0:
                        prof = SummaryDashboard._calculate_profit(day_qs)
                    cost = float(day_qs.aggregate(s=Sum('cost_price'))['s'] or 0)
                    if cost == 0 and vol > 0:
                        cost = max(0.0, vol - prof)

                    revenue_data.append(vol)
                    cost_data.append(cost)
                    profit_data.append(prof)

        return JsonResponse({
            'status': 'success',
            'labels': labels,
            'datasets': [
                {'label': 'Revenue (₦)', 'data': revenue_data, 'borderColor': '#3B82F6', 'backgroundColor': 'rgba(59, 130, 246, 0.10)', 'fill': False},
                {'label': 'Cost (₦)', 'data': cost_data, 'borderColor': '#EF4444', 'backgroundColor': 'rgba(239, 68, 68, 0.10)', 'fill': False},
                {'label': 'Profit / Loss (₦)', 'data': profit_data, 'borderColor': '#10B981', 'backgroundColor': 'rgba(16, 185, 129, 0.10)', 'fill': False}
            ]
        })


