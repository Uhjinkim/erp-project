from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    model = User
    ordering = ["email"]
    list_display = ["email", "employee", "is_active", "is_staff"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("사원", {"fields": ("employee",)}),
        (
            "권한",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("일시", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "employee", "password1", "password2", "is_staff"),
            },
        ),
    )
    search_fields = ["email", "employee__person__name"]
