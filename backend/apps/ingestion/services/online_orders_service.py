import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction as db_transaction
from django.utils.dateparse import parse_datetime

from ..connectors.online_orders import OnlineOrdersAPIError, iter_all_pages
from ..models.base import Customer
from ..models.inventory import Category, Product
from ..models.online_injection_job import OnlineInjectionJob
from ..models.online_orders import OnlineOrder, OnlineOrderLine
from ..validators.online_orders import validate_order, validate_order_line

logger = logging.getLogger(__name__)

_PAGE_LIMIT = 100
_ORDER_UPDATE_FIELDS = [
    "orderDatetime",
    "shippingProvince",
    "orderStatus",
    "paymentMethod",
]


class OnlineOrdersIngestionService:
    def __init__(self) -> None:
        self._system_user_id_cache: int | None = None
        self._default_category_id_cache: int | None = None

    def create_job(self, trigger: str = "scheduled") -> OnlineInjectionJob:
        job: OnlineInjectionJob = OnlineInjectionJob.objects.create(
            status=OnlineInjectionJob.StatusChoices.PENDING, trigger=trigger
        )
        return job

    def process_job(self, job: OnlineInjectionJob) -> None:
        job.status = OnlineInjectionJob.StatusChoices.RUNNING
        job.save(update_fields=["status"])
        total = valid = errors = pages = 0
        all_errors: list[dict[str, Any]] = []
        try:
            for page_data in iter_all_pages(limit=_PAGE_LIMIT):
                pages += 1
                page_valid, page_errors, page_err_details = self._process_page(
                    page_data
                )
                total += len(page_data)
                valid += page_valid
                errors += page_errors
                all_errors.extend(page_err_details)
                job.total_orders = total
                job.valid_orders = valid
                job.error_orders = errors
                job.pages_fetched = pages
                job.save(
                    update_fields=[
                        "total_orders",
                        "valid_orders",
                        "error_orders",
                        "pages_fetched",
                    ]
                )
            job.status = OnlineInjectionJob.StatusChoices.COMPLETED
            job.error_report = {"order_errors": all_errors} if all_errors else {}
            job.save(update_fields=["status", "error_report"])
            logger.info(
                "OnlineInjectionJob %s completed — valid=%s errors=%s",
                job.id,
                valid,
                errors,
            )
        except OnlineOrdersAPIError as exc:
            logger.exception("OnlineInjectionJob %s failed: %s", job.id, exc)
            job.status = OnlineInjectionJob.StatusChoices.FAILED
            job.error_report = {"fatal_error": str(exc)}
            job.save(update_fields=["status", "error_report"])
            raise

    def _process_page(
        self, orders: list[dict[str, Any]]
    ) -> tuple[int, int, list[dict[str, Any]]]:
        to_process: list[tuple[dict[str, Any], Any]] = []
        errors = 0
        err_details: list[dict[str, Any]] = []

        now = datetime.now()
        for order_dict in orders:
            errs = validate_order(order_dict)
            if errs:
                errors += 1
                err_details.append(
                    {"order_id": order_dict.get("onlineOrderId"), "errors": errs}
                )
                continue
            dt = parse_datetime(str(order_dict["orderDatetime"]))
            if dt is None:
                errors += 1
                logger.warning(
                    "Unparseable orderDatetime for order %s",
                    order_dict.get("onlineOrderId"),
                )
                continue
            if dt.replace(tzinfo=None) > now:
                errors += 1
                err_details.append(
                    {
                        "order_id": order_dict.get("onlineOrderId"),
                        "errors": [
                            {
                                "field": "orderDatetime",
                                "error": (
                                    f"orderDatetime"
                                    f" '{order_dict['orderDatetime']}'"
                                    f" is in the future"
                                ),
                            }
                        ],
                    }
                )
                continue
            to_process.append((order_dict, dt))

        if not to_process:
            return 0, errors, err_details

        with db_transaction.atomic():
            customer_map = self._resolve_customers(
                {str(o["customerId"]) for o, _ in to_process}
            )
            order_rows = self._build_order_rows(to_process, customer_map)
            OnlineOrder.objects.bulk_create(
                order_rows,
                update_conflicts=True,
                unique_fields=["onlineOrderId"],
                update_fields=_ORDER_UPDATE_FIELDS,
            )
            self._upsert_lines(to_process)

        return len(order_rows), errors, err_details

    def _resolve_customers(self, customer_ids: set[str]) -> dict[str, Customer]:
        existing = {
            c.customerId: c
            for c in Customer.objects.filter(customerId__in=customer_ids)
        }
        missing = customer_ids - existing.keys()
        if missing:
            Customer.objects.bulk_create(
                [
                    Customer(customerId=cid, userId_id=self._system_user_id)
                    for cid in missing
                ],
                ignore_conflicts=True,
            )
            existing = {
                c.customerId: c
                for c in Customer.objects.filter(customerId__in=customer_ids)
            }
        return existing

    def _build_order_rows(
        self,
        to_process: list[tuple[dict[str, Any], Any]],
        customer_map: dict[str, Customer],
    ) -> list[OnlineOrder]:
        rows = []
        for o, dt in to_process:
            cust = customer_map.get(str(o["customerId"]))
            if cust is None:
                logger.warning(
                    "Customer %s unresolved — skipping order %s",
                    o["customerId"],
                    o.get("onlineOrderId"),
                )
                continue
            rows.append(
                OnlineOrder(
                    onlineOrderId=int(o["onlineOrderId"]),
                    customerId=cust,
                    orderDatetime=dt,
                    shippingProvince=o.get("shippingProvince", ""),
                    orderStatus=o["orderStatus"],
                    paymentMethod=o["paymentMethod"],
                )
            )
        return rows

    def _resolve_products(self, sku_set: set[str]) -> dict[str, Product]:
        prods = {
            p.productSKU: p for p in Product.objects.filter(productSKU__in=sku_set)
        }
        missing = sku_set - prods.keys()
        if missing:
            Product.objects.bulk_create(
                [
                    Product(
                        productSKU=sku,
                        productName=sku,
                        categoryId_id=self._default_category_id,
                    )
                    for sku in missing
                ],
                ignore_conflicts=True,
            )
            prods = {
                p.productSKU: p for p in Product.objects.filter(productSKU__in=sku_set)
            }
        return prods

    def _upsert_lines(self, to_process: list[tuple[dict[str, Any], Any]]) -> None:
        valid_lines: list[dict[str, Any]] = []
        sku_set: set[str] = set()
        for o, _ in to_process:
            for line in o.get("lines", []):
                if not validate_order_line(line):
                    sku_set.add(str(line["productSKU"]))
                    valid_lines.append(line)

        if not valid_lines:
            return

        prods = self._resolve_products(sku_set)
        line_rows = [
            OnlineOrderLine(
                lineId=int(line["lineId"]),
                onlineOrderId_id=int(line["onlineOrderId"]),
                productSKU=prods[str(line["productSKU"])],
                quantity=int(line["quantity"]),
                unitPrice=Decimal(str(line["unitPrice"])),
                discountApplied=Decimal(str(line["discountApplied"])),
                totalAmount=Decimal(str(line["totalAmount"])),
            )
            for line in valid_lines
            if prods.get(str(line["productSKU"])) is not None
        ]
        OnlineOrderLine.objects.bulk_create(line_rows, ignore_conflicts=True)

    @property
    def _system_user_id(self) -> int:
        if self._system_user_id_cache is None:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user, _ = User.objects.get_or_create(
                username="system",
                defaults={"email": "system@insightflow.internal", "is_active": False},
            )
            self._system_user_id_cache = int(user.pk)
        return self._system_user_id_cache

    @property
    def _default_category_id(self) -> int:
        if self._default_category_id_cache is None:
            cat, _ = Category.objects.get_or_create(
                categoryId=0, defaults={"name": "Uncategorised"}
            )
            self._default_category_id_cache = int(cat.pk)
        return self._default_category_id_cache
