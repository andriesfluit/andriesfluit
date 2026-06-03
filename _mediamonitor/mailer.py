"""SMTP send via Gmail app password, with retry on transient errors."""

import logging
import os
import smtplib
import time
from email.message import EmailMessage

logger = logging.getLogger(__name__)

# Gmail occasionally returns a transient 4xx (seen: 451 4.3.0 "Mail server
# temporarily rejected message") when two monitors send within minutes of each
# other from the same account, or when a message is large. These clear on a
# short retry, so back off and try again before failing the run.
_MAX_ATTEMPTS = 4
_BACKOFF_SECONDS = 15


def send(subject, html_body, text_body, to_addr):
    user = os.environ.get("GMAIL_USER", "andries.fluit@gmail.com")
    pw   = os.environ.get("GMAIL_APP_PASSWORD")
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
            # Retry only transient failures: 4xx SMTP codes, disconnects,
            # timeouts. Permanent errors (5xx, e.g. bad auth) raise immediately.
            code = getattr(e, "smtp_code", None)
            transient = code is None or 400 <= code < 500
            if attempt < _MAX_ATTEMPTS and transient:
                wait = _BACKOFF_SECONDS * attempt
                logger.warning("SMTP send attempt %d/%d failed (%s); retrying in %ds",
                               attempt, _MAX_ATTEMPTS, e, wait)
                time.sleep(wait)
                continue
            raise
