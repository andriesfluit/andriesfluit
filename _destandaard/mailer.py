"""SMTP send via Gmail app password, with retry on transient errors.
(Same approach as _mediamonitor/mailer.py.)"""

import logging
import os
import smtplib
import time
from email.message import EmailMessage

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 4
_BACKOFF_SECONDS = 15


def send(subject, html_body, text_body, to_addr):
    user = os.environ.get("GMAIL_USER", "andries.fluit@gmail.com")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not pw:
        raise RuntimeError("GMAIL_APP_PASSWORD not set")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
                s.login(user, pw)
                s.send_message(msg)
            return
        except (smtplib.SMTPResponseException, smtplib.SMTPServerDisconnected,
                OSError) as e:
            code = getattr(e, "smtp_code", None)
            transient = code is None or 400 <= code < 500
            if attempt < _MAX_ATTEMPTS and transient:
                wait = _BACKOFF_SECONDS * attempt
                logger.warning("SMTP send attempt %d/%d failed (%s); retrying in %ds",
                               attempt, _MAX_ATTEMPTS, e, wait)
                time.sleep(wait)
                continue
            raise
