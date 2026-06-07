"""
claude_ai.py — Google Gemini AI Integration (via Vertex AI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Drop-in replacement for the previous Anthropic integration.
Identical public function signatures — main.py and skills/ require NO changes.

Backend:  Google Vertex AI  (project: haul-e-498411)
Model:    gemini-2.5-flash  (configurable via GEMINI_MODEL in .env)
Auth:     Reuses google_credentials.json (same service account as Sheets)
          Falls back to Application Default Credentials (ADC) if file absent.

Public API (unchanged):
    parse_and_draft_email(broker_email, broker_name, lane, date, notes="")
        → dict[broker_name, broker_email, lane, date, email_body]

    parse_attachment_and_draft(file_bytes, media_type, notes="")
        → dict[broker_name, broker_email, lane, date, email_body]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import logging
from typing import Any

from google import genai
from google.genai import types
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
GOOGLE_PROJECT_ID: str = os.getenv("GOOGLE_PROJECT_ID", "haul-e-498411")
GOOGLE_LOCATION: str   = os.getenv("GOOGLE_LOCATION", "us-central1")
CREDENTIALS_FILE: str  = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
GEMINI_MODEL: str      = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Vertex AI requires the cloud-platform scope
_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# Module-level lazy client (initialised once on first use)
_client: genai.Client | None = None


# ── Auth & Client ─────────────────────────────────────────────────────────────

def _build_client() -> genai.Client:
    """
    Builds an authenticated Vertex AI GenAI client.

    Auth priority:
      1. Service account JSON file (GOOGLE_SHEETS_CREDENTIALS_FILE in .env)
         — same file used by sheets_logger.py, zero extra setup required.
      2. Application Default Credentials (ADC) — fallback for Cloud Run /
         GCE environments where a metadata server is available.

    Raises:
        google.auth.exceptions.GoogleAuthError: On auth failure.
    """
    if os.path.isfile(CREDENTIALS_FILE):
        log.info("Gemini auth: service account file '%s'", CREDENTIALS_FILE)
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=_VERTEX_SCOPES,
        )
        return genai.Client(
            vertexai=True,
            project=GOOGLE_PROJECT_ID,
            location=GOOGLE_LOCATION,
            credentials=creds,
        )

    log.warning(
        "Credentials file '%s' not found — falling back to ADC. "
        "Ensure 'Vertex AI User' role is granted to the default service account.",
        CREDENTIALS_FILE,
    )
    return genai.Client(
        vertexai=True,
        project=GOOGLE_PROJECT_ID,
        location=GOOGLE_LOCATION,
    )


def _get_client() -> genai.Client:
    """Returns the module-level singleton GenAI client, initialising it on first call."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


# ── System Prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are the AI communications assistant for Mor Logistics Manitoba Ltd, a professional
Canadian trucking and cross-border freight company.

Company Profile:
  - Company:       Mor Logistics Manitoba Ltd
  - MC Number:     MC #1420840
  - Sales Email:   sales@morlogistics.ca
  - Sales Rep:     Ghani
  - Speciality:    Canada-US cross-border freight, DAT load board lanes

Your task is to draft highly professional, warm, and personalized freight broker
outreach emails. Follow these rules strictly:

1. Address the broker by their first name only.
2. Reference the exact lane (origin → destination) and the specific pickup date.
3. Emphasize Mor Logistics' reliability, on-time delivery, and professionalism.
4. Use Canadian business English (e.g. "travelling" not "traveling").
5. Keep the email concise — under 160 words unless special instructions say otherwise.
6. Close with the full Ghani / Mor Logistics signature block.
7. Do NOT include a Subject line in the body — return the email body text only.
8. Make each email feel specific and genuine, not boilerplate copy-paste.
9. Never hallucinate broker details. Use only what is provided.
10. If compliance or Canadian freight regulations are relevant to the lane, you may
    briefly mention adherence to FMCSA / Transport Canada standards.
""".strip()


# ── Text-Based Draft ──────────────────────────────────────────────────────────

async def parse_and_draft_email(
    broker_email: str,
    broker_name: str,
    lane: str,
    date: str,
    notes: str = "",
) -> dict[str, Any]:
    """
    Calls Gemini via Vertex AI to draft a personalized broker outreach email.

    Args:
        broker_email:  Recipient's email address.
        broker_name:   Broker's first name for personalization.
        lane:          Full lane string (e.g. "Laredo TX to Toronto ON").
        date:          Pickup / availability date (e.g. "June 3").
        notes:         Optional additional instructions or context.

    Returns:
        dict:
            broker_name  (str)
            broker_email (str)
            lane         (str)
            date         (str)
            email_body   (str)  ← ready-to-send email body

    Raises:
        EnvironmentError: If project/location config is missing.
        google.api_core.exceptions.GoogleAPIError: On API-level failures.
        ValueError: If the model returns an empty response.
    """
    if not GOOGLE_PROJECT_ID:
        raise EnvironmentError(
            "GOOGLE_PROJECT_ID is not set in .env. "
            "Add: GOOGLE_PROJECT_ID=haul-e-498411"
        )

    user_prompt = f"""
Draft a professional freight broker outreach email using the details below.

