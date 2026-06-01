from django.contrib import admin

from .models import InsightReport, Pipeline


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "data_source", "records_processed", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(InsightReport)
class InsightReportAdmin(admin.ModelAdmin):
    list_display = ("title", "pipeline", "created_at")
    search_fields = ("title",)
