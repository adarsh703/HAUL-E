"""
main.py — Mor Logistics Broker Bot (Discord Hub)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The central Discord bot engine. Responsibilities:

  • Hosts all slash commands (/sendmail, /parsefile, /skills, /ping, /help)
  • Registers all skills via SkillRegistry on startup
  • Orchestrates the 3-step pipeline: AI Draft → Gmail Send → Sheets Log
  • Returns live step-by-step progress updates as Discord embed edits
  • Handles all errors gracefully without crashing the bot

Pipeline:
    Discord /sendmail  →  Claude AI  →  Gmail SMTP  →  Google Sheets  →  ✅ Discord Embed

Run:
    python main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import io
import logging

import discord
from discord import app_commands
from dotenv import load_dotenv

from skills import SkillRegistry
from skills.parse_load import register as register_parse
from skills.send_email import register as register_email
from skills.log_outreach import register as register_log
from sheets_logger import ensure_headers
from claude_ai import parse_attachment_and_draft

load_dotenv()

from logging.handlers import RotatingFileHandler

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            "broker_bot.log", 
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=2,
            encoding="utf-8"
        ),
    ],
)
log = logging.getLogger("broker_bot.main")

# ── Config ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
ALLOWED_CHANNEL_ID: int = int(os.getenv("ALLOWED_CHANNEL_ID", 0))

if not DISCORD_TOKEN:
    raise EnvironmentError(
        "DISCORD_TOKEN is not set. Add it to your .env file.\n"
        "Get your token at: https://discord.com/developers/applications"
    )

# Brand colour palette
COLOUR_BRAND   = 0x5865F2   # Discord blurple (in-progress)
COLOUR_SUCCESS = 0x57F287   # Green
COLOUR_WARNING = 0xFEE75C   # Yellow
COLOUR_ERROR   = 0xED4245   # Red


# ── Bot Definition ────────────────────────────────────────────────────────────

class BrokerBot(discord.Client):
    """
    Core Discord client for the Mor Logistics Broker Outreach Bot.

    Skills are registered in setup_hook() via the SkillRegistry.
    Adding a new skill requires only:
      1. Writing the skill in skills/<your_skill>.py
      2. Importing and calling register(self.skills) here
    """

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.skills = SkillRegistry()

    async def setup_hook(self) -> None:
        """
        Runs once before the bot connects to Discord.
        Registers all skills and syncs slash commands globally.
        """
        # ── Register skills ───────────────────────────────────────────────────
        register_parse(self.skills)
        register_email(self.skills)
        register_log(self.skills)
        # ↑ To add a new skill, import its register() function and call it here.

        # ── Bootstrap Google Sheet headers (non-fatal if it fails) ────────────
        await ensure_headers()

        # ── Sync slash commands with Discord ──────────────────────────────────
        await self.tree.sync()
        log.info("✅ Slash commands synced | Active skills: %s", self.skills.list_skills())

    async def on_ready(self) -> None:
        log.info("🤖 Bot online: %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/sendmail"
            )
        )


client = BrokerBot()


# ── Embed Helpers ─────────────────────────────────────────────────────────────

def _progress_embed(
    broker_name: str,
    broker_email: str,
    lane: str,
    date: str,
    status_text: str,
    color: int = COLOUR_BRAND,
) -> discord.Embed:
    """Builds the standard pipeline progress embed."""
    embed = discord.Embed(
        title="📬  Broker Outreach Pipeline",
        color=color,
    )
    embed.add_field(
        name="👤 Broker",
        value=f"**{broker_name}**\n`{broker_email}`",
        inline=True,
    )
    embed.add_field(name="🛣️ Lane", value=lane, inline=True)
    embed.add_field(name="📅 Date", value=date, inline=True)
    embed.add_field(name="⚙️ Pipeline Status", value=status_text, inline=False)
    return embed


def _error_embed(title: str, detail: str) -> discord.Embed:
    """Builds a compact error embed."""
    embed = discord.Embed(title=f"❌  {title}", color=COLOUR_ERROR)
    embed.description = f"```{str(detail)[:1000]}```"
    embed.set_footer(text="Check broker_bot.log for the full stack trace.")
    return embed


# ── Channel Guard ─────────────────────────────────────────────────────────────

def _allowed(interaction: discord.Interaction) -> bool:
    """Returns True if the command is permitted in this channel."""
    return ALLOWED_CHANNEL_ID == 0 or interaction.channel_id == ALLOWED_CHANNEL_ID


# ── Safe Sheets Log ───────────────────────────────────────────────────────────

async def _safe_log(
    broker_name: str,
    broker_email: str,
    lane: str,
    date: str,
    status: str,
    email_preview: str,
) -> bool:
    """Logs to Sheets; returns True on success, False on failure (non-fatal)."""
    try:
        await client.skills.execute(
            "log_outreach",
            broker_name=broker_name,
            broker_email=broker_email,
            lane=lane,
            date=date,
            status=status,
            email_preview=email_preview,
        )
        return True
    except Exception as exc:
        log.error("Sheets logging failed: %s", exc, exc_info=True)
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@client.tree.command(
    name="sendmail",
    description="Draft and send a professional broker outreach email.",
)
@app_commands.describe(
    broker_email="Broker's email address (e.g. surinder@amodispatch.ca)",
    broker_name="Broker's first name (e.g. Surinder)",
    lane='Full lane — origin to destination (e.g. "Laredo TX to Toronto ON")',
    date='Pickup / availability date (e.g. "June 3")',
    notes="Optional: special instructions or extra context",
)
async def cmd_sendmail(
    interaction: discord.Interaction,
    broker_email: str,
    broker_name: str,
    lane: str,
    date: str,
    notes: str = "",
) -> None:
    """
    Full 3-step pipeline:
      1. Claude AI drafts a personalized email
      2. Gmail SMTP sends it to the broker
      3. Google Sheets logs the outreach record

    Each step updates the same embed in-place, giving live progress feedback.
    """
    if not _allowed(interaction):
        await interaction.response.send_message(
            "❌ This command is only permitted in the designated outreach channel.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)
    log.info(
        "Pipeline started | Broker: %s <%s> | Lane: %s | Date: %s",
        broker_name, broker_email, lane, date,
    )

    # ── Initial embed ─────────────────────────────────────────────────────────
    embed = _progress_embed(
        broker_name, broker_email, lane, date,
        "**Step 1 / 3** ⏳  Drafting your email…",
    )
    msg: discord.WebhookMessage = await interaction.followup.send(embed=embed)

    # ── Step 1: AI Draft ──────────────────────────────────────────────────────
    email_body = ""
    try:
        result = await client.skills.execute(
            "parse_and_draft",
            broker_email=broker_email,
            broker_name=broker_name,
            lane=lane,
            date=date,
            notes=notes,
        )
        email_body = result["email_body"]
        embed = _progress_embed(
            broker_name, broker_email, lane, date,
            "**Step 1 / 3** ✅  Email drafted\n"
            "**Step 2 / 3** ⏳  Sending email…",
        )
        await msg.edit(embed=embed)
    except Exception as exc:
        log.error("AI draft failed: %s", exc, exc_info=True)
        embed = _progress_embed(
            broker_name, broker_email, lane, date,
            f"**Step 1 / 3** ❌  AI drafting error",
            color=COLOUR_ERROR,
        )
        embed.add_field(name="Error Detail", value=f"```{str(exc)[:512]}```", inline=False)
        await msg.edit(embed=embed)
        await _safe_log(broker_name, broker_email, lane, date, f"PARSE_FAILED: {exc}", "")
        return

    # ── Step 2: Send Email ────────────────────────────────────────────────────
    try:
        await client.skills.execute(
            "send_email",
            to=broker_email,
            broker_name=broker_name,
            lane=lane,
            body=email_body,
        )
        embed = _progress_embed(
            broker_name, broker_email, lane, date,
            "**Step 1 / 3** ✅  Email drafted\n"
            "**Step 2 / 3** ✅  Email sent\n"
            "**Step 3 / 3** ⏳  Logging to Sheets…",
        )
        await msg.edit(embed=embed)
    except Exception as exc:
        log.error("Gmail send failed: %s", exc, exc_info=True)
        embed = _progress_embed(
            broker_name, broker_email, lane, date,
            "**Step 1 / 3** ✅  Email drafted\n"
            f"**Step 2 / 3** ❌  Send failed",
            color=COLOUR_ERROR,
        )
        embed.add_field(name="Error Detail", value=f"```{str(exc)[:512]}```", inline=False)
        await msg.edit(embed=embed)
        await _safe_log(broker_name, broker_email, lane, date, f"SEND_FAILED: {exc}", email_body[:250])
        return

    # ── Step 3: Log to Sheets ─────────────────────────────────────────────────
    log_ok = await _safe_log(broker_name, broker_email, lane, date, "SENT", email_body)

    # ── Final success embed ───────────────────────────────────────────────────
    log_status = "✅  Logged to Google Sheets" if log_ok else "⚠️  Email sent, but Sheets logging failed"
    final_color = COLOUR_SUCCESS if log_ok else COLOUR_WARNING

    final_embed = _progress_embed(
        broker_name, broker_email, lane, date,
        f"**Step 1 / 3** ✅  Email drafted\n"
        f"**Step 2 / 3** ✅  Email sent\n"
        f"**Step 3 / 3** {log_status}",
        color=final_color,
    )
    preview = email_body[:420].strip()
    final_embed.add_field(
        name="📧  Email Preview",
        value=f"```{preview}{'…' if len(email_body) > 420 else ''}```",
        inline=False,
    )
    await msg.edit(embed=final_embed)
    log.info("Pipeline complete | Broker: %s <%s>", broker_name, broker_email)


# ── /parsefile — Vision-based DAT screenshot parsing ─────────────────────────

@client.tree.command(
    name="parsefile",
    description="Upload a DAT screenshot or load board image — AI extracts data and sends the email.",
)
@app_commands.describe(
    attachment="A DAT load board screenshot (PNG, JPG, or WEBP)",
    notes="Optional: extra instructions or context",
)
async def cmd_parsefile(
    interaction: discord.Interaction,
    attachment: discord.Attachment,
    notes: str = "",
) -> None:
    """
    Vision pipeline:
      1. Download the uploaded image
      2. Claude vision extracts: Broker Name, Broker Email, Lane, Date
      3. Claude drafts the email
      4. Gmail sends it
      5. Sheets logs it
    """
    if not _allowed(interaction):
        await interaction.response.send_message(
            "❌ This command is only permitted in the designated outreach channel.",
            ephemeral=True,
        )
        return

    # Validate file type
    allowed_types = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    if attachment.content_type not in allowed_types:
        await interaction.response.send_message(
            f"❌ Unsupported file type: `{attachment.content_type}`.\n"
            "Please upload a PNG, JPG, WEBP, or GIF image of the DAT load board.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)
    log.info("Vision pipeline started | File: %s | Type: %s", attachment.filename, attachment.content_type)

    # ── Step 1: Download attachment ───────────────────────────────────────────
    init_embed = discord.Embed(
        title="🖼️  DAT Screenshot Parser",
        color=COLOUR_BRAND,
    )
    init_embed.add_field(name="📎 File", value=attachment.filename, inline=True)
    init_embed.add_field(name="⚙️ Status", value="⏳ Downloading & parsing image…", inline=False)
    msg = await interaction.followup.send(embed=init_embed)

    try:
        file_bytes = await attachment.read()
    except Exception as exc:
        log.error("Attachment download failed: %s", exc, exc_info=True)
        init_embed.set_field_at(1, name="⚙️ Status", value=f"❌ Download failed\n```{exc}```", inline=False)
        init_embed.color = COLOUR_ERROR
        await msg.edit(embed=init_embed)
        return

    # ── Step 2: Claude Vision parse + draft ──────────────────────────────────
    try:
        result = await parse_attachment_and_draft(
            file_bytes=file_bytes,
            media_type=attachment.content_type,
            notes=notes,
        )
    except Exception as exc:
        log.error("Vision parse failed: %s", exc, exc_info=True)
        init_embed.set_field_at(1, name="⚙️ Status", value=f"❌ Vision parse error\n```{exc}```", inline=False)
        init_embed.color = COLOUR_ERROR
        await msg.edit(embed=init_embed)
        return

    # Hand off to the standard email+log pipeline using extracted data
    broker_name  = result["broker_name"]
    broker_email = result["broker_email"]
    lane         = result["lane"]
    date         = result["date"]
    email_body   = result["email_body"]

    # ── Step 3: Send email ────────────────────────────────────────────────────
    progress_embed = _progress_embed(
        broker_name, broker_email, lane, date,
        "**Vision Parse** ✅  Data extracted\n"
        "**Step 2 / 3** ⏳  Sending via Gmail…",
    )
    progress_embed.set_field_at(0, name="👤 Broker", value=f"**{broker_name}**\n`{broker_email}`", inline=True)
    await msg.edit(embed=progress_embed)

    try:
        await client.skills.execute(
            "send_email",
            to=broker_email,
            broker_name=broker_name,
            lane=lane,
            body=email_body,
        )
    except Exception as exc:
        log.error("Gmail send failed (vision pipeline): %s", exc, exc_info=True)
        progress_embed = _progress_embed(
            broker_name, broker_email, lane, date,
            f"**Vision Parse** ✅  Data extracted\n**Step 2 / 3** ❌  Gmail error",
            color=COLOUR_ERROR,
        )
        progress_embed.add_field(name="Error", value=f"```{str(exc)[:512]}```", inline=False)
        await msg.edit(embed=progress_embed)
        await _safe_log(broker_name, broker_email, lane, date, f"SEND_FAILED: {exc}", email_body[:250])
        return

    # ── Step 4: Log ───────────────────────────────────────────────────────────
    log_ok = await _safe_log(broker_name, broker_email, lane, date, "SENT (VISION)", email_body)

    log_status = "✅  Logged to Google Sheets" if log_ok else "⚠️  Email sent, Sheets logging failed"
    final_embed = _progress_embed(
        broker_name, broker_email, lane, date,
        f"**Vision Parse** ✅  Data extracted\n"
        f"**Step 2 / 3** ✅  Email sent via Gmail\n"
        f"**Step 3 / 3** {log_status}",
        color=COLOUR_SUCCESS if log_ok else COLOUR_WARNING,
    )
    preview = email_body[:420].strip()
    final_embed.add_field(
        name="📧  Email Preview",
        value=f"```{preview}{'…' if len(email_body) > 420 else ''}```",
        inline=False,
    )
    await msg.edit(embed=final_embed)


# ── /skills — List registered skills ─────────────────────────────────────────

@client.tree.command(
    name="skills",
    description="List all registered bot skills/tools.",
)
async def cmd_skills(interaction: discord.Interaction) -> None:
    """Shows every skill currently loaded in the SkillRegistry."""
    skill_list = client.skills.list_skills()
    lines = "\n".join(f"• `{s}`" for s in skill_list) if skill_list else "_No skills loaded._"
    embed = discord.Embed(
        title="🧠  Registered Bot Skills",
        description=lines,
        color=COLOUR_BRAND,
    )
    embed.add_field(
        name="ℹ️ How to extend",
        value="Add a new file in `skills/`, implement an async function, "
              "call `register(registry)`, and import it in `main.py setup_hook()`. "
              "Zero changes to the core bot engine.",
        inline=False,
    )
    embed.set_footer(text=f"Total skills: {len(skill_list)}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── /ping — Health check ──────────────────────────────────────────────────────

@client.tree.command(name="ping", description="Check if the bot is alive.")
async def cmd_ping(interaction: discord.Interaction) -> None:
    latency_ms = round(client.latency * 1000)
    await interaction.response.send_message(
        f"🏓  Pong! Latency: **{latency_ms} ms**", ephemeral=True
    )


# ── /help — Command reference ─────────────────────────────────────────────────

@client.tree.command(
    name="help",
    description="Show all available commands and how to use them.",
)
async def cmd_help(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="📖  Broker Bot — Command Reference",
        color=COLOUR_BRAND,
    )
    embed.add_field(
        name="`/sendmail`",
        value="Draft and send a broker outreach email.\n"
              "**Args:** `broker_email` `broker_name` `lane` `date` `[notes]`\n"
              "**Example:** `/sendmail broker_email:sur@amodispatch.ca broker_name:Surinder "
              'lane:"Laredo TX to Toronto ON" date:"June 3"`',
        inline=False,
    )
    embed.add_field(
        name="`/parsefile`",
        value="Upload a DAT screenshot — AI extracts data and sends the email automatically.\n"
              "**Args:** `attachment` `[notes]`",
        inline=False,
    )
    embed.add_field(
        name="`/skills`",
        value="List all registered bot skills/tools.",
        inline=True,
    )
    embed.add_field(
        name="`/ping`",
        value="Check bot latency.",
        inline=True,
    )
    embed.add_field(
        name="`/help`",
        value="Show this message.",
        inline=True,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client.run(DISCORD_TOKEN, log_handler=None)
