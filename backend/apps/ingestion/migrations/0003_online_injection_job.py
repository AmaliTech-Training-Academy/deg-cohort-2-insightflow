import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0002_injectionjob"),
    ]

    operations = [
        migrations.CreateModel(
            name="OnlineInjectionJob",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "trigger",
                    models.CharField(
                        choices=[
                            ("scheduled", "Scheduled"),
                            ("manual", "Manual"),
                        ],
                        default="scheduled",
                        max_length=20,
                    ),
                ),
                ("total_orders", models.IntegerField(blank=True, null=True)),
                ("valid_orders", models.IntegerField(default=0)),
                ("error_orders", models.IntegerField(default=0)),
                ("pages_fetched", models.IntegerField(default=0)),
                ("error_report", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Online Orders Ingestion Job",
                "verbose_name_plural": "Online Orders Ingestion Jobs",
                "db_table": "online_injection_job",
                "ordering": ["-created_at"],
            },
        ),
    ]
