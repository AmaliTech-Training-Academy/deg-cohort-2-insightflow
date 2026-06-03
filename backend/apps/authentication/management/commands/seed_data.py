import random

from apps.authentication.models import User
from apps.ingestion.models.base import Customer
from apps.ingestion.models.inventory import Category, Product, Store
from apps.ingestion.models.pos import Cashier
from django.core.management.base import BaseCommand
from faker import Faker

fake = Faker()


class Command(BaseCommand):
    help = "Seed with initial data "

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.HTTP_INFO("Starting database seeding..."))

        # Clear existing data
        self.stdout.write("Clearing existing data...")
        User.objects.exclude(is_superuser=True).delete()
        Store.objects.all().delete()
        Category.objects.all().delete()
        Cashier.objects.all().delete()
        Customer.objects.all().delete()
        Product.objects.all().delete()

        # Create Stores
        self.stdout.write("Creating stores...")
        stores = []
        store_names = [
            "Downtown Store",
            "Mall Store",
            "Airport Store",
            "Harbor Store",
            "Central Park Store",
            "Tech Hub Store",
            "Market Square Store",
            "Riverside Store",
            "Grand Plaza Store",
            "Urban Center Store",
        ]
        provinces = ["Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba"]

        for i, store_name in enumerate(store_names, 1):
            store = Store.objects.create(
                storeId=i,
                storeName=store_name,
                province=random.choice(provinces),  # nosec
            )
            stores.append(store)
        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(stores)} stores"))

        # Create Categories
        self.stdout.write("Creating categories...")
        categories = []
        category_names = [
            "Electronics",
            "Clothing",
            "Groceries",
            "Home & Garden",
            "Sports & Outdoors",
            "Books & Media",
            "Toys & Games",
            "Beauty & Personal Care",
            "Food & Beverages",
            "Office Supplies",
        ]

        for i, cat_name in enumerate(category_names, 1):
            category = Category.objects.create(categoryId=i, name=cat_name)
            categories.append(category)
        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(categories)} categories"))

        # Create Users (Admin, Cashiers, Customers)
        self.stdout.write("Creating users...")
        users = []
        roles = ["admin", "cashier", "customer"]

        # Create or get superuser
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@insightflow.com",
                "is_superuser": True,
                "is_staff": True,
                "role": "admin",
            },
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
        users.append(admin_user)

        # Create 20 regular users with different roles
        for i in range(1, 21):
            role = random.choice(roles)  # nosec B311
            username = f"{role}_{i}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{role}{i}@insightflow.com",
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "role": role,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(f"password{i}")
                user.save()
            users.append(user)

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(users)} users"))

        # Create Cashiers
        self.stdout.write("Creating cashiers...")
        cashiers = []
        cashier_users = [u for u in users if u.role == "cashier"]
        # Create more cashiers than dedicated cashier users by
        # assigning multiple cashiers to some users
        for i, user in enumerate(cashier_users, 1):
            num_positions = random.randint(1, 2)  # nosec B311
            for j in range(num_positions):
                cashier = Cashier.objects.create(
                    cashierId=len(cashiers) + i * 10 + j,
                    storeId=random.choice(stores),  # nosec B311
                    fullName=f"{user.first_name} {user.last_name}",
                    userId=user,
                )
                cashiers.append(cashier)

        # If we don't have enough cashiers, create some more with regular users
        while len(cashiers) < 20:
            user = random.choice(users)  # nosec B311
            cashier = Cashier.objects.create(
                cashierId=5000 + len(cashiers),
                storeId=random.choice(stores),  # nosec B311
                fullName=f"{fake.first_name()} {fake.last_name()}",
                userId=user,
            )
            cashiers.append(cashier)

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(cashiers)} cashiers"))

        # Create Customers
        self.stdout.write("Creating customers...")
        customers = []
        customer_users = [u for u in users if u.role == "customer"]

        # Create customers from customer-role users
        for user in customer_users:
            customer = Customer.objects.create(userId=user)
            customers.append(customer)

        # Create additional customers to reach 50+
        customer_counter = User.objects.filter(role="customer").count() + 1
        while len(customers) < 50:
            # Create new users for additional customers with unique usernames
            unique_username = f"cust_{customer_counter}_{fake.first_name().lower()}"
            customer_user = User.objects.create_user(
                username=unique_username,
                email=fake.email(),
                password="password123",  # nosec B106
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                role="customer",
                is_active=True,
            )
            customer = Customer.objects.create(userId=customer_user)
            customers.append(customer)
            customer_counter += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(customers)} customers"))

        # Create Products
        self.stdout.write("Creating products...")
        product_names_by_category = {
            "Electronics": [
                "Laptop",
                "Smartphone",
                "Tablet",
                "Headphones",
                "Monitor",
                "Keyboard",
                "Mouse",
                "USB Cable",
                "Charger",
                "Speaker",
            ],
            "Clothing": [
                "T-Shirt",
                "Jeans",
                "Dress",
                "Jacket",
                "Shoes",
                "Socks",
                "Hat",
                "Scarf",
                "Gloves",
                "Sweater",
            ],
            "Groceries": [
                "Milk",
                "Bread",
                "Eggs",
                "Cheese",
                "Yogurt",
                "Butter",
                "Coffee",
                "Tea",
                "Rice",
                "Pasta",
            ],
            "Home & Garden": [
                "Pillow",
                "Bedsheet",
                "Towel",
                "Lamp",
                "Mirror",
                "Vase",
                "Plant",
                "Pot",
                "Curtain",
                "Rug",
            ],
            "Sports & Outdoors": [
                "Running Shoes",
                "Yoga Mat",
                "Dumbbell",
                "Bicycle",
                "Football",
                "Tennis Racket",
                "Skateboard",
                "Backpack",
                "Water Bottle",
                "Tent",
            ],
            "Books & Media": [
                "Novel",
                "Magazine",
                "Comic",
                "DVD",
                "CD",
                "Audiobook",
                "Poster",
                "Calendar",
                "Notebook",
                "Pen",
            ],
            "Toys & Games": [
                "Action Figure",
                "Board Game",
                "Puzzle",
                "Video Game",
                "Toy Car",
                "Doll",
                "Building Block",
                "Card Game",
                "Remote Control",
                "Kite",
            ],
            "Beauty & Personal Care": [
                "Shampoo",
                "Conditioner",
                "Soap",
                "Toothpaste",
                "Perfume",
                "Lotion",
                "Makeup",
                "Deodorant",
                "Razor",
                "Moisturizer",
            ],
            "Food & Beverages": [
                "Chocolate",
                "Chips",
                "Candy",
                "Soda",
                "Juice",
                "Coffee",
                "Water",
                "Energy Drink",
                "Protein Bar",
                "Cookies",
            ],
            "Office Supplies": [
                "Paper",
                "Pen",
                "Pencil",
                "Marker",
                "Notebook",
                "Folder",
                "Stapler",
                "Tape",
                "Scissors",
                "Ruler",
            ],
        }

        # Build all products with manually generated SKUs
        products_to_create = []
        sku_counter = 1
        for category in categories:
            product_names = product_names_by_category.get(
                category.name, ["Generic Product"]
            )
            for product_name in product_names:
                for variant in range(1, 13):  # Create 12 variants of each product
                    products_to_create.append(
                        Product(
                            productSKU=f"PROD-{sku_counter:07d}",
                            productName=f"{product_name} - Variant {variant}",
                            categoryId=category,
                        )
                    )
                    sku_counter += 1

        # Bulk create all products (faster than individual creates)
        Product.objects.bulk_create(products_to_create, batch_size=500)
        self.stdout.write(
            self.style.SUCCESS(f"✓ Created {len(products_to_create)} products")
        )

        # Summary
        total_records = (
            len(users)
            + len(stores)
            + len(categories)
            + len(cashiers)
            + len(customers)
            + len(products_to_create)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Database seeding completed successfully!"
                f"\n\nSummary:"
                f"\n  - Stores: {len(stores)}"
                f"\n  - Categories: {len(categories)}"
                f"\n  - Users: {len(users)}"
                f"\n  - Cashiers: {len(cashiers)}"
                f"\n  - Customers: {len(customers)}"
                f"\n  - Products: {len(products_to_create)}"
                f"\n  ─────────────────"
                f"\n  Total Records: {total_records}"
            )
        )
