from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0002_injectionjob_onlineinjectionjob"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeedbackIngestionJob",
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
                ("total_fetched", models.IntegerField(default=0)),
                ("created_count", models.IntegerField(default=0)),
                ("skipped_duplicates", models.IntegerField(default=0)),
                ("errors", models.IntegerField(default=0)),
                ("error_details", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Feedback Ingestion Job",
                "verbose_name_plural": "Feedback Ingestion Jobs",
                "db_table": "feedback_ingestion_job",
                "ordering": ["-created_at"],
            },
        ),
    ]
