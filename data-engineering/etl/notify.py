"""Quality and anomaly report notifier for the InsightFlow ETL pipeline.

Uses Python stdlib only (smtplib, email.mime) — no extra packages needed.

SMTP configuration via environment variables
--------------------------------------------
  SMTP_HOST        SMTP server hostname         (default: smtp.gmail.com)
  SMTP_PORT        SMTP server port             (default: 587, STARTTLS)
  SMTP_USER        Sender e-mail address        (required to send)
  SMTP_PASSWORD    Sender password / app-token  (required to send)
  REPORT_EMAIL_TO  Recipient address  (default: okeke.makuochukwu@amalitech.com)

Behaviour
---------
* The Markdown report is **always** written to disk at
  ``<lineage_dir>/quality_report_<run_id>.md``.
* Email is sent only when ``SMTP_USER`` is set in the environment.
  If it is not set, a single WARNING is logged and the function returns
  without raising — the pipeline continues normally.
* Delivery failures are logged as ERRORS but never abort the pipeline.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

log = logging.getLogger("insightflow.notify")

_DEFAULT_RECIPIENT = "okeke.makuochukwu@amalitech.com"
_THRESHOLD_WARN = 0.99  # score below this triggers a WARNING badge


# ---------------------------------------------------------------------------
# Markdown report builder
# ---------------------------------------------------------------------------


def _health_badge(quality_reports: list[dict[str, Any]]) -> str:
    """Return CRITICAL / WARNING / OK based on the worst per-source score."""
    if any(r.get("is_critical") for r in quality_reports):
        return "CRITICAL"
    if any(r.get("overall_score", 1.0) < _THRESHOLD_WARN for r in quality_reports):
        return "WARNING"
    return "OK"


def _score_bar(score: float, width: int = 20) -> str:
    """Return a simple ASCII progress bar, e.g. ``[████░░░░░░]  80.00%``."""
    filled = round(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]  {score * 100:.2f}%"


def build_quality_markdown(
    run_id: str,
    finished_at: str,
    quality_reports: list[dict[str, Any]],
    lineage_report: dict[str, Any],
) -> str:
    """Build the full Markdown quality/anomaly report string.

    Parameters
    ----------
    run_id:
        UUID of the pipeline run.
    finished_at:
        UTC ISO timestamp of pipeline completion.
    quality_reports:
        List of ``SourceQualityReport.to_dict()`` dicts, one per source.
    lineage_report:
        ``LineageTracker.to_report()`` dict.
    """
    badge = _health_badge(quality_reports)
    badge_icon = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(badge, "❓")

    lines: list[str] = [
        "# InsightFlow ETL — Data Quality & Anomaly Report",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Run ID** | `{run_id}` |",
        f"| **Completed** | {finished_at} |",
        f"| **Overall health** | {badge_icon} **{badge}** |",
        f"| **Sources checked** | {len(quality_reports)} |",
        "",
        "---",
        "",
    ]

    # ------------------------------------------------------------------
    # 1. Quality scores summary table
    # ------------------------------------------------------------------
    lines += [
        "## 1. Data Quality Scores",
        "",
        "| Source | Total Rows | Passed | Failed | Score | Status |",
        "|--------|-----------|--------|--------|-------|--------|",
    ]
    for r in quality_reports:
        src = r["source"]
        total = r["total_rows"]
        passed = r["passed_rows"]
        failed = r["failed_rows"]
        score = r["overall_score"]
        icon = (
            "🚨"
            if r.get("is_critical")
            else ("⚠️" if score < _THRESHOLD_WARN else "✅")
        )
        lines.append(
            f"| {src} | {total:,} | {passed:,} | {failed:,} "
            f"| {score * 100:.2f}% | {icon} |"
        )
    lines += [""]

    # ------------------------------------------------------------------
    # 2. Per-rule breakdown
    # ------------------------------------------------------------------
    lines += ["## 2. Rule-Level Pass Rates", ""]
    for r in quality_reports:
        src = r["source"]
        rule_scores: dict[str, float] = r.get("rule_scores", {})
        if not rule_scores:
            continue
        lines += [f"### {src}", ""]
        lines += ["| Rule | Pass Rate | Bar |", "|------|-----------|-----|"]
        for rule, rate in rule_scores.items():
            icon = "✅" if rate >= 1.0 else ("⚠️" if rate >= 0.95 else "🚨")
            lines.append(
                f"| `{rule}` | {rate * 100:.2f}% | {_score_bar(rate, 10)} {icon} |"
            )
        lines += [""]

    # ------------------------------------------------------------------
    # 3. Anomalies (rule failures)
    # ------------------------------------------------------------------
    total_anomalies = sum(r.get("anomaly_count", 0) for r in quality_reports)
    lines += [f"## 3. Rule-Failure Anomalies  ({total_anomalies} total)", ""]

    any_anomaly = False
    for r in quality_reports:
        src = r["source"]
        count = r.get("anomaly_count", 0)
        if count == 0:
            continue
        any_anomaly = True
        lines += [f"### {src} — {count} row(s) failed", ""]
        # Summarise which rules caused failures from rule_scores
        failing_rules = [
            rule for rule, rate in r.get("rule_scores", {}).items() if rate < 1.0
        ]
        if failing_rules:
            lines += ["**Rules with failures:**", ""]
            for rule in failing_rules:
                rate = r["rule_scores"][rule]
                failed_rows = round((1 - rate) * r["total_rows"])
                pct = (1 - rate) * 100
                lines.append(f"- `{rule}`: **{failed_rows}** rows failed ({pct:.2f}%)")
        lines += [""]

    if not any_anomaly:
        lines += ["_No rule-failure anomalies detected across all sources._", ""]

    # ------------------------------------------------------------------
    # 4. Statistical outliers
    # ------------------------------------------------------------------
    total_outlier_cols = sum(len(r.get("outlier_columns", {})) for r in quality_reports)
    lines += [
        f"## 4. Statistical Outliers (IQR method)  "
        f"({total_outlier_cols} column(s) flagged)",
        "",
    ]

    any_outlier = False
    for r in quality_reports:
        src = r["source"]
        outlier_cols: dict[str, int] = r.get("outlier_columns", {})
        if not outlier_cols:
            continue
        any_outlier = True
        lines += [f"### {src}", ""]
        lines += ["| Column | Outlier Rows |", "|--------|-------------|"]
        for col, cnt in outlier_cols.items():
            lines.append(f"| `{col}` | {cnt} |")
        lines += [""]

    if not any_outlier:
        lines += ["_No statistical outliers detected in any source._", ""]

    # ------------------------------------------------------------------
    # 5. Lineage journey
    # ------------------------------------------------------------------
    lines += ["## 5. Data Lineage Journey", ""]
    sources: dict[str, list[dict]] = lineage_report.get("sources", {})
    if not sources:
        lines += ["_No lineage events recorded._", ""]
    else:
        for src, events in sources.items():
            lines += [f"### {src}", ""]
            lines += [
                "| Stage | From | To | Extracted | Loaded | Filtered | Quality |",
                "|-------|------|----|-----------|--------|----------|---------|",
            ]
            for ev in events:
                stage = ev.get("stage", "—")
                src_tbl = ev.get("source_table", "—")
                tgt_tbl = ev.get("target_table", "—")
                extracted = ev.get("rows_extracted", 0)
                loaded = ev.get("rows_loaded", 0)
                filtered = ev.get("rows_filtered", 0)
                q = ev.get("quality_score", 1.0)
                q_icon = "✅" if q >= 0.99 else ("⚠️" if q >= 0.95 else "🚨")
                lines.append(
                    f"| `{stage}` | `{src_tbl}` | `{tgt_tbl}` "
                    f"| {extracted:,} | {loaded:,} | {filtered:,} "
                    f"| {q * 100:.1f}% {q_icon} |"
                )
            lines += [""]

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    lines += [
        "---",
        "",
        f"_Generated by InsightFlow ETL · run `{run_id}` · {finished_at}_",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Disk persistence
# ---------------------------------------------------------------------------


def save_markdown_report(
    content: str,
    output_dir: Path,
    run_id: str,
) -> Path:
    """Write the Markdown report to ``<output_dir>/quality_report_<run_id>.md``.

    The directory is created if it does not exist.

    Returns
    -------
    Path
        Path of the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"quality_report_{run_id}.md"
    out_path.write_text(content, encoding="utf-8")
    log.info("Quality report saved: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# SMTP delivery
# ---------------------------------------------------------------------------


def _send_email(
    *,
    to: str,
    subject: str,
    body: str,
    attachment_name: str,
    attachment_content: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
) -> None:
    """Send *attachment_content* as a .md file attachment.

    Port 465  → implicit SSL  (``smtplib.SMTP_SSL``).
    Other ports → STARTTLS upgrade (``smtplib.SMTP`` + ``starttls()``).

    Parameters
    ----------
    smtp_user:
        SMTP authentication username (may be an API key).
    smtp_from:
        Envelope + header ``From`` address — must be a valid e-mail.
        Defaults to *smtp_user* when not separately configured, which works
        for standard SMTP but not for API-key-based providers such as
        TurboSMTP — set ``SMTP_FROM`` in the environment for those.

    Raises
    ------
    Exception
        Any SMTP or network error (caller should catch and log).
    """
    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = to
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    part = MIMEApplication(attachment_content.encode("utf-8"), Name=attachment_name)
    part["Content-Disposition"] = f'attachment; filename="{attachment_name}"'
    msg.attach(part)

    context = ssl.create_default_context()

    # send_message() handles charset/encoding automatically — avoids
    # UnicodeEncodeError when the body or attachment contains non-ASCII chars.
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg, smtp_from, [to])
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.send_message(msg, smtp_from, [to])

    log.info("Quality report emailed to %s", to)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def send_pipeline_report(
    run_id: str,
    quality_reports: list[dict[str, Any]],
    lineage_report: dict[str, Any],
    output_dir: Path,
) -> None:
    """Build the quality/anomaly report, save it, and optionally email it.

    Always writes ``quality_report_<run_id>.md`` to *output_dir*.

    Email is sent when ``SMTP_USER`` is present in the environment.  If it
    is absent, a WARNING is logged and the function returns without error.
    Delivery failures are caught and logged as errors — they never abort
    the pipeline.

    Parameters
    ----------
    run_id:
        UUID of the pipeline run.
    quality_reports:
        List of ``SourceQualityReport.to_dict()`` dicts.
    lineage_report:
        ``LineageTracker.to_report()`` dict.
    output_dir:
        Directory where the .md file is saved (same as lineage output dir).
    """
    finished_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    md_content = build_quality_markdown(
        run_id=run_id,
        finished_at=finished_at,
        quality_reports=quality_reports,
        lineage_report=lineage_report,
    )

    report_path = save_markdown_report(md_content, output_dir, run_id)

    # ------------------------------------------------------------------
    # Email delivery
    # ------------------------------------------------------------------
    smtp_user = os.getenv("SMTP_USER", "")
    if not smtp_user:
        log.warning(
            "SMTP_USER not set — quality report saved to %s but NOT emailed.",
            report_path,
        )
        return

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    recipient = os.getenv("REPORT_EMAIL_TO", _DEFAULT_RECIPIENT)
    # SMTP_FROM is the visible sender address (may differ from the auth user,
    # e.g. when SMTP_USER is a TurboSMTP API key rather than an email address).
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    badge = _health_badge(quality_reports)
    subject = f"[InsightFlow ETL] Quality Report — {finished_at[:10]} — {badge}"

    body_lines = [
        f"InsightFlow ETL pipeline completed at {finished_at}.",
        f"Run ID: {run_id}",
        f"Overall health: {badge}",
        "",
        "The full quality and anomaly report is attached as a Markdown file.",
        "Open it in any Markdown viewer, GitHub, or VS Code for formatted output.",
        "",
    ]
    for r in quality_reports:
        icon = "CRITICAL" if r.get("is_critical") else "OK"
        body_lines.append(
            f"  {r['source']:<25} score={r['overall_score'] * 100:.2f}%  "
            f"failed={r['failed_rows']}  [{icon}]"
        )

    attachment_name = f"quality_report_{run_id}.md"

    try:
        _send_email(
            to=recipient,
            subject=subject,
            body="\n".join(body_lines),
            attachment_name=attachment_name,
            attachment_content=md_content,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_from=smtp_from,
        )
    except Exception as exc:  # noqa: BLE001
        log.error(
            "Failed to send quality report email to %s: %s. "
            "Report saved locally at %s.",
            recipient,
            exc,
            report_path,
        )
