from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Sum, Count
from django.db.models.functions import TruncHour, TruncDay, TruncMonth
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
        provider_balances = stats.get('provider_balances', {})

        vtu_balance_sum = float(provider_balances.get('vtu', 0) or 0)

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
        range_info = parse_date_range(request)
        stats = SummaryDashboard.summary(start=range_info['start_dt'], end=range_info['end_dt'])
        return JsonResponse({
            'status': 'success',
            'vtu_providers': stats.get('vtu_providers', [])
        })


class DashboardOverviewExtraApiView(PortalLoginRequired, View):
    """API for loading User Base Stats, Network Health, and Recent Failed Transactions Alerts dynamically."""
    def get(self, request):
        range_info = parse_date_range(request)
        stats = SummaryDashboard.summary(start=range_info['start_dt'], end=range_info['end_dt'])
        return JsonResponse({
            'status': 'success',
            'users': stats.get('users', {}),
            'service_health': stats.get('service_health', {}),
            'alerts': stats.get('alerts', {})
        })


class RevenueChartDataView(PortalLoginRequired, View):
    """
    Revenue/Cost/Profit chart data view.
    Uses single grouped-aggregate queries (TruncHour / TruncDay / TruncMonth)
    instead of one DB hit per time bucket — dramatically reduces DB load.
    """

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_bucket_map(qs, trunc_fn, field='time'):
        """
        Given a queryset and a Trunc function, return a dict keyed by the
        truncated datetime value:
            { dt: {'vol': float, 'prof': float, 'cost': float} }
        A single aggregation query is issued.
        """
        rows = (
            qs
            .annotate(bucket=trunc_fn(field))
            .values('bucket')
            .annotate(
                vol=Sum('amount'),
                prof=Sum('profit'),
                cost=Sum('cost_price'),
            )
        )
        result = {}
        for row in rows:
            result[row['bucket']] = {
                'vol':  float(row['vol']  or 0),
                'prof': float(row['prof'] or 0),
                'cost': float(row['cost'] or 0),
            }
        return result

    @staticmethod
    def _resolve(bucket_data, fallback_vol=0.0, fallback_prof=0.0, fallback_cost=0.0):
        vol  = bucket_data.get('vol',  fallback_vol)
        prof = bucket_data.get('prof', fallback_prof)
        cost = bucket_data.get('cost', fallback_cost)
        # If profit not stored, approximate from vol - cost
        if prof == 0 and vol > 0 and cost > 0:
            prof = max(0.0, vol - cost)
        elif cost == 0 and vol > 0:
            cost = max(0.0, vol - prof)
        return vol, cost, prof

    def get(self, request):
        range_param   = request.GET.get('range', '').strip().lower()
        date_from_str = request.GET.get('date_from', '').strip()
        date_to_str   = request.GET.get('date_to',   '').strip()
        days_param    = request.GET.get('days')

        now   = timezone.now()
        today = now.date()

        labels        = []
        revenue_data  = []
        cost_data     = []
        profit_data   = []

        base_qs = Purchase.objects.filter(status='success')

        # ── 1. CUSTOM DATE RANGE (Max 30 days) ──────────────────────
        if date_from_str or date_to_str:
            try:
                d_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                d_to   = datetime.strptime(date_to_str,   '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid date format.'}, status=400)

            if d_to < d_from:
                return JsonResponse({'error': 'End date cannot be earlier than Start date.'}, status=400)

            num_days = (d_to - d_from).days + 1
            if num_days > 30:
                return JsonResponse({'error': 'Custom date range cannot exceed 30 days max.'}, status=400)

            range_qs   = base_qs.filter(time__date__gte=d_from, time__date__lte=d_to)
            bucket_map = self._build_bucket_map(range_qs, TruncDay)

            # Normalise keys to date objects
            day_map = {}
            for k, v in bucket_map.items():
                key = k.date() if hasattr(k, 'date') else k
                day_map[key] = v

            for i in range(num_days):
                date_val = d_from + timedelta(days=i)
                labels.append(date_val.strftime('%b %d'))
                vol, cost, prof = self._resolve(day_map.get(date_val, {}))
                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 2. TODAY (Group by Hours 00:00 – 23:00) ─────────────────
        elif range_param == 'today':
            tz = timezone.get_current_timezone()
            day_start = timezone.make_aware(
                datetime.combine(today, datetime.min.time()), tz)
            day_end   = timezone.make_aware(
                datetime.combine(today, datetime.max.time()), tz)

            today_qs   = base_qs.filter(time__gte=day_start, time__lte=day_end)
            bucket_map = self._build_bucket_map(today_qs, TruncHour)

            # normalise keys to local aware datetimes for comparison
            hour_map = {}
            for k, v in bucket_map.items():
                key = k.astimezone(tz).replace(minute=0, second=0, microsecond=0)
                hour_map[key] = v

            for h in range(24):
                labels.append(f"{h:02d}:00")
                bucket_dt = day_start.replace(hour=h, minute=0, second=0, microsecond=0)
                vol, cost, prof = self._resolve(hour_map.get(bucket_dt, {}))
                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 3. THIS WEEK (Mon–Sun, group by day) ────────────────────
        elif range_param == 'this_week':
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)

            week_qs    = base_qs.filter(time__date__gte=monday, time__date__lte=sunday)
            bucket_map = self._build_bucket_map(week_qs, TruncDay)

            day_map = {}
            for k, v in bucket_map.items():
                key = k.date() if hasattr(k, 'date') else k
                day_map[key] = v

            for i in range(7):
                date_val = monday + timedelta(days=i)
                labels.append(date_val.strftime('%a %b %d'))
                vol, cost, prof = self._resolve(day_map.get(date_val, {}))
                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 4. THIS YEAR (Jan–Dec, group by month) ──────────────────
        elif range_param == 'this_year':
            year     = today.year
            year_qs  = base_qs.filter(time__year=year)
            bucket_map = self._build_bucket_map(year_qs, TruncMonth)

            month_map = {}
            for k, v in bucket_map.items():
                # key can be date(year, month, 1) or datetime; normalise to month int
                month_num = k.month if hasattr(k, 'month') else None
                if month_num:
                    month_map[month_num] = v

            for m in range(1, 13):
                labels.append(datetime(year, m, 1).strftime('%b'))
                vol, cost, prof = self._resolve(month_map.get(m, {}))
                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        # ── 5. THIS MONTH (default, group by day) ───────────────────
        else:
            first_day = today.replace(day=1)
            if today.month == 12:
                next_month_first = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month_first = today.replace(month=today.month + 1, day=1)
            last_day   = next_month_first - timedelta(days=1)
            total_days = (last_day - first_day).days + 1

            month_qs   = base_qs.filter(time__date__gte=first_day, time__date__lte=last_day)
            bucket_map = self._build_bucket_map(month_qs, TruncDay)

            day_map = {}
            for k, v in bucket_map.items():
                key = k.date() if hasattr(k, 'date') else k
                day_map[key] = v

            for i in range(total_days):
                date_val = first_day + timedelta(days=i)
                labels.append(date_val.strftime('%b %d'))
                vol, cost, prof = self._resolve(day_map.get(date_val, {}))
                revenue_data.append(vol)
                cost_data.append(cost)
                profit_data.append(prof)

        return JsonResponse({
            'status': 'success',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenue (₦)',
                    'data': revenue_data,
                    'borderColor': '#3B82F6',
                    'backgroundColor': 'rgba(59, 130, 246, 0.10)',
                    'fill': False,
                },
                {
                    'label': 'Cost (₦)',
                    'data': cost_data,
                    'borderColor': '#EF4444',
                    'backgroundColor': 'rgba(239, 68, 68, 0.10)',
                    'fill': False,
                },
                {
                    'label': 'Profit / Loss (₦)',
                    'data': profit_data,
                    'borderColor': '#10B981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.10)',
                    'fill': False,
                },
            ]
        })


