from django.shortcuts import render
from django.views import View
from custom_admin.mixins import PortalPermissionMixin
from summary.models import SummaryDashboard


class ReportsIndexView(PortalPermissionMixin, View):
    required_permission = ('summary.SiteConfig', 'view')

    def get(self, request):
        stats = SummaryDashboard.summary()
        return render(request, 'custom_admin/reports/index.html', {'stats': stats})
