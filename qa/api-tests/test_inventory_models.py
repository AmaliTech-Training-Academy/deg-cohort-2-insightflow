"""
Tests for inventory models (Store, Category, Product, Inventory).
"""

import pytest
from apps.ingestion.models.inventory import Category, Inventory, Product, Store


@pytest.mark.django_db
class TestStoreModel:
    """Test cases for the Store model."""

    def test_create_store(self):
        """Test creating a store."""
        store = Store.objects.create(
            storeId=1, storeName="Downtown Store", province="Ontario"
        )
        assert store.storeId == 1
        assert store.storeName == "Downtown Store"
        assert store.province == "Ontario"

    def test_store_db_table(self):
        """Test that Store model uses correct database table."""
        assert Store._meta.db_table == "store"

    def test_store_primary_key(self):
        """Test that storeId is the primary key."""
        store = Store.objects.create(
            storeId=1, storeName="Downtown Store", province="Ontario"
        )
        store2 = Store.objects.get(pk=1)
        assert store2.storeId == store.storeId

    def test_store_fields_max_length(self):
        """Test store fields constraints."""
        store_name_field = Store._meta.get_field("storeName")
        assert store_name_field.max_length == 255

        province_field = Store._meta.get_field("province")
        assert province_field.max_length == 255

    def test_store_update(self):
        """Test updating a store."""
        store = Store.objects.create(
            storeId=1, storeName="Downtown", province="Ontario"
        )
        store.storeName = "Uptown"
        store.save()
        updated = Store.objects.get(storeId=1)
        assert updated.storeName == "Uptown"

    def test_store_deletion(self):
        """Test deleting a store."""
        store = Store.objects.create(storeId=1, storeName="Test", province="Ontario")
        store_id = store.storeId
        store.delete()
        assert Store.objects.filter(storeId=store_id).exists() is False

    def test_multiple_stores(self):
        """Test creating multiple stores."""
        for i in range(1, 4):
            Store.objects.create(
                storeId=i, storeName=f"Store {i}", province=f"Province {i}"
            )
        assert Store.objects.count() == 3

    def test_store_string_representation(self):
        """Test store string representation."""
        store = Store.objects.create(
            storeId=1, storeName="Downtown Store", province="Ontario"
        )
        assert str(store.storeName) == "Downtown Store"


@pytest.mark.django_db
class TestCategoryModel:
    """Test cases for the Category model."""

    def test_create_category(self):
        """Test creating a category."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        assert category.categoryId == 1
        assert category.name == "Electronics"

    def test_category_db_table(self):
        """Test that Category model uses correct database table."""
        assert Category._meta.db_table == "category"

    def test_category_primary_key(self):
        """Test that categoryId is the primary key."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        category2 = Category.objects.get(pk=1)
        assert category2.categoryId == category.categoryId

    def test_category_name_max_length(self):
        """Test category name field constraints."""
        name_field = Category._meta.get_field("name")
        assert name_field.max_length == 255

    def test_category_update(self):
        """Test updating a category."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        category.name = "Gadgets"
        category.save()
        updated = Category.objects.get(categoryId=1)
        assert updated.name == "Gadgets"

    def test_multiple_categories(self):
        """Test creating multiple categories."""
        categories = ["Electronics", "Clothing", "Food", "Books"]
        for i, cat_name in enumerate(categories, 1):
            Category.objects.create(categoryId=i, name=cat_name)
        assert Category.objects.count() == 4

    def test_category_deletion(self):
        """Test deleting a category."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        category_id = category.categoryId
        category.delete()
        assert Category.objects.filter(categoryId=category_id).exists() is False


