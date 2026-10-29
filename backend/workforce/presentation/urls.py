from django.urls import path
from rest_framework.routers import DefaultRouter

from workforce.presentation.views import (
    DepartmentViewSet,
    EmployeeViewSet,
    NewHireRegistrationView,
    PersonalInfoChangeRequestViewSet,
    PersonViewSet,
    PositionViewSet,
    RoleViewSet,
)

router = DefaultRouter()
router.register("persons", PersonViewSet, basename="person")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("departments", DepartmentViewSet, basename="department")
router.register("positions", PositionViewSet, basename="position")
router.register("roles", RoleViewSet, basename="role")
router.register(
    "personal-info-requests",
    PersonalInfoChangeRequestViewSet,
    basename="personal-info-request",
)

urlpatterns = [
    path("new-hires/", NewHireRegistrationView.as_view(), name="new-hire-registration"),
    *router.urls,
]
