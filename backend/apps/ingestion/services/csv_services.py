import logging
from datetime import datetime as dt
from decimal import Decimal

import pandas as pd
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.core.exceptions import (
    CSVParseException,
    FileSizeLimitException,
    UnsupportedFileTypeException,
    ValidationException,
)

from ..models.base import InjectionJob
from ..models.pos import PosTransaction, PosTransactionLine
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
            raise FileSizeLimitException(
                detail=f"File is {mb}MB — maximum is 50MB"
            )

        # extension check
        if not file.name.lower().endswith(".csv"):
            raise UnsupportedFileTypeException(
                detail="Only .csv files are accepted"
            )

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
        Reads the saved CSV row by row.
        - Groups rows by transaction_id
        - Creates PosTransaction records
        - Creates PosTransactionLine records for each product
        - Logs errors for invalid rows
        """
        job.status = InjectionJob.StatusChoices.RUNNING
        job.save(update_fields=["status"])

        try:
            df = pd.read_csv(job.file.path)
            df.columns = df.columns.str.strip().str.lower()

            valid_rows = []
            row_errors = []

            # ── Phase 1: Validate all rows ────────────────────────
            # to_dict(orient="records") is significantly faster than iterrows
            for idx, row_dict in enumerate(df.to_dict(orient="records")):
                row_num = idx + 2  # +1 header, +1 for 1-based display
                # Replace float NaN with None so validators see proper nulls
                row_dict = {
                    k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                    for k, v in row_dict.items()
                }

                errors = validate_pos_row(row_dict, row_num=row_num)

                if errors:
                    row_errors.extend(errors)
                else:
                    valid_rows.append((idx, row_dict))

                # live progress update every 500 rows
                if idx > 0 and idx % 500 == 0:
                    job.valid_rows = len(valid_rows)
                    job.error_rows = len(row_errors)
                    job.save(update_fields=["valid_rows", "error_rows"])

            # ── Phase 2: Insert into PosTransaction + PosTransactionLine ──
            with db_transaction.atomic():
                # Group valid rows by transaction_id
                transactions_map: dict = {}
                for _idx, row_dict in valid_rows:
                    txn_id = row_dict["transaction_id"]
                    if txn_id not in transactions_map:
                        transactions_map[txn_id] = {
                            "store_id": row_dict["store_id"],
                            "cashier_id": row_dict["cashier_id"],
                            "date": row_dict["date"],
                            "lines": [],
                        }
                    transactions_map[txn_id]["lines"].append(row_dict)

                for txn_id, txn_data in transactions_map.items():
                    # ── Parse date — produce a timezone-aware UTC datetime ──
                    date_str = str(txn_data["date"])
                    parsed_date = None
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                        try:
                            naive = dt.strptime(date_str, fmt).replace(
                                hour=0, minute=0, second=0
                            )
                            parsed_date = timezone.make_aware(naive, timezone.utc)
                            break
                        except ValueError:
                            continue

                    if parsed_date is None:
                        row_errors.append(
                            {
                                "transaction_id": txn_id,
                                "field": "date",
                                "error": f'Cannot parse date "{date_str}"',
                            }
                        )
                        continue

                    # ── PosTransaction — get_or_create prevents duplicate key ──
                    try:
                        pos_txn, created = PosTransaction.objects.get_or_create(
                            posTransactionId=int(txn_id),
                            defaults={
                                "storeId_id": int(txn_data["store_id"]),
                                "cashierId_id": int(txn_data["cashier_id"]),
                                "transactionDatetime": parsed_date,
                            },
                        )
                    except Exception as e:
                        row_errors.append(
                            {
                                "transaction_id": txn_id,
                                "field": "PosTransaction",
                                "error": f"Failed to create transaction: {e}",
                            }
                        )
                        continue

                    if not created:
                        # Already ingested — skip line items to avoid duplicates
                        logger.warning(
                            f"Job {job.id} — txn {txn_id} already exists, skipping"
                        )
                        continue

                    # ── Build PosTransactionLine records ─────────────────
                    line_records = []
                    for line_idx, line_dict in enumerate(txn_data["lines"], 1):
                        try:
                            # Zero-pad both parts so txn=12/line=31 ≠ txn=123/line=1
                            line_id = int(f"{int(txn_id):012d}{line_idx:03d}")
                            line_records.append(
                                PosTransactionLine(
                                    lineId=line_id,
                                    posTransactionId=pos_txn,
                                    productSKU_id=line_dict["product_sku"],
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

                    if line_records:
                        try:
                            PosTransactionLine.objects.bulk_create(
                                line_records, batch_size=1000
                            )
                        except Exception as e:
                            row_errors.append(
                                {
                                    "transaction_id": txn_id,
                                    "field": "bulk_insert",
                                    "error": f"Bulk insert failed: {e}",
                                }
                            )

                # ── Mark job complete ────
                job.status = InjectionJob.StatusChoices.COMPLETED
                job.valid_rows = len(valid_rows)
                job.error_rows = len(row_errors)
                job.error_report = {"row_errors": row_errors} if row_errors else {}
                job.save()

            logger.info(
                f"POS job {job.id} done — "
                f"valid={len(valid_rows)}, errors={len(row_errors)}, "
                f"transactions={len(transactions_map)}"
            )

        except Exception as e:
            logger.exception(f"POS job {job.id} failed — {e}")
            job.status = InjectionJob.StatusChoices.FAILED
            job.error_report = {"fatal_error": str(e)}
            job.save(update_fields=["status", "error_report"])
            raise

    # ── private ───────────────────────────────────────────────

    def _count_rows(self, file) -> int:
        try:
            count = sum(1 for _ in file) - 1
            file.seek(0)
            return max(count, 0)
        except Exception:
            file.seek(0)
            return 0
