import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.embeds import progress_embed, COLOUR_ERROR, COLOUR_SUCCESS, COLOUR_WARNING, COLOUR_BRAND
from claude_ai import parse_attachment_and_draft
import os

log = logging.getLogger("broker_bot.email_outreach")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", 0))

class EmailOutreach(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _allowed(self, interaction: discord.Interaction) -> bool:
        """Returns True if the command is permitted in this channel."""
        return ALLOWED_CHANNEL_ID == 0 or interaction.channel_id == ALLOWED_CHANNEL_ID

    async def _safe_log(
        self,
        broker_name: str,
        broker_email: str,
        lane: str,
        date: str,
        status: str,
        email_preview: str,
    ) -> bool:
        """Logs to Sheets; returns True on success, False on failure (non-fatal)."""
        try:
            await self.bot.skills.execute(
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

    @app_commands.command(
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
    async def sendmail(
        self,
        interaction: discord.Interaction,
        broker_email: str,
        broker_name: str,
        lane: str,
        date: str,
        notes: str = "",
    ) -> None:
        """
        Full 3-step pipeline:
          1. AI drafts a personalized email
          2. Gmail SMTP sends it to the broker
          3. Google Sheets logs the outreach record
        """
        if not self._allowed(interaction):
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

        embed = progress_embed(
            broker_name, broker_email, lane, date,
            "**Step 1 / 3** ⏳  Drafting your email…",
        )
        msg = await interaction.followup.send(embed=embed)

        # Step 1: AI Draft
        email_body = ""
        try:
            result = await self.bot.skills.execute(
                "parse_and_draft",
                broker_email=broker_email,
                broker_name=broker_name,
                lane=lane,
                date=date,
                notes=notes,
            )
            email_body = result["email_body"]
            embed = progress_embed(
                broker_name, broker_email, lane, date,
                "**Step 1 / 3** ✅  Email drafted\n"
                "**Step 2 / 3** ⏳  Sending email…",
            )
            await msg.edit(embed=embed)
        except Exception as exc:
            log.error("AI draft failed: %s", exc, exc_info=True)
            embed = progress_embed(
                broker_name, broker_email, lane, date,
                f"**Step 1 / 3** ❌  AI drafting error",
                color=COLOUR_ERROR,
            )
            embed.add_field(name="Error Detail", value=f"```{str(exc)[:512]}```", inline=False)
            await msg.edit(embed=embed)
            await self._safe_log(broker_name, broker_email, lane, date, f"PARSE_FAILED: {exc}", "")
            return

        # Step 2: Send Email
        try:
            await self.bot.skills.execute(
                "send_email",
                to=broker_email,
                broker_name=broker_name,
                lane=lane,
                body=email_body,
            )
            embed = progress_embed(
                broker_name, broker_email, lane, date,
                "**Step 1 / 3** ✅  Email drafted\n"
                "**Step 2 / 3** ✅  Email sent\n"
                "**Step 3 / 3** ⏳  Logging to Sheets…",
            )
            await msg.edit(embed=embed)
        except Exception as exc:
            log.error("Gmail send failed: %s", exc, exc_info=True)
            embed = progress_embed(
                broker_name, broker_email, lane, date,
                "**Step 1 / 3** ✅  Email drafted\n"
                f"**Step 2 / 3** ❌  Send failed",
                color=COLOUR_ERROR,
            )
            embed.add_field(name="Error Detail", value=f"```{str(exc)[:512]}```", inline=False)
            await msg.edit(embed=embed)
            await self._safe_log(broker_name, broker_email, lane, date, f"SEND_FAILED: {exc}", email_body[:250])
            return

        # Step 3: Log to Sheets
        log_ok = await self._safe_log(broker_name, broker_email, lane, date, "SENT", email_body)

        log_status = "✅  Logged to Google Sheets" if log_ok else "⚠️  Email sent, but Sheets logging failed"
        final_color = COLOUR_SUCCESS if log_ok else COLOUR_WARNING

        final_embed = progress_embed(
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

    @app_commands.command(
        name="parsefile",
        description="Upload a DAT screenshot or load board image — AI extracts data and sends the email.",
    )
    @app_commands.describe(
        attachment="A DAT load board screenshot (PNG, JPG, or WEBP)",
        notes="Optional: extra instructions or context",
    )
    async def parsefile(
        self,
        interaction: discord.Interaction,
        attachment: discord.Attachment,
        notes: str = "",
    ) -> None:
        if not self._allowed(interaction):
            await interaction.response.send_message(
                "❌ This command is only permitted in the designated outreach channel.",
                ephemeral=True,
            )
            return

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

        broker_name  = result["broker_name"]
        broker_email = result["broker_email"]
        lane         = result["lane"]
        date         = result["date"]
        email_body   = result["email_body"]

        progress_embed_obj = progress_embed(
            broker_name, broker_email, lane, date,
            "**Vision Parse** ✅  Data extracted\n"
            "**Step 2 / 3** ⏳  Sending via Gmail…",
        )
        progress_embed_obj.set_field_at(0, name="👤 Broker", value=f"**{broker_name}**\n`{broker_email}`", inline=True)
        await msg.edit(embed=progress_embed_obj)

        try:
            await self.bot.skills.execute(
                "send_email",
                to=broker_email,
                broker_name=broker_name,
                lane=lane,
                body=email_body,
            )
        except Exception as exc:
            log.error("Gmail send failed (vision pipeline): %s", exc, exc_info=True)
            progress_embed_obj = progress_embed(
                broker_name, broker_email, lane, date,
                f"**Vision Parse** ✅  Data extracted\n**Step 2 / 3** ❌  Gmail error",
                color=COLOUR_ERROR,
            )
            progress_embed_obj.add_field(name="Error", value=f"```{str(exc)[:512]}```", inline=False)
            await msg.edit(embed=progress_embed_obj)
            await self._safe_log(broker_name, broker_email, lane, date, f"SEND_FAILED: {exc}", email_body[:250])
            return

        log_ok = await self._safe_log(broker_name, broker_email, lane, date, "SENT (VISION)", email_body)

        log_status = "✅  Logged to Google Sheets" if log_ok else "⚠️  Email sent, Sheets logging failed"
        final_embed = progress_embed(
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

async def setup(bot: commands.Bot):
    await bot.add_cog(EmailOutreach(bot))
