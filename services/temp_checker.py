"""
temp_checker.py — Discord-native Temperature Check-In Service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Manages recurring temperature check messages to drivers for active reefer loads.
Uses a simple in-memory tracker + discord bot loop instead of APScheduler to
avoid event loop issues.

Public API:
  start_temp_checks(load_id, driver_phone, interval_minutes=180)
  stop_temp_checks(load_id)
  get_active_checks()
  init_temp_checker(bot) — call once at bot startup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import asyncio
import discord
from discord.ext import tasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

log = logging.getLogger("broker_bot.temp_checker")

# ── In-Memory Active Checks ──────────────────────────────────────────────────
# { load_id: { "driver_phone": str, "interval_minutes": int, "last_sent": datetime, "next_send": datetime } }
_active_checks: Dict[str, Dict[str, Any]] = {}
_bot = None  # Set via init_temp_checker


def init_temp_checker(bot):
    """Call this once at bot startup to give the temp checker access to the bot."""
    global _bot
    _bot = bot
    _start_loop()
    log.info("✅ Temp checker initialized")


def _start_loop():
    """Start the background loop that checks every minute."""
    if not _temp_loop.is_running():
        _temp_loop.start()


@tasks.loop(minutes=1)
async def _temp_loop():
    """Runs every minute, checks if any temp checks are due."""
    if not _active_checks:
        return

    now = datetime.now(timezone.utc)
    
    for load_id, info in list(_active_checks.items()):
        # Check if due for a new message
        if now >= info["next_send"]:
            await _send_temp_check(load_id, info["driver_phone"])
            info["last_sent"] = now
            info["next_send"] = now + timedelta(minutes=info["interval_minutes"])
            info["awaiting_response"] = True
            info["last_check_sent"] = now
            
        # Check if waiting for response for more than 15 mins
        if info.get("awaiting_response") and info.get("last_check_sent"):
            if now >= info["last_check_sent"] + timedelta(minutes=15):
                info["awaiting_response"] = False
                log.warning("No temp response for Load %s after 15m. Sending email.", load_id)
                import os
                notify_email = os.getenv("GMAIL_USER", "cavemann177@gmail.com")
                try:
                    from services.twilio_sms import forward_no_response_email
                    asyncio.create_task(forward_no_response_email(notify_email, load_id))
                except Exception as e:
                    log.error(f"Failed to trigger no response email: {e}")


async def _send_temp_check(load_id: str, driver_phone: str) -> None:
    """Send a temp check message to the driver's Discord thread."""
    if not _bot:
        log.warning("Bot not initialized for temp checker")
        return

    from database.models import AsyncSessionLocal, Load
    from sqlalchemy.future import select

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Load).where(Load.load_id == load_id))
            load = result.scalars().first()
            if not load or not load.discord_thread_id:
                log.warning("No Discord thread found for load %s — stopping temp checks.", load_id)
                _active_checks.pop(load_id, None)
                return

            # Stop if load is no longer in transit
            if load.status not in ('In Transit', 'Assigned', 'Dispatched'):
                log.info("Load %s is '%s' — stopping temp checks.", load_id, load.status)
                _active_checks.pop(load_id, None)
                return

            thread_id = int(load.discord_thread_id)

        thread = _bot.get_channel(thread_id)
        if not thread:
            try:
                thread = await _bot.fetch_channel(thread_id)
            except discord.NotFound:
                log.warning("Could not find Discord thread %s for load %s", thread_id, load_id)
                _active_checks.pop(load_id, None)
                return

        await thread.send(
            f"🌡️ **HAUL-E Temp Check — Load {load_id}**\n"
            f"What is your current reefer temperature reading?"
        )
        log.info("🌡️  Temp check sent to thread | Load: %s", load_id)

    except Exception:
        log.exception("❌ Failed to send temp check | Load: %s", load_id)


# ── Public API ────────────────────────────────────────────────────────────────

async def start_temp_checks(
    load_id: str,
    driver_phone: str,
    interval_minutes: int = 180,
) -> None:
    """
    Start recurring temperature check-ins for a load.

    Args:
        load_id:          Unique load identifier.
        driver_phone:     Driver's phone number (kept for reference).
        interval_minutes: Minutes between each check. Defaults to 180 (3 hours).
    """
    now = datetime.now(timezone.utc)

    _active_checks[load_id] = {
        "driver_phone": driver_phone,
        "interval_minutes": interval_minutes,
        "last_sent": now,
        "next_send": now + timedelta(minutes=interval_minutes),
    }

    log.info(
        "🌡️  Temp checks started | Load: %s | Every %dm",
        load_id,
        interval_minutes,
    )

    # Ensure loop is running
    _start_loop()

    # Fire the first check immediately
    await _send_temp_check(load_id, driver_phone)


async def stop_temp_checks(load_id: str) -> None:
    """Stop recurring temperature checks for a load."""
    removed = _active_checks.pop(load_id, None)
    if removed:
        log.info("🛑 Temp checks stopped | Load: %s", load_id)
    else:
        log.warning("⚠️  No active temp checks for Load: %s (already stopped?)", load_id)

def mark_temp_responded(load_id: str) -> None:
    """Mark that the driver responded to the temp check."""
    if load_id in _active_checks:
        _active_checks[load_id]["awaiting_response"] = False
        log.info("✅ Marked temp check as responded for Load %s", load_id)

def update_temp_interval(load_id: str, new_interval_minutes: int) -> bool:
    """Update the interval for an active temp check."""
    if load_id in _active_checks:
        info = _active_checks[load_id]
        info["interval_minutes"] = new_interval_minutes
        info["next_send"] = info["last_sent"] + timedelta(minutes=new_interval_minutes)
        log.info(f"⏱️ Updated temp check interval for {load_id} to {new_interval_minutes}m")
        return True
    return False


def get_active_checks() -> List[Dict[str, Any]]:
    """Returns a list of all currently active temp-check jobs."""
    active = []
    for load_id, info in _active_checks.items():
        active.append({
            "load_id": load_id,
            "driver_phone": info["driver_phone"],
            "interval_minutes": info["interval_minutes"],
            "next_run": info["next_send"].isoformat(),
        })
    return active


# ── Stubs for Legacy API ──────────────────────────────────────────────────────
class _DummyScheduler:
    running = True
    def start(self): pass
    def get_job(self, job_id): return None

_scheduler = _DummyScheduler()

async def start_location_checks(load_id: str, shipper_email: str, interval_minutes: int = 180):
    log.info(f"📍 Location checks stub called for {load_id}")

async def stop_location_checks(load_id: str):
    pass

def schedule_delivery_check(load_id: str, driver_phone: str, run_date):
    log.info(f"📍 Delivery check stub scheduled for {load_id} at {run_date}")
