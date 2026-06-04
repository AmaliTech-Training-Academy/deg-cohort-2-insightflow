import logging
from datetime import datetime as dt
from decimal import Decimal

import pandas as pd
from apps.core.exceptions import (
    CSVParseException,
    FileSizeLimitException,
    UnsupportedFileTypeException,
    ValidationException,
)
from django.db import transaction as db_transaction
from django.utils import timezone

from ..models.base import InjectionJob
from ..models.inventory import Product, Store
from ..models.pos import Cashier, PosTransaction, PosTransactionLine
from ..validators.pos import validate_pos_file_columns, validate_pos_row

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB


class POSIngestionService:

    # ── Phase 1 — view calls this ─────────────────────────────

    def validate_upload(self, file) -> None:
        """
        File-level checks only. Fast. No DB writes.
        Raises a specific exception on failure; returns None on success.
        """

        # size check
        if file.size > MAX_UPLOAD_BYTES:
            mb = round(file.size / (1024 * 1024), 1)
            raise FileSizeLimitException(detail=f"File is {mb}MB — maximum is 50MB")

        # extension check
        if not file.name.lower().endswith(".csv"):
            raise UnsupportedFileTypeException(detail="Only .csv files are accepted")

        # can pandas even open it?
        try:
            df_header = pd.read_csv(file, nrows=0)
            file.seek(0)
        except (
            pd.errors.ParserError,
            pd.errors.EmptyDataError,
            UnicodeDecodeError,
            OSError,
        ):
            raise CSVParseException()

        # required columns check
        missing = validate_pos_file_columns(df_header.columns.tolist())
        if missing:
            raise ValidationException(
                detail="Missing required columns",
                details={"missing_columns": missing},
            )

    def accept_upload(self, file, uploaded_by=None) -> InjectionJob:
        """
        Creates the InjectionJob and saves the file to disk.
        Returns the job so the view can dispatch the Celery task.
        """
        total_rows = self._count_rows(file)

        job: InjectionJob = InjectionJob.objects.create(
            status=InjectionJob.StatusChoices.PENDING,
            total_rows=total_rows,
        )

        job.file = file
        job.save(update_fields=["file"])

        logger.info(
            f"POS upload accepted — "
            f"job={job.id}, file={file.name}, "
            f"rows={total_rows}, user={uploaded_by}"
        )

        return job

    # ── Phase 2 — Celery task calls this ─────────────────────

    def process_job(self, job: InjectionJob) -> None:
        """
        Reads the saved CSV, validates all rows, then inserts into DB using
        two bulk_create calls instead of one DB round-trip per transaction.

        Optimisations vs. the naive approach:
        - Vectorized validation: pandas/numpy column ops; Python loop only over
          the (small) invalid subset for detailed error messages.
        - Single bulk_create for all PosTransaction rows (ignore_conflicts keeps
          idempotency — re-uploading the same file is safe).
        - Single bulk_create for all PosTransactionLine rows across every txn.
        """
        job.status = InjectionJob.StatusChoices.RUNNING
        job.save(update_fields=["status"])

        try:
            df = pd.read_csv(job.file.path)
            df.columns = df.columns.str.strip().str.lower()

            # ── Phase 1: Vectorized validation ───────────────────────────
            # Null / empty checks across all required columns (numpy-level)
            required = [
                "transaction_id",
                "store_id",
                "cashier_id",
                "product_sku",
                "quantity",
                "unit_price",
                "discount_applied",
                "total",
                "date",
            ]
            null_mask = df[required].isna().any(axis=1)
            for col in ["transaction_id", "store_id", "product_sku"]:
                null_mask |= df[col].astype(str).str.strip() == ""

            # Numeric field validation (vectorized, C-level)
            cashier_num = pd.to_numeric(df["cashier_id"], errors="coerce")
            qty_num = pd.to_numeric(df["quantity"], errors="coerce")
            price_num = pd.to_numeric(df["unit_price"], errors="coerce")
            disc_num = pd.to_numeric(df["discount_applied"], errors="coerce")
            total_num = pd.to_numeric(df["total"], errors="coerce")

            numeric_ok = (
                cashier_num.notna()
                & (cashier_num > 0)
                & qty_num.notna()
                & (qty_num > 0)
                & price_num.notna()
                & (price_num > 0)
                & disc_num.notna()
                & (disc_num >= 0)
                & total_num.notna()
                & (total_num > 0)
            )

            # Date parsing via apply (C-level string ops per cell)
            df["_parsed_date"] = df["date"].apply(self._parse_date_field)
            date_ok = df["_parsed_date"].notna()

            valid_mask = ~null_mask & numeric_ok & date_ok
            valid_df = df[valid_mask].copy()
            invalid_df = df[~valid_mask]

            # Collect detailed errors only for invalid rows (small subset)
            row_errors: list = []
            for idx, row in invalid_df.iterrows():
                row_dict = {
                    k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                    for k, v in row.to_dict().items()
                    if not k.startswith("_")
                }
                row_errors.extend(validate_pos_row(row_dict, row_num=idx + 2))

            # Intermediate progress save (DB-level rejections not yet known)
            job.error_rows = len(invalid_df)
            job.save(update_fields=["error_rows"])

            # ── Phase 2: Bulk DB insert ───────────────────────────────────
            with db_transaction.atomic():
                # Three FK sets — one query each, O(1) membership check in loop
                valid_store_ids = set(Store.objects.values_list("storeId", flat=True))
                valid_cashier_ids = set(
                    Cashier.objects.values_list("cashierId", flat=True)
                )
                valid_product_skus = set(
                    Product.objects.values_list("productSKU", flat=True)
                )

                # Group rows by transaction_id (pandas groupby — C-level)
                transactions_map: dict = {}
                for txn_id, group in valid_df.groupby("transaction_id"):
                    first = group.iloc[0]
                    transactions_map[txn_id] = {
                        "store_id": first["store_id"],
                        "cashier_id": first["cashier_id"],
                        "parsed_date": first["_parsed_date"],
                        "lines": group.to_dict("records"),
                    }

                # Build all PosTransaction objects — zero DB calls
                txn_objects: list = []
                skipped_txns: set = set()
                db_rejected_count: int = 0

                for txn_id, txn_data in transactions_map.items():
                    if int(txn_data["store_id"]) not in valid_store_ids:
                        row_errors.append(
                            {
                                "transaction_id": txn_id,
                                "field": "store_id",
                                "error": f'Store {txn_data["store_id"]} does not exist',
                            }
                        )
                        skipped_txns.add(txn_id)
                        db_rejected_count += len(txn_data["lines"])
                        continue

                    if int(txn_data["cashier_id"]) not in valid_cashier_ids:
                        row_errors.append(
                            {
                                "transaction_id": txn_id,
                                "field": "cashier_id",
                                "error": (
                                    f"Cashier {txn_data['cashier_id']}"
                                    " does not exist"
                                ),
                            }
                        )
                        skipped_txns.add(txn_id)
                        db_rejected_count += len(txn_data["lines"])
                        continue

                    naive = txn_data["parsed_date"]
                    aware = (
                        timezone.make_aware(naive, timezone.utc)
                        if timezone.is_naive(naive)
                        else naive
                    )
                    txn_objects.append(
                        PosTransaction(
                            posTransactionId=int(txn_id),
                            storeId_id=int(txn_data["store_id"]),
                            cashierId_id=int(txn_data["cashier_id"]),
                            transactionDatetime=aware,
                        )
                    )

                # ONE bulk_create for ALL transactions
                # ignore_conflicts=True makes re-uploads idempotent
                if txn_objects:
                    PosTransaction.objects.bulk_create(
                        txn_objects, ignore_conflicts=True
                    )

                # Build ALL PosTransactionLine objects — zero DB calls
                all_line_records: list = []
                for txn_id, txn_data in transactions_map.items():
                    if txn_id in skipped_txns:
                        continue
                    for line_idx, line_dict in enumerate(txn_data["lines"], 1):
                        sku = line_dict["product_sku"]
                        if sku not in valid_product_skus:
                            row_errors.append(
                                {
                                    "transaction_id": txn_id,
                                    "field": "product_sku",
                                    "error": f"Product {sku} does not exist",
                                }
                            )
                            db_rejected_count += 1
                            continue
                        # Zero-pad both parts so txn=12/line=31 ≠ txn=123/line=1
                        line_id = int(f"{int(txn_id):012d}{line_idx:03d}")
                        try:
                            all_line_records.append(
                                PosTransactionLine(
                                    lineId=line_id,
                                    posTransactionId_id=int(txn_id),
                                    productSKU_id=sku,
                                    quantity=int(line_dict["quantity"]),
                                    unitPrice=Decimal(str(line_dict["unit_price"])),
                                    discountApplied=Decimal(
                                        str(line_dict["discount_applied"])
                                    ),
                                    totalAmount=Decimal(str(line_dict["total"])),
                                )
                            )
                        except Exception as e:
                            row_errors.append(
                                {
                                    "transaction_id": txn_id,
                                    "field": "PosTransactionLine",
                                    "error": f"Failed to build line item: {e}",
                                }
                            )

                # ONE bulk_create for ALL lines across every transaction
                if all_line_records:
                    PosTransactionLine.objects.bulk_create(
                        all_line_records,
                        batch_size=1000,
                        ignore_conflicts=True,
                    )

                job.status = InjectionJob.StatusChoices.COMPLETED
                job.valid_rows = len(valid_df) - db_rejected_count
                job.rejected_rows = db_rejected_count
                job.error_rows = len(invalid_df)
                job.error_report = {"row_errors": row_errors} if row_errors else {}
                job.save()

            logger.info(
                f"POS job {job.id} done — "
                f"valid={len(valid_df)}, errors={len(row_errors)}, "
                f"transactions={len(txn_objects)}"
            )

        except Exception as e:
            logger.exception(f"POS job {job.id} failed — {e}")
            job.status = InjectionJob.StatusChoices.FAILED
            job.error_report = {"fatal_error": str(e)}
            job.save(update_fields=["status", "error_report"])
            raise

    # ── private ───────────────────────────────────────────────

    @staticmethod
    def _parse_date_field(val) -> dt | None:
        """Parse a single date/datetime cell; return None if unparseable."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        raw = str(val).strip()
        if not raw:
            return None
        try:
            return dt.fromisoformat(raw)
        except ValueError:
            pass
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                return dt.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    def _count_rows(self, file) -> int:
        try:
            count = sum(1 for _ in file) - 1
            file.seek(0)
            return max(count, 0)
        except Exception:
            file.seek(0)
            return 0
