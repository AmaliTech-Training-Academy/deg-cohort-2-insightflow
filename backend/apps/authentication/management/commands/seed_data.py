from apps.authentication.models import Role, User
from apps.datasources.models import DataSource, DataSourceType
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Seeds the database with initial users and data sources"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        admin, created = User.objects.get_or_create(
            email="admin@amalitech.com",
            defaults={
                "username": "admin@amalitech.com",
                "first_name": "Admin",
                "last_name": "User",
                "role": Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("password123")
            admin.save()
            self.stdout.write(
                self.style.SUCCESS("  Created admin user: admin@amalitech.com")
            )

        regular_user, created = User.objects.get_or_create(
            email="user@amalitech.com",
            defaults={
                "username": "user@amalitech.com",
                "first_name": "Regular",
                "last_name": "User",
                "role": Role.USER,
            },
        )
        if created:
            regular_user.set_password("password123")
            regular_user.save()
            self.stdout.write(
                self.style.SUCCESS("  Created regular user: user@amalitech.com")
            )

        ds1, created = DataSource.objects.get_or_create(
            name="Sales Data CSV",
            defaults={
                "type": DataSourceType.CSV,
                "file_path": "/data/sales.csv",
                "created_by": admin,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS("  Created data source: Sales Data CSV")
            )

        ds2, created = DataSource.objects.get_or_create(
            name="User Analytics API",
            defaults={
                "type": DataSourceType.API,
                "connection_url": "https://api.example.com/analytics",
                "created_by": admin,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS("  Created data source: User Analytics API")
            )

        self.stdout.write(self.style.SUCCESS("Database seeding complete."))
