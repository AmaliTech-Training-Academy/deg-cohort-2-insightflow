import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IngestionJob",
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
                    "source_type",
                    models.CharField(
                        choices=[
                            ("POS", "Point of Sale"),
                            ("ONLINE_ORDERS", "Online Orders"),
                            ("FEEDBACK", "Customer Feedback"),
                            ("INVENTORY", "Inventory"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                (
                    "file_path",
                    models.CharField(blank=True, max_length=500, null=True),
                ),
                ("connection_url", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ingestion_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ingestion_jobs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="POSStagingRecord",
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
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("valid_rows", models.PositiveIntegerField(default=0)),
                ("error_rows", models.PositiveIntegerField(default=0)),
                ("ingested_at", models.DateTimeField(blank=True, null=True)),
                (
                    "transaction_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "store_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "product_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("quantity", models.PositiveIntegerField(default=0)),
                (
                    "amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                ("transaction_date", models.DateField(blank=True, null=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="posstagingrecord_records",
                        to="ingestion.ingestionjob",
                    ),
                ),
            ],
            options={
                "db_table": "ingestion_pos_staging",
                "ordering": ["-ingested_at"],
            },
        ),
        migrations.CreateModel(
            name="OnlineOrderStagingRecord",
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
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("valid_rows", models.PositiveIntegerField(default=0)),
                ("error_rows", models.PositiveIntegerField(default=0)),
                ("ingested_at", models.DateTimeField(blank=True, null=True)),
                (
                    "order_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "customer_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                ("items", models.JSONField(blank=True, default=list)),
                ("order_date", models.DateField(blank=True, null=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onlineorderstagingrecord_records",
                        to="ingestion.ingestionjob",
                    ),
                ),
            ],
            options={
                "db_table": "ingestion_online_orders_staging",
                "ordering": ["-ingested_at"],
            },
        ),
        migrations.CreateModel(
            name="FeedbackStagingRecord",
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
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("valid_rows", models.PositiveIntegerField(default=0)),
                ("error_rows", models.PositiveIntegerField(default=0)),
                ("ingested_at", models.DateTimeField(blank=True, null=True)),
                (
                    "feedback_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "customer_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "rating",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("comment", models.TextField(blank=True, null=True)),
                ("feedback_date", models.DateField(blank=True, null=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedbackstagingrecord_records",
                        to="ingestion.ingestionjob",
                    ),
                ),
            ],
            options={
                "db_table": "ingestion_feedback_staging",
                "ordering": ["-ingested_at"],
            },
        ),
        migrations.CreateModel(
            name="InventoryStagingRecord",
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
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("valid_rows", models.PositiveIntegerField(default=0)),
                ("error_rows", models.PositiveIntegerField(default=0)),
                ("ingested_at", models.DateTimeField(blank=True, null=True)),
                (
                    "product_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "warehouse_id",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("snapshot_date", models.DateField(blank=True, null=True)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventorystagingrecord_records",
                        to="ingestion.ingestionjob",
                    ),
                ),
            ],
            options={
                "db_table": "ingestion_inventory_staging",
                "ordering": ["-ingested_at"],
            },
        ),
    ]
