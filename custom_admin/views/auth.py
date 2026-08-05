from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.views import View


class PortalLoginView(View):
    def get(self, request):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_admin or request.user.is_superuser):
            return redirect('portal:dashboard')
        return render(request, 'custom_admin/login.html')

    def post(self, request):
        phone = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=phone, password=password)
        if user is None:
            # Fallback check if username parameter is phone_number
            user = authenticate(request, phone_number=phone, password=password)

        if user is not None:
            if user.is_staff or user.is_admin or user.is_superuser:
                django_login(request, user)
                next_url = request.GET.get('next') or 'portal:dashboard'
                return redirect(next_url)
            else:
                return render(request, 'custom_admin/login.html', {'error': 'Account lacks admin access privileges.'})
        else:
            return render(request, 'custom_admin/login.html', {'error': 'Invalid phone number or password.'})


class PortalLogoutView(View):
    def get(self, request):
        django_logout(request)
        return redirect('portal:login')

    def post(self, request):
        django_logout(request)
        return redirect('portal:login')
