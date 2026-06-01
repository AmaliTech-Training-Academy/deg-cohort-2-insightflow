from django.contrib import admin

from .models import DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "created_by", "created_at")
    list_filter = ("type",)
    search_fields = ("name",)
