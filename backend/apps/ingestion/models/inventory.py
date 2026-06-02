from apps.core.models import TimeStampedModel
from django.db import models


class Store(TimeStampedModel):
    storeId = models.IntegerField(primary_key=True, db_column="storeId")
    storeName = models.CharField(max_length=255, db_column="storeName")
    province = models.CharField(max_length=255, db_column="province")

    class Meta:
        db_table = "store"


class Category(models.Model):
    categoryId = models.IntegerField(primary_key=True, db_column="categoryId")
    name = models.CharField(max_length=255, db_column="name")

    class Meta:
        db_table = "category"


class Product(models.Model):
    productSKU = models.CharField(
        max_length=20, primary_key=True, db_column="productSKU"
    )
    productName = models.CharField(max_length=255, db_column="productName")
    categoryId = models.ForeignKey(
        Category, on_delete=models.CASCADE, db_column="categoryId"
    )

    class Meta:
        db_table = "product"

    def save(self, *args, **kwargs):
        if not self.productSKU:
            last_product = Product.objects.all().order_by("productSKU").last()
            if not last_product:
                self.productSKU = "PROD-0000001"
            else:
                last_number = int(last_product.productSKU.split("-")[1])
                next_number = last_number + 1
                self.productSKU = f"PROD-{next_number:07d}"
        super().save(*args, **kwargs)


class Inventory(models.Model):
    inventoryId = models.IntegerField(primary_key=True, db_column="inventoryId")
    productSKU = models.ForeignKey(
        Product, on_delete=models.CASCADE, to_field="productSKU", db_column="productSKU"
    )
    currentStockQty = models.IntegerField(db_column="currentStockQty")
    reorderThreshold = models.IntegerField(db_column="reorderThreshold")
    lastRestockedDate = models.DateField(db_column="lastRestockedDate")

    class Meta:
        db_table = "inventory"
