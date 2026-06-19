"""
gmail_sender.py — Gmail SMTP Email Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sends professional broker outreach emails via Gmail SMTP (TLS).
Uses an App Password for authentication — no OAuth2 browser flow needed.

Setup requirements:
  1. Enable 2FA on the Gmail/Google Workspace account.
  2. Go to Google Account → Security → App Passwords.
  3. Generate a 16-character App Password for "Mail".
  4. Set GMAIL_USER and GMAIL_APP_PASSWORD in .env.

All blocking SMTP operations run in asyncio.to_thread() to avoid
blocking the Discord event loop.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
GMAIL_USER: str = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
SMTP_HOST: str = "smtp.gmail.com"
SMTP_PORT: int = 587           # TLS (STARTTLS)
COMPANY_NAME: str = "Mor Logistics Manitoba Ltd"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_subject(lane: str) -> str:
    """Generates a professional, lane-specific email subject line."""
    return f"Equipment Available | {lane} | {COMPANY_NAME}"


def _build_html_body(plain_text: str) -> str:
    """Wraps plain text in minimal, professional HTML for better email client rendering."""
    escaped = plain_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paragraphs = "".join(
        f"<p style='margin:0 0 12px 0;'>{line}</p>" if line.strip() else "<br>"
        for line in escaped.splitlines()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;
             color:#222222;line-height:1.6;max-width:640px;margin:0 auto;
             padding:24px;">
  {paragraphs}
</body>
</html>"""


# ── Core SMTP Send (Blocking) ──────────────────────────────────────────────────

def _send_via_smtp(to: str, subject: str, plain_body: str) -> None:
    """
    Blocking SMTP send — call only via asyncio.to_thread().

    Args:
        to:          Recipient email address.
        subject:     Email subject line.
        plain_body:  Plain-text email body (Claude AI output).

    Raises:
        EnvironmentError: If Gmail credentials are not configured.
        smtplib.SMTPException: On any SMTP protocol/auth failure.
        OSError: On network connectivity issues.
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise EnvironmentError(
            "GMAIL_USER or GMAIL_APP_PASSWORD is missing from .env. "
            "See README for App Password setup instructions."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{COMPANY_NAME} <{GMAIL_USER}>"
    msg["To"] = to
    msg["Cc"] = GMAIL_USER
    msg["Reply-To"] = GMAIL_USER

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(_build_html_body(plain_body), "html", "utf-8"))

    log.info("SMTP connecting → %s:%d as %s", SMTP_HOST, SMTP_PORT, GMAIL_USER)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [to, GMAIL_USER], msg.as_string())

    log.info("✉️  Email delivered → %s | Subject: %s", to, subject)


# ── Public Async Interface ────────────────────────────────────────────────────

async def send_broker_email(
    to: str,
    broker_name: str,
    lane: str,
    body: str,
) -> None:
    """
    Async entry point — sends the broker outreach email without blocking
    the Discord event loop.

    Args:
        to:          Broker's email address (e.g. surinder@amodispatch.ca).
        broker_name: Broker's name (used for logging only; body is pre-written).
        lane:        Lane string used to generate the subject line.
        body:        Full pre-drafted email body from Claude AI.

    Raises:
        EnvironmentError: Missing Gmail credentials.
        smtplib.SMTPAuthenticationError: Wrong App Password.
        smtplib.SMTPRecipientsRefused: Invalid recipient address.
        Exception: Any other SMTP or network error — propagates to caller.
    """
    subject = _build_subject(lane)
    log.info("Dispatching email | To: %s (%s) | Lane: %s", broker_name, to, lane)
    await asyncio.to_thread(_send_via_smtp, to, subject, body)

def _send_invoice_via_smtp(to: str, subject: str, plain_body: str, pdf_path: str, bol_path: str = None) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise EnvironmentError("GMAIL_USER or GMAIL_APP_PASSWORD is missing from .env.")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{COMPANY_NAME} <{GMAIL_USER}>"
    msg["To"] = to
    msg["Cc"] = GMAIL_USER
    msg["Reply-To"] = GMAIL_USER

    # Attach text body
    text_part = MIMEMultipart("alternative")
    text_part.attach(MIMEText(plain_body, "plain", "utf-8"))
    text_part.attach(MIMEText(_build_html_body(plain_body), "html", "utf-8"))
    msg.attach(text_part)

    # Attach PDF Invoice
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(pdf_attachment)

    # Attach BOL Image
    if bol_path and os.path.exists(bol_path):
        with open(bol_path, "rb") as f:
            from email.mime.image import MIMEImage
            bol_attachment = MIMEImage(f.read())
            bol_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(bol_path))
            msg.attach(bol_attachment)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [to, GMAIL_USER], msg.as_string())

async def send_invoice_email(to: str, load_id: str, pdf_path: str, bol_path: str = None) -> None:
    subject = f"Invoice & BOL for Load {load_id} | {COMPANY_NAME}"
    body = f"Hello,\n\nPlease find attached the Invoice and Proof of Delivery (BOL) for Load {load_id}.\nLet us know if you need any further information.\n\nThank you,\n{COMPANY_NAME}"
    await asyncio.to_thread(_send_invoice_via_smtp, to, subject, body, pdf_path, bol_path)
