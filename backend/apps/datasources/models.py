from django.conf import settings
from django.db import models


class DataSourceType(models.TextChoices):
    CSV = "CSV", "CSV"
    JSON = "JSON", "JSON"
    API = "API", "API"
    DATABASE = "DATABASE", "Database"


class DataSource(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=DataSourceType.choices)
    connection_url = models.TextField(blank=True, null=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="datasources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_sources"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.type})"
