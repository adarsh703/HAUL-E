"""
sheets_logger.py — Google Sheets Activity Logger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Appends one row per broker outreach attempt to a Google Spreadsheet,
creating a live management dashboard for Mor Logistics.

Columns logged (in order):
  A  Timestamp (UTC)
  B  Broker Name
  C  Broker Email
  D  Lane
  E  Pickup Date
  F  Status          (SENT / SEND_FAILED / LOG_FAILED)
  G  Email Preview   (first 250 chars of the drafted email)

Setup requirements:
  1. Create a Google Cloud project and enable the Sheets API.
  2. Create a Service Account and download the JSON key.
  3. Share your Google Sheet with the service account email (Editor access).
  4. Set GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS_FILE in .env.

All blocking Google API calls run in asyncio.to_thread().
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
CREDENTIALS_FILE: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
TAB_NAME: str = os.getenv("SHEETS_TAB_NAME", "Outreach Log")
SCOPES: list[str] = ["https://www.googleapis.com/auth/spreadsheets"]

# Standard column headers — must match column order above
HEADERS: list[str] = [
    "Timestamp (UTC)",
    "Broker Name",
    "Broker Email",
    "Lane",
    "Pickup Date",
    "Status",
    "Email Preview",
]


# ── Auth & Service ────────────────────────────────────────────────────────────

def _get_sheets_service() -> Any:
    """
    Builds an authenticated Google Sheets API service client.

    Raises:
        FileNotFoundError: If the credentials JSON file is missing.
        google.auth.exceptions.GoogleAuthError: On auth failure.
    """
    if not os.path.isfile(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Google credentials file not found: '{CREDENTIALS_FILE}'.\n"
            "  1. Go to Google Cloud Console → IAM & Admin → Service Accounts.\n"
            "  2. Create a service account with Sheets API Editor access.\n"
            "  3. Download the JSON key and save it as 'google_credentials.json'.\n"
            "  4. Share your Google Sheet with the service account email."
        )
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


# ── Core Append (Blocking) ────────────────────────────────────────────────────

def _append_row(
    broker_name: str,
    broker_email: str,
    lane: str,
    date: str,
    status: str,
    email_preview: str,
) -> None:
    """
    Blocking function that appends a single row to the Google Sheet.
    Call only via asyncio.to_thread().

    Raises:
        EnvironmentError: GOOGLE_SHEETS_ID not configured.
        HttpError: Google Sheets API error.
        FileNotFoundError: Credentials file missing.
    """
    if not SPREADSHEET_ID:
        raise EnvironmentError(
            "GOOGLE_SHEETS_ID is not set in .env. "
            "Copy the Sheet ID from the spreadsheet URL."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    # Truncate preview to 250 chars to keep the sheet readable
    preview_truncated = email_preview[:250].strip().replace("\n", " ")

    row = [
        timestamp,
        broker_name,
        broker_email,
        lane,
        date,
        status,
        preview_truncated,
    ]

    service = _get_sheets_service()

    # Wrap tab name in single quotes to handle spaces (e.g. 'Outreach Log'!A1)
    safe_tab = f"'{TAB_NAME}'"
    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{safe_tab}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        )
        .execute()
    )

    rows_updated = result.get("updates", {}).get("updatedRows", 0)
    log.info(
        "📊 Sheets row appended | Broker: %s | Status: %s | Rows updated: %d",
        broker_email, status, rows_updated,
    )


# ── Header Bootstrap (Blocking) ───────────────────────────────────────────────

def _ensure_headers_sync() -> None:
    """
    Checks if the sheet tab has headers in row 1.
    If the sheet is empty, writes the standard HEADERS row.
    Safe to call on every bot startup (idempotent).
    """
    if not SPREADSHEET_ID:
        return

    service = _get_sheets_service()
    safe_tab = f"'{TAB_NAME}'"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range=f"{safe_tab}!A1:G1")
        .execute()
    )
    existing = result.get("values", [])

    if not existing:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{safe_tab}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [HEADERS]},
        ).execute()
        log.info("📊 Sheet headers written to tab '%s'", TAB_NAME)
    else:
        log.info("📊 Sheet headers already present in tab '%s'", TAB_NAME)


# ── Public Async Interface ────────────────────────────────────────────────────

async def append_outreach_log(
    broker_name: str,
    broker_email: str,
    lane: str,
    date: str,
    status: str,
    email_preview: str,
) -> None:
    """
    Async entry point — appends one outreach row to Google Sheets without
    blocking the Discord event loop.

    Args:
        broker_name:   Broker's display name.
        broker_email:  Broker's email address.
        lane:          Full lane string (e.g. "Laredo TX to Toronto ON").
        date:          Pickup date string.
        status:        Outcome code: "SENT", "SEND_FAILED", "PARSE_FAILED", etc.
        email_preview: First ~250 chars of the drafted email body.

    Raises:
        EnvironmentError: Missing spreadsheet ID.
        FileNotFoundError: Missing credentials file.
        HttpError: Google Sheets API error.
    """
    log.info(
        "Logging outreach | Broker: %s <%s> | Status: %s",
        broker_name, broker_email, status,
    )
    await asyncio.to_thread(
        _append_row, broker_name, broker_email, lane, date, status, email_preview
    )


async def ensure_headers() -> None:
    """
    Async wrapper for header bootstrapping.
    Call once in BrokerBot.setup_hook() to auto-create column headers
    if the sheet tab is brand new.
    """
    try:
        await asyncio.to_thread(_ensure_headers_sync)
    except Exception as exc:
        # Non-fatal — bot still runs even if headers can't be verified
        log.warning("Could not verify sheet headers: %s", exc)
