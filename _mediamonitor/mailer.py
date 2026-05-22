"""SMTP send via Gmail app password."""

import os
import smtplib
from email.message import EmailMessage


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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)
