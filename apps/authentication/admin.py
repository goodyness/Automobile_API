from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetToken, User, UserChassis


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for the custom User model."""

    # Show email prominently in the list view
    list_display = ("email", "username", "name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "username", "name")
    ordering = ("-date_joined",)

    # Add `name` to the fieldsets used by BaseUserAdmin
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("name",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("email", "name")}),
    )


@admin.register(UserChassis)
class UserChassisAdmin(admin.ModelAdmin):
    list_display = ("user", "chassis")
    list_filter = ("chassis",)
    search_fields = ("user__email",)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "created_at", "used")
    list_filter = ("used",)
    search_fields = ("user__email", "token")
    readonly_fields = ("created_at",)
