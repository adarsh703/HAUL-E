"""
skills/log_outreach.py — Activity Logging Skill
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wraps sheets_logger.append_outreach_log as a registerable SkillRegistry entry.

To register:
    from skills.log_outreach import register
    register(registry)

Future skill extensions you can add here without touching main.py:
    • log_to_crm           — push records to HubSpot / Pipedrive / Salesforce
    • generate_daily_report — summarize today's outreach stats to a Discord channel
    • alert_on_threshold   — notify manager if daily outreach < target volume
    • export_to_csv        — export the Sheets log as a CSV on demand
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from skills import SkillRegistry
from sheets_logger import append_outreach_log


async def _log_outreach_skill(
    broker_name: str,
    broker_email: str,
    lane: str,
    date: str,
    status: str,
    email_preview: str,
) -> None:
    """
    Skill entry point — appends one outreach row to Google Sheets.

    Args:
        broker_name:   Broker's display name.
        broker_email:  Broker's email address.
        lane:          Full lane string.
        date:          Pickup date string.
        status:        Outcome status code (e.g. "SENT", "SEND_FAILED").
        email_preview: First ~250 chars of the drafted email body.
    """
    await append_outreach_log(
        broker_name=broker_name,
        broker_email=broker_email,
        lane=lane,
        date=date,
        status=status,
        email_preview=email_preview,
    )


def register(registry: SkillRegistry) -> None:
    """
    Register the 'log_outreach' skill into the provided SkillRegistry.
    Called once during bot startup in main.py setup_hook().
    """
    registry.register("log_outreach", _log_outreach_skill)
