"""
temp_checker.py — APScheduler-based Temperature Check-In Service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Manages recurring temperature check SMS messages to drivers for active reefer
loads.  Each load gets its own APScheduler interval job, keyed by load_id.

Public API:
  start_temp_checks(load_id, driver_phone, interval_hours=3)
  stop_temp_checks(load_id)
  get_active_checks()

Sends messages through services.twilio_sms.send_temp_check().
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
from typing import List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from services.twilio_sms import send_temp_check

log = logging.getLogger("broker_bot.temp_checker")

# ── Module-Level Scheduler Singleton ──────────────────────────────────────────
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///apscheduler_jobs.sqlite')
}
_scheduler: AsyncIOScheduler = AsyncIOScheduler(jobstores=jobstores)

# Prefix used for all temp-check job IDs so they don't collide with other jobs.
_JOB_ID_PREFIX = "temp_check_"


def _build_job_id(load_id: str) -> str:
    """Returns a deterministic scheduler job ID for a given load."""
    return f"{_JOB_ID_PREFIX}{load_id}"


def _build_temp_check_message(load_id: str) -> str:
    """Builds the SMS body sent to the driver for a temperature check-in."""
    return (
        f"🌡️ HAUL-E Temp Check — Load {load_id}\n"
        f"Please confirm: Is the temperature correct? "
        f"Reply YES or NO with current reading."
    )


# ── Scheduled Callback ───────────────────────────────────────────────────────

async def _send_temp_check_sms(load_id: str, driver_phone: str) -> None:
    """
    Callback executed by the scheduler on each interval tick.
    Sends a temp-check SMS to the driver and logs the result.
    """
    try:
        await send_temp_check(driver_phone, load_id)
        log.info(
            "🌡️  Temp check sent | Load: %s | Driver: %s",
            load_id,
            driver_phone,
        )
        
        # Schedule 15 minute timeout check
        from datetime import datetime, timedelta
        import pytz
        import uuid
        now_utc = datetime.now(pytz.utc)
        
        if not _scheduler.running:
            _scheduler.start()
            
        _scheduler.add_job(
            _check_temp_timeout,
            trigger="date",
            run_date=datetime.now() + timedelta(minutes=15),
            args=[load_id, now_utc],
            id=f"timeout_{load_id}_{uuid.uuid4().hex[:8]}"
        )
    except Exception:
        log.exception(
            "❌ Failed to send temp check | Load: %s | Driver: %s",
            load_id,
            driver_phone,
        )

async def _check_temp_timeout(load_id: str, sent_time_utc) -> None:
    from database.session import get_db_session
    from database.models import Load, TempCheckLog
    from sqlalchemy import select
    from services.motive_service import get_vehicle_tracking
    from services.twilio_sms import forward_temp_response_email
    import asyncio
    
    try:
        async with get_db_session() as session:
            load = (await session.execute(select(Load).where(Load.load_id == load_id))).scalars().first()
            if not load or load.status not in ["In Transit", "Dispatched"]:
                return
                
            recent_log = (await session.execute(
                select(TempCheckLog)
                .where(TempCheckLog.load_id == load_id)
                .where(TempCheckLog.timestamp > sent_time_utc.replace(tzinfo=None))
            )).scalars().first()
            
            if not recent_log:
                # Driver didn't respond!
                tracking = await asyncio.to_thread(get_vehicle_tracking, load.driver)
                eta_str = "Unknown"
                if tracking:
                    eta_str = f"{tracking.get('eta_time', 'Unknown')} ({tracking.get('distance_to_destination', 'Unknown')} left)"
                
                msg_body = "No response by driver as he is off duty."
                if eta_str != "Unknown":
                    msg_body += f"\n\nCurrent Motive ETA: {eta_str}"
                    
                if load.shipper_email:
                    await forward_temp_response_email(load.shipper_email, load.load_id, msg_body, is_issue=True)
                elif load.broker_email:
                    await forward_temp_response_email(load.broker_email, load.load_id, msg_body, is_issue=True)
                    
                log.info(f"Driver timeout reached for {load_id}. Emailed shipper.")
    except Exception as e:
        log.error(f"Failed to process driver timeout for {load_id}: {e}")

async def _send_silent_location_update(load_id: str, shipper_email: str) -> None:
    try:
        from services.twilio_sms import forward_location_email
        await forward_location_email(shipper_email, load_id)
        log.info(f"📍 Silent tracking check triggered | Load: {load_id}")
    except Exception:
        log.exception(f"❌ Failed to trigger silent tracking | Load: {load_id}")

# ── Public API ────────────────────────────────────────────────────────────────

async def start_location_checks(
    load_id: str,
    shipper_email: str,
    interval_minutes: int = 180,
) -> None:
    job_id = _build_job_id(load_id) # Using same prefix so stop_temp_checks works for both
    
    if not _scheduler.running:
        _scheduler.start()
        
    _scheduler.add_job(
        _send_silent_location_update,
        trigger="interval",
        minutes=interval_minutes,
        id=job_id,
        replace_existing=True,
        args=[load_id, shipper_email],
        name=f"Tracking update — Load {load_id}",
    )
    log.info(f"📍 Tracking checks started | Load: {load_id} | Every {interval_minutes}m")
    await _send_silent_location_update(load_id, shipper_email)

async def start_temp_checks(
    load_id: str,
    driver_phone: str,
    interval_minutes: int = 1,
) -> None:
    """
    Start recurring temperature check-in SMS for a load.

    Args:
        load_id:          Unique load identifier (e.g. "MOR-12345").
        driver_phone:     Driver's phone number in E.164 format (e.g. "+15551234567").
        interval_minutes: Minutes between each check-in SMS. Defaults to 1 for testing.

    If a job already exists for this load_id it is replaced so the interval
    or phone number can be updated without a separate stop call.
    """
    job_id = _build_job_id(load_id)

    # Ensure the scheduler is running (idempotent after the first call).
    if not _scheduler.running:
        _scheduler.start()
        log.info("✅ Temp-check scheduler started")

    _scheduler.add_job(
        _send_temp_check_sms,
        trigger="interval",
        minutes=interval_minutes,
        id=job_id,
        replace_existing=True,
        args=[load_id, driver_phone],
        name=f"Temp check — Load {load_id}",
        misfire_grace_time=3600,
    )

    log.info(
        "🌡️  Temp checks started | Load: %s | Driver: %s | Every %dm",
        load_id,
        driver_phone,
        interval_minutes,
    )

    # Fire the first check immediately so the driver isn't waiting N hours.
    await _send_temp_check_sms(load_id, driver_phone)


async def stop_temp_checks(load_id: str) -> None:
    """
    Stop recurring temperature check-in SMS for a delivered/cancelled load.

    Args:
        load_id: The load whose temp-check job should be removed.

    Silently succeeds if no job exists for the given load_id.
    """
    job_id = _build_job_id(load_id)
    try:
        _scheduler.remove_job(job_id)
        log.info("🛑 Temp checks stopped | Load: %s", load_id)
    except JobLookupError:
        log.warning(
            "⚠️  No active temp-check job found for Load: %s (already stopped?)",
            load_id,
        )


def get_active_checks() -> List[Dict[str, Any]]:
    """
    Returns a list of all currently active temp-check jobs.

    Each entry is a dict with:
        load_id         — The load identifier.
        driver_phone    — The driver's phone number.
        interval_hours  — Hours between SMS messages.
        next_run        — Next scheduled execution time (ISO 8601 string or None).
    """
    active: List[Dict[str, Any]] = []

    for job in _scheduler.get_jobs():
        if not job.id.startswith(_JOB_ID_PREFIX):
            continue

        load_id = job.args[0] if job.args else job.id.removeprefix(_JOB_ID_PREFIX)
        driver_phone = job.args[1] if job.args and len(job.args) > 1 else "unknown"

        # Extract interval minutes from the trigger.
        interval_minutes = None
        if hasattr(job.trigger, "interval"):
            interval_minutes = int(job.trigger.interval.total_seconds() // 60)

        active.append({
            "load_id": load_id,
            "driver_phone": driver_phone,
            "interval_minutes": interval_minutes,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })

    return active

# ── Delivery Check Scheduling ────────────────────────────────────────────────

async def _send_delivery_check_sms(load_id: str, driver_phone: str) -> None:
    """
    Callback executed when the expected delivery time is reached.
    """
    try:
        from services.twilio_sms import _send_whatsapp_sync
        import asyncio
        msg = f"📍 HAUL-E Delivery Check — Load {load_id}\n\nHave you completed the delivery? Please reply 'Delivered' when empty, or let us know if there are any delays."
        await asyncio.to_thread(_send_whatsapp_sync, driver_phone, msg)
        log.info(f"📍 Delivery check sent | Load: {load_id} | Driver: {driver_phone}")
    except Exception:
        log.exception(f"❌ Failed to send delivery check | Load: {load_id} | Driver: {driver_phone}")

def schedule_delivery_check(load_id: str, driver_phone: str, run_date) -> None:
    """
    Schedule a one-time message to check if the driver has delivered.
    """
    job_id = f"delivery_check_{load_id}"
    
    if not _scheduler.running:
        _scheduler.start()
        
    _scheduler.add_job(
        _send_delivery_check_sms,
        trigger="date",
        run_date=run_date,
        id=job_id,
        replace_existing=True,
        args=[load_id, driver_phone],
        name=f"Delivery check — Load {load_id}",
    )
    log.info(f"📍 Scheduled delivery check | Load: {load_id} | Time: {run_date}")
