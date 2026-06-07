"""
skills/send_email.py — Email Dispatch Skill
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wraps gmail_sender.send_broker_email as a registerable SkillRegistry entry.

To register:
    from skills.send_email import register
    register(registry)

Future skill extensions you can add here without touching main.py:
    • send_followup_email  — auto follow-up 3 business days after initial send
    • send_bulk_outreach   — batch through a CSV list of brokers
    • attach_rate_sheet    — attach a PDF rate sheet to the outreach email
    • cc_manager           — CC the sales manager on high-priority lanes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from skills import SkillRegistry
from gmail_sender import send_broker_email


async def _send_email_skill(
    to: str,
    broker_name: str,
    lane: str,
    body: str,
) -> None:
    """
    Skill entry point — dispatches the pre-drafted email via Gmail SMTP.

    Args:
        to:          Broker email address.
        broker_name: Broker name (for subject line & logging).
        lane:        Lane string (for subject line).
        body:        Full pre-drafted email body from Claude AI.
    """
    await send_broker_email(
        to=to,
        broker_name=broker_name,
        lane=lane,
        body=body,
    )


def register(registry: SkillRegistry) -> None:
    """
    Register the 'send_email' skill into the provided SkillRegistry.
    Called once during bot startup in main.py setup_hook().
    """
    registry.register("send_email", _send_email_skill)
