from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = (
        "display_avatar",
        "username",
        "email",
        "role",
        "is_staff",
        "created_at",
        "is_verified",
        "tier",
        "current_storage_usage_display",
        "storage_limit_display",
        "remaining_storage_display",
        "last_storage_warning_level",
    )

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("avatar", "first_name", "last_name", "email", "role", "tier")}),
        ("Storage Management", {"fields": ("last_storage_warning_level",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at")

    def display_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url,
            )
        return "-"

    display_avatar.short_description = "Avatar"

    def current_storage_usage_display(self, obj):
        return f"{obj.current_storage_usage / (1024 * 1024):.2f} MB"

    current_storage_usage_display.short_description = "Current Storage Usage"

    def storage_limit_display(self, obj):
        return f"{obj.storage_limit / (1024 * 1024):.2f} MB"

    storage_limit_display.short_description = "Storage Limit"

    def remaining_storage_display(self, obj):
        return f"{obj.remaining_storage / (1024 * 1024):.2f} MB"

    remaining_storage_display.short_description = "Remaining"
