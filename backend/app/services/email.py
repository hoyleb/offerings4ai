from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(recipient: str, subject: str, text_body: str) -> None:
    """Purpose: Deliver an outbound transactional email.

    Args:
        recipient: Destination email address.
        subject: Email subject line.
        text_body: Plain-text body content.

    Returns:
        None.

    Raises:
        HTTPException: When SMTP delivery is selected but required settings are missing
            or the message cannot be sent.
    """

    settings = get_settings()
    mode = settings.email_delivery_mode.lower().strip()

    if mode == "log":
        logger.info(
            "Verification email queued in log mode",
            extra={"recipient": recipient, "subject": subject, "body": text_body},
        )
        return

    if mode != "smtp":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unsupported email delivery mode. Configure EMAIL_DELIVERY_MODE as "
                "'log' or 'smtp'."
            ),
        )

    if not settings.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMTP_HOST must be configured before verification emails can be sent",
        )

    message = EmailMessage()
    message["From"] = settings.email_from_address
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                _login_and_send(server, message)
            return

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls()
                server.ehlo()
            _login_and_send(server, message)
    except OSError as exc:
        logger.exception("SMTP delivery failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send verification email right now",
        ) from exc


def _login_and_send(server: smtplib.SMTP, message: EmailMessage) -> None:
    settings = get_settings()
    if settings.smtp_username:
        server.login(settings.smtp_username, settings.smtp_password or "")
    server.send_message(message)
