import os
import logging
from logging.handlers import RotatingFileHandler
import discord
from discord.ext import commands
from dotenv import load_dotenv

from skills import SkillRegistry
from skills.parse_load import register as register_parse
from skills.send_email import register as register_email
from skills.log_outreach import register as register_log
from sheets_logger import ensure_headers
from database.models import init_db

load_dotenv()

# Resolve credentials file to absolute path and set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI
creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
if os.path.exists(creds_file):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(creds_file)

# ── Logging Setup ─────────────────────────────────────────────────────────────
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

file_handler = RotatingFileHandler("broker_bot.log", maxBytes=5*1024*1024, backupCount=2, encoding="utf-8")
file_handler.setFormatter(log_formatter)

error_handler = RotatingFileHandler("bot-errors.log", maxBytes=5*1024*1024, backupCount=2, encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[stream_handler, file_handler, error_handler],
)
log = logging.getLogger("broker_bot.main")

# ── Config ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

if not DISCORD_TOKEN:
    raise EnvironmentError(
        "DISCORD_TOKEN is not set. Add it to your .env file.\n"
        "Get your token at: https://discord.com/developers/applications"
    )

# ── Bot Definition ────────────────────────────────────────────────────────────

class BrokerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required for OCR and Conversational LLM
        super().__init__(command_prefix="!", intents=intents)
        self.skills = SkillRegistry()

    async def setup_hook(self) -> None:
        # Register skills
        register_parse(self.skills)
        register_email(self.skills)
        register_log(self.skills)

        # Bootstrap Google Sheet headers
        await ensure_headers()
        
        # Initialize Database
        await init_db()

        # Load Cogs
        await self.load_extension("cogs.onboarding")
        await self.load_extension("cogs.tracking")
        await self.load_extension("cogs.ai_dispatcher")
        await self.load_extension("cogs.email_outreach")
        await self.load_extension("cogs.document_ocr")
        await self.load_extension("cogs.conversational_llm")
        await self.load_extension("cogs.driver_portal")
        await self.load_extension("cogs.email_listener")
        await self.load_extension("cogs.website_connector")

        # Sync slash commands with Discord
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

# Global Error Handler
@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    log.error(f"Global App Command Error: {error}", exc_info=True)
    if not interaction.response.is_done():
        await interaction.response.send_message("❌ An unexpected error occurred. Check bot-errors.log.", ephemeral=True)
    else:
        await interaction.followup.send("❌ An unexpected error occurred. Check bot-errors.log.", ephemeral=True)

if __name__ == "__main__":
    client.run(DISCORD_TOKEN, log_handler=None)