@pytest.mark.django_db
class TestProductModel:
    """Test cases for the Product model."""

    def test_create_product_with_sku(self):
        """Test creating a product with custom SKU."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=category
        )
        assert product.productSKU == "PROD-0000001"
        assert product.productName == "Laptop"
        assert product.categoryId == category

    def test_create_product_auto_sku(self):
        """Test creating a product with auto-generated SKU."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(productName="Laptop", categoryId=category)
        assert product.productSKU == "PROD-0000001"

    def test_product_auto_sku_increment(self):
        """Test that auto-generated SKUs increment correctly."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product1 = Product.objects.create(productName="Laptop", categoryId=category)
        product2 = Product.objects.create(productName="Desktop", categoryId=category)
        product3 = Product.objects.create(productName="Tablet", categoryId=category)

        assert product1.productSKU == "PROD-0000001"
        assert product2.productSKU == "PROD-0000002"
        assert product3.productSKU == "PROD-0000003"

    def test_product_db_table(self):
        """Test that Product model uses correct database table."""
        assert Product._meta.db_table == "product"

    def test_product_primary_key(self):
        """Test that productSKU is the primary key."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=category
        )
        product2 = Product.objects.get(pk="PROD-0000001")
        assert product2.productSKU == product.productSKU

    def test_product_foreign_key_to_category(self):
        """Test product foreign key relationship to category."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=category
        )
        assert product.categoryId.categoryId == 1
        assert product.categoryId.name == "Electronics"

    def test_product_update(self):
        """Test updating a product."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=category
        )
        product.productName = "Gaming Laptop"
        product.save()
        updated = Product.objects.get(productSKU="PROD-0000001")
        assert updated.productName == "Gaming Laptop"

    def test_product_deletion_cascade(self):
        """Test deleting a category cascades to products."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(  # noqa F841
            productSKU="PROD-0000001", productName="Laptop", categoryId=category
        )
        category.delete()
        assert Product.objects.filter(productSKU="PROD-0000001").exists() is False

    def test_product_sku_format(self):
        """Test auto-generated SKU format."""
        category = Category.objects.create(categoryId=1, name="Electronics")
        product = Product.objects.create(productName="Laptop", categoryId=category)
        assert product.productSKU.startswith("PROD-")
        assert len(product.productSKU) == 12


@pytest.mark.django_db
class TestInventoryModel:
    """Test cases for the Inventory model."""

    def setup_method(self):
        """Setup test data."""
        self.category = Category.objects.create(categoryId=1, name="Electronics")
        self.product = Product.objects.create(
            productSKU="PROD-0000001", productName="Laptop", categoryId=self.category
        )

    def test_create_inventory(self):
        """Test creating an inventory entry."""
        from datetime import date

        inventory = Inventory.objects.create(
            inventoryId=1,
            productSKU=self.product,
            currentStockQty=100,
            reorderThreshold=20,
            lastRestockedDate=date.today(),
        )
        assert inventory.inventoryId == 1
        assert inventory.productSKU == self.product
        assert inventory.currentStockQty == 100
        assert inventory.reorderThreshold == 20

    def test_inventory_db_table(self):
        """Test that Inventory model uses correct database table."""
        assert Inventory._meta.db_table == "inventory"

    def test_inventory_primary_key(self):
        """Test that inventoryId is the primary key."""
        from datetime import date

        inventory = Inventory.objects.create(
            inventoryId=1,
            productSKU=self.product,
            currentStockQty=100,
            reorderThreshold=20,
            lastRestockedDate=date.today(),
        )
        inv2 = Inventory.objects.get(pk=1)
        assert inv2.inventoryId == inventory.inventoryId

    def test_inventory_stock_tracking(self):
        """Test inventory stock tracking."""
        from datetime import date

        inventory = Inventory.objects.create(
            inventoryId=1,
            productSKU=self.product,
            currentStockQty=100,
            reorderThreshold=20,
            lastRestockedDate=date.today(),
        )
        inventory.currentStockQty -= 10
        inventory.save()
        updated = Inventory.objects.get(inventoryId=1)
        assert updated.currentStockQty == 90

    def test_inventory_deletion_cascade(self):
        """Test deleting a product cascades to inventory."""
        from datetime import date

        inventory = Inventory.objects.create(  # noqa F841
            inventoryId=1,
            productSKU=self.product,
            currentStockQty=100,
            reorderThreshold=20,
            lastRestockedDate=date.today(),
        )
        self.product.delete()
        assert Inventory.objects.filter(inventoryId=1).exists() is False

    def test_inventory_multiple_entries(self):
        """Test creating multiple inventory entries."""
        from datetime import date

        for i in range(1, 4):
            product = Product.objects.create(
                productName=f"Product {i}", categoryId=self.category
            )
            Inventory.objects.create(
                inventoryId=i,
                productSKU=product,
                currentStockQty=100 * i,
                reorderThreshold=20,
                lastRestockedDate=date.today(),
            )
        assert Inventory.objects.count() == 3
