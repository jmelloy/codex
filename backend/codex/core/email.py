"""Outbound email delivery (SMTP / SES) for password resets and notification digests.

Environment variables:
    CODEX_EMAIL_BACKEND       – "" (default, disabled) | "smtp" | "ses"
    CODEX_EMAIL_FROM_ADDRESS  – "from" address used for all outbound mail
    CODEX_EMAIL_FROM_NAME     – "from" display name (default "Codex")
    CODEX_APP_BASE_URL        – base URL used to build links in emails (default "http://localhost:8065")

    # SMTP backend
    CODEX_SMTP_HOST           – SMTP server hostname
    CODEX_SMTP_PORT           – SMTP server port (default 587)
    CODEX_SMTP_USERNAME       – SMTP auth username
    CODEX_SMTP_PASSWORD       – SMTP auth password
    CODEX_SMTP_USE_TLS        – whether to use STARTTLS (default true)

    # SES backend — reuses AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY already read by core/s3_storage.py
    CODEX_SES_REGION          – AWS region for SES (default CODEX_S3_REGION's default, "us-east-1")

With `CODEX_EMAIL_BACKEND` unset/empty, `send_email` logs at debug level and
returns `False` immediately — every caller treats a failed/no-op send as
non-fatal, so features degrade gracefully with no email config.
"""

import asyncio
import logging
import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CODEX_EMAIL_BACKEND: str = os.getenv("CODEX_EMAIL_BACKEND", "").strip().lower()
CODEX_EMAIL_FROM_ADDRESS: str | None = os.getenv("CODEX_EMAIL_FROM_ADDRESS")
CODEX_EMAIL_FROM_NAME: str = os.getenv("CODEX_EMAIL_FROM_NAME", "Codex")
CODEX_APP_BASE_URL: str = os.getenv("CODEX_APP_BASE_URL", "http://localhost:8065")

# SMTP
CODEX_SMTP_HOST: str | None = os.getenv("CODEX_SMTP_HOST")
CODEX_SMTP_PORT: int = int(os.getenv("CODEX_SMTP_PORT", "587"))
CODEX_SMTP_USERNAME: str | None = os.getenv("CODEX_SMTP_USERNAME")
CODEX_SMTP_PASSWORD: str | None = os.getenv("CODEX_SMTP_PASSWORD")
CODEX_SMTP_USE_TLS: bool = os.getenv("CODEX_SMTP_USE_TLS", "true").lower() == "true"

# SES
CODEX_SES_REGION: str = os.getenv("CODEX_SES_REGION", os.getenv("CODEX_S3_REGION", "us-east-1"))


@dataclass
class EmailMessage:
    """A single outbound email, backend-agnostic."""

    to: str
    subject: str
    text_body: str
    html_body: str | None = None


def is_email_configured() -> bool:
    """Whether a usable email backend is configured."""
    return CODEX_EMAIL_BACKEND in ("smtp", "ses") and bool(CODEX_EMAIL_FROM_ADDRESS)


def _from_header() -> str:
    return f"{CODEX_EMAIL_FROM_NAME} <{CODEX_EMAIL_FROM_ADDRESS}>"


def _build_mime_message(message: EmailMessage) -> MIMEMultipart:
    mime_message = MIMEMultipart("alternative")
    mime_message["Subject"] = message.subject
    mime_message["From"] = _from_header()
    mime_message["To"] = message.to
    mime_message.attach(MIMEText(message.text_body, "plain"))
    if message.html_body:
        mime_message.attach(MIMEText(message.html_body, "html"))
    return mime_message


def _send_via_smtp(message: EmailMessage) -> None:
    mime_message = _build_mime_message(message)
    with smtplib.SMTP(CODEX_SMTP_HOST, CODEX_SMTP_PORT, timeout=10) as smtp:
        if CODEX_SMTP_USE_TLS:
            smtp.starttls()
        if CODEX_SMTP_USERNAME and CODEX_SMTP_PASSWORD:
            smtp.login(CODEX_SMTP_USERNAME, CODEX_SMTP_PASSWORD)
        smtp.sendmail(CODEX_EMAIL_FROM_ADDRESS, [message.to], mime_message.as_string())


def _send_via_ses(message: EmailMessage) -> None:
    client = boto3.client("ses", region_name=CODEX_SES_REGION)
    body: dict = {"Text": {"Data": message.text_body}}
    if message.html_body:
        body["Html"] = {"Data": message.html_body}
    client.send_email(
        Source=_from_header(),
        Destination={"ToAddresses": [message.to]},
        Message={"Subject": {"Data": message.subject}, "Body": body},
    )


async def send_email(message: EmailMessage) -> bool:
    """Send an email through the configured backend.

    Returns `True` on success, `False` otherwise (no config, or any backend
    exception) — never raises. Callers must treat a `False` return as
    non-fatal: a mail failure must never crash or block a request.
    """
    if not is_email_configured():
        logger.debug("Email backend not configured — skipping send to %s", message.to)
        return False

    try:
        if CODEX_EMAIL_BACKEND == "smtp":
            await asyncio.to_thread(_send_via_smtp, message)
        elif CODEX_EMAIL_BACKEND == "ses":
            await asyncio.to_thread(_send_via_ses, message)
        else:
            logger.error("Unknown CODEX_EMAIL_BACKEND %r", CODEX_EMAIL_BACKEND)
            return False
    except (smtplib.SMTPException, OSError, BotoCoreError, ClientError):
        logger.error("Failed to send email to %s via %s", message.to, CODEX_EMAIL_BACKEND, exc_info=True)
        return False

    return True


def render_password_reset_email(username: str, reset_url: str) -> EmailMessage:
    """Build the password-reset email for a user."""
    text_body = (
        f"Hi {username},\n\n"
        "We received a request to reset your Codex password. Use the link below to choose a new one:\n\n"
        f"{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email — your password won't be changed.\n"
    )
    html_body = (
        f"<p>Hi {username},</p>"
        "<p>We received a request to reset your Codex password. "
        f'Use the link below to choose a new one:</p><p><a href="{reset_url}">{reset_url}</a></p>'
        "<p>If you didn't request this, you can safely ignore this email — your password won't be changed.</p>"
    )
    return EmailMessage(to="", subject="Reset your Codex password", text_body=text_body, html_body=html_body)
