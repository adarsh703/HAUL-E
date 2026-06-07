"""
skills/parse_load.py — AI Email Drafting Skill
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wraps claude_ai.parse_and_draft_email as a registerable SkillRegistry entry.

To register:
    from skills.parse_load import register
    register(registry)

Future skill extensions you can add here without touching main.py:
    • parse_dat_screenshot — parse a DAT board image via Claude vision
    • extract_rate_info    — pull mileage/rate data from load board docs
    • suggest_counter_rate — AI-powered counter-rate recommendation
    • lane_market_analysis — summarize historical lane rate trends from DAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from typing import Any
from skills import SkillRegistry
from claude_ai import parse_and_draft_email


async def _parse_and_draft_skill(
    broker_email: str,
    broker_name: str,
    lane: str,
    date: str,
    notes: str = "",
) -> dict[str, Any]:
    """
    Skill entry point — invokes Claude AI to draft a personalized broker email.

    Returns:
        dict with keys: broker_name, broker_email, lane, date, email_body
    """
    return await parse_and_draft_email(
        broker_email=broker_email,
        broker_name=broker_name,
        lane=lane,
        date=date,
        notes=notes,
    )


def register(registry: SkillRegistry) -> None:
    """
    Register the 'parse_and_draft' skill into the provided SkillRegistry.
    Called once during bot startup in main.py setup_hook().
    """
    registry.register("parse_and_draft", _parse_and_draft_skill)
