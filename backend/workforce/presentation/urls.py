from rest_framework.routers import DefaultRouter

from workforce.presentation.views import (
    DepartmentViewSet,
    EmployeeViewSet,
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

urlpatterns = router.urls
