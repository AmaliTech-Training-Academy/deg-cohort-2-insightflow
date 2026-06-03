from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import TokenBlacklist, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (("InsightFlow", {"fields": ("role",)}),)
    ordering = ("email",)


@admin.register(TokenBlacklist)
class TokenBlacklistAdmin(admin.ModelAdmin):
    list_display = ("user", "blacklisted_at", "expires_at")
    list_filter = ("blacklisted_at", "user")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("token", "blacklisted_at")
    ordering = ("-blacklisted_at",)
