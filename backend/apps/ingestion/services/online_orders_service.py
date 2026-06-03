import logging
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


class OnlineOrdersIngestionService:
    def __init__(self) -> None:
        self._system_user_id_cache: int | None = None
        self._default_category_id_cache: int | None = None

    def create_job(self, trigger: str = "scheduled") -> OnlineInjectionJob:
        job: OnlineInjectionJob = OnlineInjectionJob.objects.create(
            status=OnlineInjectionJob.StatusChoices.PENDING,
            trigger=trigger,
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
                page_valid, page_errors, page_err_details = self._process_page(page_data, job)
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
            logger.info("OnlineInjectionJob %s completed — valid=%s errors=%s", job.id, valid, errors)

        except OnlineOrdersAPIError as exc:
            logger.exception("OnlineInjectionJob %s failed: %s", job.id, exc)
            job.status = OnlineInjectionJob.StatusChoices.FAILED
            job.error_report = {"fatal_error": str(exc)}
            job.save(update_fields=["status", "error_report"])
            raise

    def _process_page(
        self, orders: list[dict[str, Any]], job: OnlineInjectionJob
    ) -> tuple[int, int, list[dict[str, Any]]]:
        valid = errors = 0
        err_details: list[dict[str, Any]] = []

        with db_transaction.atomic():
            for order_dict in orders:
                order_errors = validate_order(order_dict)
                if order_errors:
                    errors += 1
                    err_details.append(
                        {"order_id": order_dict.get("onlineOrderId"), "errors": order_errors}
                    )
                    continue
                try:
                    self._upsert_order(order_dict)
                    valid += 1
                except Exception as exc:
                    logger.warning(
                        "Job %s — order %s failed: %s",
                        job.id,
                        order_dict.get("onlineOrderId"),
                        exc,
                    )
                    errors += 1

        return valid, errors, err_details

    def _upsert_order(self, order_dict: dict[str, Any]) -> None:
        dt = parse_datetime(str(order_dict["orderDatetime"]))
        if dt is None:
            logger.warning("Unparseable orderDatetime for order %s — skipping", order_dict.get("onlineOrderId"))
            return

        customer, _ = Customer.objects.get_or_create(
            customerId=order_dict["customerId"],
            defaults={"userId_id": self._system_user_id},
        )

        order, _ = OnlineOrder.objects.update_or_create(
            onlineOrderId=int(order_dict["onlineOrderId"]),
            defaults={
                "customerId": customer,
                "orderDatetime": dt,
                "shippingProvince": order_dict.get("shippingProvince", ""),
                "orderStatus": order_dict["orderStatus"],
                "paymentMethod": order_dict["paymentMethod"],
            },
        )

        for line_dict in order_dict.get("lines", []):
            if validate_order_line(line_dict, order_id=order.onlineOrderId):
                continue
            product, _ = Product.objects.get_or_create(
                productSKU=line_dict["productSKU"],
                defaults={
                    "productName": line_dict["productSKU"],
                    "categoryId_id": self._default_category_id,
                },
            )
            OnlineOrderLine.objects.get_or_create(
                lineId=int(line_dict["lineId"]),
                defaults={
                    "onlineOrderId": order,
                    "productSKU": product,
                    "quantity": int(line_dict["quantity"]),
                    "unitPrice": Decimal(str(line_dict["unitPrice"])),
                    "discountApplied": Decimal(str(line_dict["discountApplied"])),
                    "totalAmount": Decimal(str(line_dict["totalAmount"])),
                },
            )

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
