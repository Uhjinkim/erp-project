from django.urls import path
from rest_framework.routers import DefaultRouter

from accounts.views import AccountViewSet, CsrfCookieView, CurrentUserView, LoginView, LogoutView

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")

urlpatterns = [
    path("csrf/", CsrfCookieView.as_view(), name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    *router.urls,
]
