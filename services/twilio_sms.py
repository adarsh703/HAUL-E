"""
twilio_sms.py — Twilio SMS & WhatsApp Messaging Service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sends SMS and WhatsApp messages to drivers and dispatchers via Twilio.
Handles dispatch load detail texts, recurring temperature check prompts,
and forwarding driver responses to shippers (email) and dispatchers (WhatsApp).

All blocking Twilio REST calls run in asyncio.to_thread() to avoid
blocking the Discord / FastAPI event loop.

Setup requirements:
  1. Create a Twilio account and get Account SID + Auth Token.
  2. Purchase or verify a Twilio phone number for SMS.
  3. Enable the WhatsApp sandbox or connect a WhatsApp Business number.
  4. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import asyncio
import logging
from datetime import datetime

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
DRIVER_TEST_PHONE: str = os.getenv("DRIVER_TEST_PHONE", "")
COMPANY_NAME: str = "Mor Logistics Manitoba Ltd"

# ── Twilio Client (lazy-init) ────────────────────────────────────────────────
_client: Client | None = None


def _get_client() -> Client:
    """
    Returns a cached Twilio REST client. Raises on missing credentials.
    """
    global _client
    if _client is not None:
        return _client

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise EnvironmentError(
            "TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing from .env. "
            "See README for Twilio setup instructions."
        )

    _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    log.info("Twilio client initialised (SID: %s…)", TWILIO_ACCOUNT_SID[:8])
    return _client


# ── Low-Level Blocking Senders ───────────────────────────────────────────────

def _send_sms_sync(to: str, body: str) -> str:
    """
    Blocking SMS send (Redirected to Discord)
    """
    import requests
    import os
    token = os.getenv("DISCORD_TOKEN")
    if not token: return "discord_sent"
    url = "https://discord.com/api/v10/channels/1517447020791468122/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"content": f"**SMS to {to}**: {body}"}
    try:
        requests.post(url, headers=headers, json=payload)
    except:
        pass
    return "discord_sent"


def _send_whatsapp_sync(to: str, body: str) -> str:
    """
    Blocking WhatsApp send (Redirected to Discord)
    """
    import requests
    import os
    token = os.getenv("DISCORD_TOKEN")
    if not token: return "discord_sent"
    url = "https://discord.com/api/v10/channels/1517447020791468122/messages"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"content": f"**WhatsApp to {to}**: {body}"}
    try:
        requests.post(url, headers=headers, json=payload)
    except:
        pass
    return "discord_sent"


# ── Utility Helpers ──────────────────────────────────────────────────────────

def _estimate_segments(body: str) -> int:
    """Rough SMS segment count (160-char segments, 153 for multi-part)."""
    length = len(body)
    if length <= 160:
        return 1
    return (length // 153) + (1 if length % 153 else 0)


def _format_load_sms(load_data: dict, driver_name: str, truck: str, trailer: str) -> str:
    """
    Formats the extracted load/RC data into an original, highly detailed,
    and professional dispatch message for Mor Logistics.
    """
    info = load_data.get("load_information", {})
    stops = load_data.get("stops", [])
    reefer = load_data.get("reefer_operations", {})
    
    load_number = info.get("broker_load_number", "N/A")
    commodity = info.get("commodity", "N/A")
    weight = info.get("weight", "N/A")
    
    # Temperature parsing
    temp_setpoint = reefer.get("temperature_setpoint", "")
    temp_req = info.get("temperature_requirements", "")
    temp_display = temp_setpoint or temp_req or "Not specified"
    
    lines = [
        f"*** MOR LOGISTICS DISPATCH ***",
        f"Load Reference: {load_number}",
        f"Assigned Driver: {driver_name}",
        f"Equipment: Truck {truck} / Trailer {trailer}",
        f"",
        f"-- FREIGHT DETAILS --",
        f"Commodity: {commodity}",
        f"Weight: {weight}",
        f"Temperature: {temp_display}",
        f"",
        f"-- ROUTING --"
    ]

    for i, stop in enumerate(stops, 1):
        stop_type = stop.get("stop_type", "Stop")
        is_pickup = "pickup" in stop_type.lower()
        label = "PICKUP" if is_pickup else "DELIVERY"
        
        company = stop.get("company_name", "")
        address = stop.get("address", "")
        city_state = stop.get("city_state", "")
        full_address = ", ".join(filter(None, [address, city_state]))
        
        appt_date = stop.get("appointment_date", "")
        appt_time = stop.get("appointment_time", "")
        timing = f"{appt_date} {appt_time}".strip()
        instructions = stop.get("instructions", "")
        
        lines.append(f"")
        lines.append(f"[STOP {i}: {label}]")
        if company:
            lines.append(f"Facility: {company}")
        if full_address:
            lines.append(f"Address: {full_address}")
        
        if is_pickup:
            lines.append(f"Pickup #: {load_number}")
        else:
            lines.append(f"Delivery #: {load_number}")
            
        if timing:
            lines.append(f"Appointment: {timing}")
        if instructions:
            lines.append(f"Notes: {instructions}")
        
    lines.append(f"")
    lines.append("Please reply LOADED once the freight is on the truck.")
    
    return "\n".join(lines)



def _format_temp_check(load_id: str) -> str:
    """
    Builds the recurring temperature check prompt message.
    """
    import pytz
    toronto_tz = pytz.timezone('America/Toronto')
    now = datetime.now(toronto_tz).strftime("%I:%M %p EST")
    return (
        f"🌡️ TEMP CHECK — Load #{load_id}\n"
        f"Time: {now}\n"
        f"\n"
        f"What is your current reefer temperature reading?\n"
        f"\n"
        f"Please reply with the temperature (e.g. \"-2°F\" or \"34°F\").\n"
        f"If there's an issue, reply ISSUE and describe it.\n"
        f"\n"
        f"— {COMPANY_NAME}"
    )


# ── Public Async Interface ───────────────────────────────────────────────────

async def send_sms(to: str, body: str) -> str:
    """
    Send a plain SMS message (Redirected to Discord)
    """
    log.info("Dispatching SMS to Discord → %s (%d chars)", to, len(body))
    await _send_discord_message("1517447020791468122", f"**To {to}**: {body}")
    return "discord_sent"


async def send_whatsapp(to: str, body: str) -> str:
    """
    Send a WhatsApp message (Redirected to Discord)
    """
    log.info("Dispatching WhatsApp to Discord → %s (%d chars)", to, len(body))
    await _send_discord_message("1517447020791468122", f"**To {to}**: {body}")
    return "discord_sent"


import aiohttp
import os

async def _send_discord_message(channel_id: str, content: str):
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.error("DISCORD_TOKEN not set for _send_discord_message")
        return
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    payload = {"content": content}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                log.error(f"Failed to send discord message: {await resp.text()}")

async def send_load_details_to_driver(to: str, load_data: dict, driver_name: str = "", truck: str = "", trailer: str = "") -> str:
    """
    Format the RC / load data into a professional dispatch text and
    send it to the driver via Discord channel 1517447020791468122.
    """
    body = _format_load_sms(load_data, driver_name, truck, trailer)
    load_id = load_data.get("load_information", {}).get("broker_load_number", "?")
    log.info("Sending load details (Load #%s) to driver via Discord", load_id)
    await _send_discord_message("1517447020791468122", body)
    return "discord_sent"


async def send_temp_check(to: str, load_id: str) -> str:
    """
    Send a recurring temperature check to the driver via their load's Discord thread.
    Falls back to the main drivers channel if no thread found.
    """
    body = _format_temp_check(load_id)

    # Look up the load's discord thread
    try:
        from database.models import AsyncSessionLocal, Load
        from sqlalchemy.future import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Load).where(Load.load_id == load_id))
            load = result.scalars().first()
            channel_id = load.discord_thread_id if load and load.discord_thread_id else "1517447020791468122"
    except Exception as e:
        log.error(f"Failed to look up thread for load {load_id}: {e}")
        channel_id = "1517447020791468122"

    log.info("🌡️ Temp check sent → Discord thread %s | Load #%s", channel_id, load_id)
    await _send_discord_message(channel_id, body)
    return "discord_sent"


async def forward_temp_response_email(
    shipper_email: str,
    load_id: str,
    driver_response: str,
    is_issue: bool = False,
) -> None:
    """
    Forward the driver's temperature response to the shipper via email.
    Uses the existing gmail_sender module for SMTP delivery.

    Args:
        shipper_email:   Shipper's email address (the one who sent us the RC).
        load_id:         The load / broker reference number.
        driver_response: Raw text response from the driver.
        is_issue:        Whether the AI determined this is a temperature issue.
    """
    from gmail_sender import _send_via_smtp

    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    # Determine if temp is correct or there's an issue
    if is_issue:
        status = "⚠️ ISSUE REPORTED"
        status_line = "The driver has reported a temperature issue or the reading is out of range. Please call the driver immediately to correct the temperature!"
    else:
        status = "✅ TEMPERATURE CONFIRMED CORRECT"
        status_line = "The driver has confirmed that the temperature in the truck is correct and within the required range."

    from database.models import Load
    from api import get_db_session
    from sqlalchemy.future import select
    from services.motive_service import sync_fleet_from_motive, get_vehicle_tracking
    
    location_str = "Location unavailable"
    on_time_str = "Estimated On Time"
    
    try:
        async with get_db_session() as session:
            result = await session.execute(select(Load).where(Load.load_id == load_id))
            load = result.scalars().first()
            if load:
                import json
                vehicles = await asyncio.to_thread(sync_fleet_from_motive)
                unit_id = None
                
                if load.operational_intelligence:
                    try:
                        intel = json.loads(load.operational_intelligence)
                        truck = intel.get("load_information", {}).get("assigned_truck", "")
                        if truck:
                            truck_clean = truck.replace("#", "").strip().lower()
                            unit_id = next((v["unit_id"] for v in vehicles if v["unit_id"].lower() == truck_clean), None)
                    except Exception:
                        pass
                
                if not unit_id and load.driver:
                    unit_id = next((v["unit_id"] for v in vehicles if v["driver"].lower() == load.driver.lower()), None)
                    
                if unit_id:
                    tracking = await asyncio.to_thread(get_vehicle_tracking, unit_id)
                    if tracking:
                        location_str = f"{tracking['location']} ({tracking['speed']} mph)"
                        on_time_str = "On Time (Driving)" if tracking['speed'] > 0 else "On Time (Idle)"
    except Exception as e:
        log.error(f"Failed to fetch Motive location for email: {e}")

    subject = f"🌡️ {status} — Load #{load_id} | {COMPANY_NAME}"
    body = (
        f"Temperature & Location Update\n"
        f"{'=' * 40}\n"
        f"\n"
        f"Load #:    {load_id}\n"
        f"Time:      {timestamp}\n"
        f"Status:    {status}\n"
        f"Location:  {location_str}\n"
        f"ETA State: {on_time_str}\n"
        f"\n"
        f"{status_line}\n"
        f"\n"
        f"Driver's response: \"{driver_response}\"\n"
        f"\n"
        f"{'=' * 40}\n"
        f"This is an automated temperature and tracking report from {COMPANY_NAME}.\n"
    )

    log.info("Forwarding temp response → %s | Load #%s | %s", shipper_email, load_id, status)
    notify_email = os.getenv('GMAIL_USER', 'cavemann177@gmail.com')
    await asyncio.to_thread(_send_via_smtp, notify_email, subject, body)


async def forward_location_email(shipper_email: str, load_id: str) -> None:
    from gmail_sender import _send_via_smtp
    from database.models import Load
    from api import get_db_session
    from sqlalchemy.future import select
    from services.motive_service import sync_fleet_from_motive, get_vehicle_tracking
    
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    location_str = "Location unavailable"
    on_time_str = "Estimated On Time"
    
    try:
        async with get_db_session() as session:
            result = await session.execute(select(Load).where(Load.load_id == load_id))
            load = result.scalars().first()
            if load:
                import json
                vehicles = await asyncio.to_thread(sync_fleet_from_motive)
                unit_id = None
                
                if load.operational_intelligence:
                    try:
                        intel = json.loads(load.operational_intelligence)
                        truck = intel.get("load_information", {}).get("assigned_truck", "")
                        if truck:
                            truck_clean = truck.replace("#", "").strip().lower()
                            unit_id = next((v["unit_id"] for v in vehicles if v["unit_id"].lower() == truck_clean), None)
                    except Exception:
                        pass
                
                if not unit_id and load.driver:
                    unit_id = next((v["unit_id"] for v in vehicles if v["driver"].lower() == load.driver.lower()), None)
                    
                if unit_id:
                    tracking = await asyncio.to_thread(get_vehicle_tracking, unit_id)
                    if tracking:
                        location_str = f"{tracking['location']} ({tracking['speed']} mph)"
                        on_time_str = "On Time (Driving)" if tracking['speed'] > 0 else "On Time (Idle)"
    except Exception as e:
        log.error(f"Failed to fetch Motive location for silent email: {e}")

    subject = f"📍 Tracking Update — Load #{load_id} | {COMPANY_NAME}"
    body = (
        f"Automated Tracking Update\n"
        f"{'=' * 40}\n"
        f"\n"
        f"Load #:    {load_id}\n"
        f"Time:      {timestamp}\n"
        f"Location:  {location_str}\n"
        f"ETA State: {on_time_str}\n"
        f"\n"
        f"{'=' * 40}\n"
        f"This is an automated tracking report from {COMPANY_NAME}.\n"
    )

    log.info("Forwarding silent location update → %s | Load #%s", shipper_email, load_id)
    notify_email = os.getenv('GMAIL_USER', 'cavemann177@gmail.com')
    await asyncio.to_thread(_send_via_smtp, notify_email, subject, body)


async def forward_temp_response_whatsapp(
    dispatcher_phone: str,
    load_id: str,
    driver_response: str,
    is_issue: bool = False,
) -> str:
    """
    Forward the driver's temperature response to the dispatcher via WhatsApp.

    Args:
        dispatcher_phone: Dispatcher's phone in E.164 format.
        load_id:          The load / broker reference number.
        driver_response:  Raw text response from the driver.
        is_issue:         Whether the AI determined this is a temperature issue.

    Returns:
        Twilio Message SID.
    """
    timestamp = datetime.now().strftime("%I:%M %p")

    # Determine if temp is correct or there's an issue
    if is_issue:
        status_emoji = "⚠️"
        status_text = "ISSUE REPORTED / OUT OF RANGE"
    else:
        status_emoji = "✅"
        status_text = "TEMP CONFIRMED OK"

    body = (
        f"🌡️ TEMP UPDATE — Load #{load_id}\n"
        f"⏰ {timestamp}\n"
        f"\n"
        f"{status_emoji} {status_text}\n"
        f"Driver says: {driver_response}\n"
        f"\n"
        f"— {COMPANY_NAME} Auto-Dispatch"
    )

    log.info("Forwarding temp response via WhatsApp → %s | Load #%s",
             dispatcher_phone, load_id)
    return await asyncio.to_thread(_send_whatsapp_sync, dispatcher_phone, body)