Broker Name:      {broker_name}
Broker Email:     {broker_email}
Lane:             {lane}
Pickup Date:      {date}
Additional Notes: {notes.strip() if notes else "None"}

Instructions:
- Write only the email body (no Subject line).
- Address the broker as '{broker_name}'.
- Sign off as Ghani, Mor Logistics Manitoba Ltd, MC #1420840, sales@morlogistics.ca.
""".strip()

    log.info(
        "Gemini draft requested | Broker: %s <%s> | Lane: %s | Date: %s | Model: %s",
        broker_name, broker_email, lane, date, GEMINI_MODEL,
    )

    client = _get_client()
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=1024,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(
                thinking_budget=512,   # light reasoning — fast turnaround
            ),
        ),
        contents=user_prompt,
    )

    email_body: str = (response.text or "").strip()
    if not email_body:
        raise ValueError(
            "Gemini returned an empty response. "
            "Check that the Vertex AI API is enabled on project haul-e-498411 "
            "and the service account has the 'Vertex AI User' role."
        )

    log.info("Gemini draft complete — %d characters", len(email_body))

    return {
        "broker_name":  broker_name,
        "broker_email": broker_email,
        "lane":         lane,
        "date":         date,
        "email_body":   email_body,
    }


# ── Vision-Based Draft (DAT Screenshots / Images) ────────────────────────────

async def parse_attachment_and_draft(
    file_bytes: bytes,
    media_type: str,
    notes: str = "",
) -> dict[str, Any]:
    """
    Uses Gemini's multimodal capability to parse a DAT load board screenshot,
    extract logistics data, and draft a broker outreach email.

    Supported media types:
        "image/png", "image/jpeg", "image/webp", "image/gif"

    Args:
        file_bytes:  Raw bytes of the image file.
        media_type:  MIME type string (e.g. "image/png").
        notes:       Optional extra instructions from the user.

    Returns:
        dict:
            broker_name  (str)
            broker_email (str)
            lane         (str)
            date         (str)
            email_body   (str)

    Raises:
        google.api_core.exceptions.GoogleAPIError: On API-level failures.
        ValueError: If required fields cannot be extracted or response is empty.
    """
    if not GOOGLE_PROJECT_ID:
        raise EnvironmentError("GOOGLE_PROJECT_ID is not set in .env.")

    text_prompt = f"""
This is a DAT load board screenshot or logistics document image.

Step 1 — Extract the following fields exactly as shown in the image:
  BROKER_NAME:  <broker first name>
  BROKER_EMAIL: <broker email address>
  LANE:         <origin city/state> to <destination city/state>
  DATE:         <pickup or availability date>

Step 2 — Using those extracted fields, draft a professional broker outreach email
on behalf of Mor Logistics Manitoba Ltd.

Return your full response in EXACTLY this format (no deviations):

BROKER_NAME: <value>
BROKER_EMAIL: <value>
LANE: <value>
DATE: <value>
---EMAIL---
<full email body here>

Additional user notes: {notes.strip() if notes else "None"}
""".strip()

    log.info(
        "Gemini vision parse requested | Media: %s | Size: %d bytes | Model: %s",
        media_type, len(file_bytes), GEMINI_MODEL,
    )

    client = _get_client()
    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=2048,
            temperature=0.4,          # lower temp for structured extraction
            thinking_config=types.ThinkingConfig(
                thinking_budget=1024,  # more budget for image understanding
            ),
        ),
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=media_type),
            types.Part.from_text(text=text_prompt),
        ],
    )

    raw: str = (response.text or "").strip()
    if not raw:
        raise ValueError(
            "Gemini vision returned an empty response. "
            "Ensure the Vertex AI API is enabled and the image is a supported format."
        )

    log.info("Gemini vision response received — %d characters", len(raw))

    # ── Parse structured response ─────────────────────────────────────────────
    fields: dict[str, str] = {}
    email_lines: list[str] = []
    in_email_section = False

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped == "---EMAIL---":
            in_email_section = True
            continue
        if in_email_section:
            email_lines.append(line)
        else:
            for key in ("BROKER_NAME", "BROKER_EMAIL", "LANE", "DATE"):
                if stripped.upper().startswith(f"{key}:"):
                    fields[key] = stripped.split(":", 1)[1].strip()
                    break

    email_body = "\n".join(email_lines).strip()

    if not fields.get("BROKER_EMAIL"):
        raise ValueError(
            "Could not extract BROKER_EMAIL from the attachment. "
            "Ensure the image clearly shows the broker's email address, "
            "or use /sendmail with manual input instead."
        )
    if not email_body:
        raise ValueError("Gemini vision returned an empty email body.")

    log.info(
        "Attachment parsed | Broker: %s <%s> | Lane: %s",
        fields.get("BROKER_NAME", "?"),
        fields.get("BROKER_EMAIL", "?"),
        fields.get("LANE", "?"),
    )

    return {
        "broker_name":  fields.get("BROKER_NAME", "Broker"),
        "broker_email": fields.get("BROKER_EMAIL", ""),
        "lane":         fields.get("LANE", "N/A"),
        "date":         fields.get("DATE", "N/A"),
        "email_body":   email_body,
    }
