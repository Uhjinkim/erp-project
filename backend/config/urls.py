from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from config.health import get_system_health


def health_check(request):
    return JsonResponse(get_system_health())


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/", include("accounts.urls")),
    path("api/workforce/", include("workforce.presentation.urls")),
    path("api/vacations/", include("vacation.presentation.urls")),
    path("api/payroll/", include("payroll.presentation.urls")),
]
