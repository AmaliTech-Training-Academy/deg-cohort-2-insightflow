import logging

import pandas as pd
from django.db import transaction as db_transaction

from ..models.base import IngestionJob
from ..models.pos import PosTransaction, PosTransactionLine
from ..validators.pos import validate_pos_file_columns, validate_pos_row

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB


class POSIngestionService:

    # ── Phase 1 — view calls this ─────────────────────────────

    def validate_upload(self, file) -> dict:
        """
        File-level checks only. Fast. No DB writes.
        Returns {'ok': True} or {'ok': False, 'error': ..., ...}
        """

        # size check
        if file.size > MAX_UPLOAD_BYTES:
            mb = round(file.size / (1024 * 1024), 1)
            return {'ok': False, 'error': f'File is {mb}MB — maximum is 50MB'}

        # extension check
        if not file.name.lower().endswith('.csv'):
            return {'ok': False, 'error': 'Only .csv files are accepted'}

        # can pandas even open it?
        try:
            df_header = pd.read_csv(file, nrows=0)
            file.seek(0)
        except Exception as e:
            return {'ok': False, 'error': f'Could not read CSV: {e}'}

        # required columns check
        missing = validate_pos_file_columns(df_header.columns.tolist())
        if missing:
            return {
                'ok': False,
                'error': 'Missing required columns',
                'missing_columns': missing,
            }

        return {'ok': True}

    def accept_upload(self, file, uploaded_by=None) -> IngestionJob:
        """
        Creates the IngestionJob and saves the file to disk.
        Returns the job so the view can dispatch the Celery task.
        """
        total_rows = self._count_rows(file)

        job = IngestionJob.objects.create(
            status=IngestionJob.STATUS_PENDING,
            total_rows=total_rows,
            valid_rows=0,
            error_rows=0,
        )

        job.file = file
        job.save(update_fields=['file'])

        logger.info(
            f'POS upload accepted — '
            f'job={job.id}, file={file.name}, '
            f'rows={total_rows}, user={uploaded_by}'
        )

        return job

    # ── Phase 2 — Celery task calls this ─────────────────────

    def process_job(self, job: IngestionJob) -> None:
        """
        Reads the saved CSV row by row.
        - Groups rows by transaction_id
        - Creates PosTransaction records
        - Creates PosTransactionLine records for each product
        - Logs errors for invalid rows
        """
        job.status = IngestionJob.STATUS_RUNNING
        job.save(update_fields=['status'])

        try:
            df = pd.read_csv(job.file.path)
            df.columns = df.columns.str.strip().str.lower()

            valid_rows = []
            row_errors = []

            # ── Phase 1: Validate all rows ────────────────────────
            for idx, row in df.iterrows():
                row_num = idx + 2
                row_dict = row.where(pd.notna(row), None).to_dict()

                errors = validate_pos_row(row_dict, row_num=row_num)

                if errors:
                    row_errors.extend(errors)
                else:
                    valid_rows.append((idx, row_dict))

                # live progress update every 500 rows
                if idx % 500 == 0 and idx > 0:
                    job.valid_rows = len(valid_rows)
                    job.error_rows = len(row_errors)
                    job.save(update_fields=['valid_rows', 'error_rows'])

            # ── Phase 2: Insert into PosTransaction + PosTransactionLine ──
            with db_transaction.atomic():
                # Group valid rows by transaction_id
                transactions_map = {}
                for idx, row_dict in valid_rows:
                    txn_id = row_dict['transaction_id']
                    if txn_id not in transactions_map:
                        transactions_map[txn_id] = {
                            'store_id': row_dict['store_id'],
                            'cashier_id': row_dict['cashier_id'],
                            'date': row_dict['date'],
                            'lines': []
                        }
                    transactions_map[txn_id]['lines'].append(row_dict)

                # Create PosTransaction + PosTransactionLine records
                for txn_id, txn_data in transactions_map.items():
                    # Parse transaction datetime
                    date_str = txn_data['date']
                    try:
                        # Try parsing as date and convert to datetime
                        from datetime import datetime as dt
                        parsed_date = None
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                            try:
                                parsed_date = dt.strptime(date_str, fmt).replace(hour=0, minute=0, second=0)
                                break
                            except ValueError:
                                continue
                        if not parsed_date:
                            raise ValueError(f'Could not parse date: {date_str}')
                    except Exception as e:
                        row_errors.append({
                            'transaction_id': txn_id,
                            'field': 'date',
                            'error': f'Could not parse transaction date: {e}'
                        })
                        continue

                    # Create PosTransaction
                    try:
                        pos_txn = PosTransaction.objects.create(
                            posTransactionId=int(txn_id),
                            storeId_id=int(txn_data['store_id']),
                            cashierId_id=int(txn_data['cashier_id']),
                            transactionDatetime=parsed_date,
                        )
                    except Exception as e:
                        row_errors.append({
                            'transaction_id': txn_id,
                            'field': 'PosTransaction',
                            'error': f'Failed to create transaction: {e}'
                        })
                        continue

                    # Create PosTransactionLine records for this transaction
                    line_records = []
                    for line_idx, line_dict in enumerate(txn_data['lines'], 1):
                        try:
                            line_records.append(
                                PosTransactionLine(
                                    lineId=int(f"{txn_id}{line_idx:03d}"),  # Composite: txn_id + line#
                                    posTransactionId=pos_txn,
                                    productSKU_id=line_dict['product_sku'],
                                    quantity=int(line_dict['quantity']),
                                    unitPrice=line_dict['unit_price'],
                                    discountApplied=line_dict['discount_applied'],
                                    totalAmount=line_dict['total'],
                                )
                            )
                        except Exception as e:
                            row_errors.append({
                                'transaction_id': txn_id,
                                'field': 'PosTransactionLine',
                                'error': f'Failed to create line item: {e}'
                            })

                    # Bulk insert line items
                    if line_records:
                        try:
                            PosTransactionLine.objects.bulk_create(line_records, batch_size=1000)
                        except Exception as e:
                            row_errors.append({
                                'transaction_id': txn_id,
                                'field': 'bulk_insert',
                                'error': f'Bulk insert failed: {e}'
                            })

                # ── Mark job complete ────
                job.status = IngestionJob.STATUS_COMPLETED
                job.valid_rows = len(valid_rows)
                job.error_rows = len(row_errors)
                job.error_report = {'row_errors': row_errors} if row_errors else {}
                job.save()

            logger.info(
                f'POS job {job.id} done — '
                f'valid={len(valid_rows)}, errors={len(row_errors)}, '
                f'transactions={len(transactions_map)}'
            )

        except Exception as e:
            logger.exception(f'POS job {job.id} failed — {e}')
            job.status = IngestionJob.STATUS_FAILED
            job.error_report = {'fatal_error': str(e)}
            job.save(update_fields=['status', 'error_report'])
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