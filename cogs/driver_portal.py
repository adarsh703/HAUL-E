import discord
from discord.ext import commands
import logging
import re
import os
import json
import asyncio
from sqlalchemy.future import select
from google import genai

from database.models import AsyncSessionLocal, Load
from utils.invoice_generator import generate_invoice
from gmail_sender import send_invoice_email

log = logging.getLogger("broker_bot.driver_portal")

DRIVERS_CHANNEL_ID = 1517447020791468122
NOTIFY_EMAIL = os.getenv("GMAIL_USER", "cavemann177@gmail.com")


class InvoiceApprovalView(discord.ui.View):
    def __init__(self, load_id: str, pdf_path: str, bol_path: str, notify_email: str):
        super().__init__(timeout=None)
        self.load_id = load_id
        self.pdf_path = pdf_path
        self.bol_path = bol_path
        self.notify_email = notify_email

    @discord.ui.button(label="Email Invoice", style=discord.ButtonStyle.success, emoji="📧")
    async def email_invoice(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            from cogs.driver_portal import send_invoice_email
            await send_invoice_email(
                to=self.notify_email,
                load_id=self.load_id,
                pdf_path=self.pdf_path,
                bol_path=self.bol_path
            )
            from database.models import AsyncSessionLocal, Load
            async with AsyncSessionLocal() as session:
                from sqlalchemy.future import select
                result = await session.execute(select(Load).where(Load.load_id == self.load_id))
                load = result.scalars().first()
                if load:
                    load.status = 'Invoiced'
                    await session.commit()
            
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(view=self)
            await interaction.followup.send(f"✅ Invoice successfully emailed to {self.notify_email}! (Status: Invoiced)")
        except Exception as e:
            import logging
            logging.error(f"Failed to auto-invoice: {e}")
            await interaction.followup.send(f"❌ Failed to email invoice: {e}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Cancelled. The invoice was not emailed.")

class DriverPortal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gemini_client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_PROJECT_ID"),
            location=os.getenv("GOOGLE_LOCATION")
        )
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _is_driver_thread(self, channel: discord.abc.Messageable) -> bool:
        """Check if a channel is a thread whose parent is the drivers channel."""
        if isinstance(channel, discord.Thread):
            return channel.parent_id == DRIVERS_CHANNEL_ID
        return False

    async def _find_load_for_thread(self, thread_id: str):
        """Look up a load by its discord_thread_id."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Load).where(Load.discord_thread_id == thread_id)
            )
            return result.scalars().first()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Only handle messages in threads under the drivers channel
        if not self._is_driver_thread(message.channel):
            return

        content = message.content.lower().strip()

        # Find the load associated with this thread
        load_record = await self._find_load_for_thread(str(message.channel.id))

        # Process attachments
        file_part = None
        if message.attachments:
            try:
                from google.genai import types
                attachment = message.attachments[0]
                file_bytes = await attachment.read()
                filename_lower = attachment.filename.lower()
                
                mime_type = "application/pdf"
                if filename_lower.endswith('.png'): mime_type = "image/png"
                elif filename_lower.endswith(('.jpg', '.jpeg')): mime_type = "image/jpeg"
                elif filename_lower.endswith('.webp'): mime_type = "image/webp"
                
                file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            except Exception as e:
                log.error(f"Error reading attachment in driver thread: {e}")

        # If we found the load via thread, we already know the load_id
        if load_record:
            load_id = load_record.load_id

            filename_hint = message.attachments[0].filename if message.attachments else "None"
            has_bol = "Yes" if load_record.bol_path else "No"
            
            prompt = f"""
Analyze this message from a truck driver in a dispatch thread for Load {load_id}.
Determine the driver's intent. Return a JSON object with key 'action'.

CRITICAL: If a document/image is attached, follow this strict sequential rule:
- If the load DOES NOT have a BOL yet (Has BOL: No), this first document is the Bill of Lading (BOL) → action MUST be "loaded"
- If the load ALREADY has a BOL (Has BOL: Yes), this second document is the Proof of Delivery (POD) → action MUST be "delivered"

If NO document is attached, classify based on the text:
- "loaded" — driver says they've picked up or are loaded
- "delivered" — driver says they've delivered or are empty
- "temp_response" — driver is responding to a temperature check (extract temp in 'temp_value')
- "issue" — driver is reporting a problem
- "unknown" — just chat or unrelated

Return JSON like: {{"action": "loaded"}} or {{"action": "temp_response", "temp_value": "-2°F"}}
Driver Message: "{content}"
Attached Filename: "{filename_hint}"
Has BOL: "{has_bol}"
"""
            try:
                contents = [prompt]
                if file_part:
                    contents.insert(0, file_part)
                    
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.model,
                    contents=contents
                )
                raw_json = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(raw_json)
            except Exception as e:
                log.error(f"Error parsing driver message with Gemini: {e}")
                data = {"action": "unknown"}

            action = data.get("action", "unknown")

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Load).where(Load.load_id == load_id))
                load = result.scalars().first()

                if not load:
                    return

                if action == "loaded":
                    load.status = 'In Transit'
                    await session.commit()
                    await message.add_reaction("✅")
                    await message.reply(f"🚚 **Load Status Updated**\nLoad {load_id} is now **In Transit**.")

                    if message.attachments:
                        await message.reply("📄 BOL received. Saved to file.")
                        try:
                            bol_attachment = message.attachments[0]
                            os.makedirs("bols", exist_ok=True)
                            bol_path = f"bols/BOL_{load_id}_{bol_attachment.filename}"
                            await bol_attachment.save(bol_path)
                            load.bol_path = bol_path
                            await session.commit()
                            
                            # Send email to cavemann
                            from gmail_sender import send_bol_email
                            asyncio.create_task(send_bol_email(NOTIFY_EMAIL, load_id, bol_path))
                            log.info(f"Emailed BOL to {NOTIFY_EMAIL}")
                                
                        except Exception as e:
                            log.error(f"Failed to save and email BOL: {e}")

                    # Automatically start Temp Checks ONLY if it's a reefer load
                    try:
                        from services.temp_checker import start_temp_checks
                        
                        # Check if this load has temperature requirements
                        is_reefer = False
                        try:
                            ops_data = json.loads(load.operational_intelligence) if load.operational_intelligence else {}
                            reefer_ops = ops_data.get('reefer_operations', {})
                            temp_setpoint = reefer_ops.get('temperature_setpoint', '')
                            temp_req = ops_data.get('load_information', {}).get('temperature_requirements', '')
                            if (temp_setpoint and temp_setpoint.lower() != 'n/a') or (temp_req and temp_req.lower() != 'n/a'):
                                is_reefer = True
                        except (json.JSONDecodeError, AttributeError):
                            pass
                        
                        if is_reefer and not load.temp_check_active:
                            await start_temp_checks(load.load_id, getattr(load, 'driver_phone', None), interval_minutes=180)
                            load.temp_check_active = True
                            await session.commit()
                            await message.reply(f"🌡️ **Reefer load detected** — temp checks started every 3 hours.")
                            log.info(f"Started temp checks for reefer load {load.load_id} after BOL receipt.")
                    except Exception as e:
                        log.error(f"Failed to start temp checks: {e}")

                elif action == "delivered":
                    load.status = 'Delivered'
                    await session.commit()
                    await message.add_reaction("✅")
                    try:
                        from services.temp_checker import stop_temp_checks
                        await stop_temp_checks(load_id)
                        load.temp_check_active = False
                        await session.commit()
                    except Exception as e:
                        log.error(f"Failed to stop temp checks for load {load_id}: {e}")
                    # In a real app we might parse attached PODs here
                    await message.reply(f"🚚 **Load Status Updated**\nLoad {load_id} is now **Delivered**. Temp checks disabled.")

                    if message.attachments:
                        await message.reply("📄 POD received. Generating invoice and emailing...")
                        
                        try:
                            # Save POD locally
                            pod_attachment = message.attachments[0]
                            os.makedirs("bols", exist_ok=True)
                            pod_path = f"bols/POD_{load_id}_{pod_attachment.filename}"
                            await pod_attachment.save(pod_path)

                            # Update load record with POD path
                            load.pod_path = pod_path
                            await session.commit()
                            
                            # Use existing BOL if uploaded at pickup, else use POD as BOL for invoice
                            final_bol = load.bol_path if load.bol_path else pod_path

                            # Generate Invoice
                            pdf_path = generate_invoice(
                                load_id=load.load_id,
                                broker_name=load.broker_email or "Broker",
                                origin_dest=load.origin_dest,
                                rate=load.rate,
                                date=load.pickup_date
                            )
                            
                            # Show in Discord and ask for approval
                            view = InvoiceApprovalView(load.load_id, pdf_path, final_bol, NOTIFY_EMAIL)
                            await message.reply(
                                f"💸 **Invoice generated for Load #{load.load_id}!**\n"
                                f"Should I email this invoice to `{NOTIFY_EMAIL}`?",
                                file=discord.File(pdf_path),
                                view=view
                            )
                        except Exception as e:
                            log.error(f"Failed to auto-invoice: {e}", exc_info=True)
                            await message.reply(f"❌ Failed to generate/send invoice: {e}")

                elif action == "temp_response":
                    temp_value = data.get("temp_value", content)
                    is_issue = "issue" in content.lower()
                    is_out_of_range = False
                    reported_temp_num = None
                    required_temp_num = None

                    reported_match = re.search(r'-?\d+', str(temp_value))
                    if reported_match:
                        reported_temp_num = float(reported_match.group())

                    try:
                        ops_data = json.loads(load.operational_intelligence) if load.operational_intelligence else {}
                        reefer_ops = ops_data.get('reefer_operations', {})
                        temp_setpoint = reefer_ops.get('temperature_setpoint', '')
                        temp_req = ops_data.get('load_information', {}).get('temperature_requirements', '')
                        
                        req_str = str(temp_setpoint) if temp_setpoint and temp_setpoint.lower() != 'n/a' else str(temp_req)
                        req_match = re.search(r'-?\d+', req_str)
                        if req_match:
                            required_temp_num = float(req_match.group())
                    except Exception:
                        pass
                    
                    if reported_temp_num is not None and required_temp_num is not None:
                        if abs(reported_temp_num - required_temp_num) > 1:
                            is_out_of_range = True

                    # Log the temp check response
                    from database.models import TempCheckLog
                    temp_log = TempCheckLog(
                        load_id=load_id,
                        driver_response=temp_value,
                        forwarded_to_shipper=True,
                        forwarded_to_dispatcher=True
                    )
                    session.add(temp_log)
                    await session.commit()
                    
                    # Mark response received to avoid 15m timeout email
                    from services.temp_checker import mark_temp_responded
                    mark_temp_responded(load_id)

                    # Forward via email
                    try:
                        from services.twilio_sms import forward_temp_response_email
                        await forward_temp_response_email(
                            shipper_email=NOTIFY_EMAIL,
                            load_id=load_id,
                            driver_response=temp_value,
                            is_issue=is_issue,
                            is_out_of_range=is_out_of_range,
                            required_temp_num=required_temp_num,
                            reported_temp_num=reported_temp_num
                        )
                    except Exception as e:
                        log.error(f"Failed to forward temp response email: {e}")

                    if is_out_of_range:
                        emoji = "❌"
                    elif is_issue:
                        emoji = "⚠️"
                    else:
                        emoji = "✅"
                        
                    await message.add_reaction(emoji)
                    await message.reply(f"{emoji} **Temp response logged** — `{temp_value}`\nForwarded to dispatch via email.")

                elif action == "issue":
                    # Forward via email
                    try:
                        from services.twilio_sms import forward_issue_email
                        await forward_issue_email(
                            shipper_email=NOTIFY_EMAIL,
                            load_id=load_id,
                            driver_message=content
                        )
                    except Exception as e:
                        log.error(f"Failed to forward issue email: {e}")

                    await message.add_reaction("🚨")
                    await message.reply("🚨 **Issue reported.** Dispatcher has been notified via email.")

        else:
            # No load found for this thread — might be an old or manual thread
            log.warning(f"No load found for thread {message.channel.id}")

    @discord.app_commands.command(name="set-temp-interval", description="Change the interval for temperature checks on a load")
    @discord.app_commands.describe(
        minutes="New interval in minutes",
        load_id="Optional: The ID of the load. Automatically inferred if used in a load thread."
    )
    async def set_temp_interval(self, interaction: discord.Interaction, minutes: int, load_id: str = None):
        if minutes < 1:
            await interaction.response.send_message("❌ Interval must be at least 1 minute.", ephemeral=True)
            return

        if not load_id:
            load_record = await self._find_load_for_thread(str(interaction.channel.id))
            if load_record:
                load_id = load_record.load_id
            else:
                await interaction.response.send_message("❌ Could not determine the load for this thread. Please specify `load_id`.", ephemeral=True)
                return

        from services.temp_checker import update_temp_interval
        success = update_temp_interval(load_id, minutes)
        
        if success:
            await interaction.response.send_message(f"✅ Temp check interval for load **{load_id}** updated to **{minutes} minutes**.")
            
            # Notify in the driver thread if it exists
            load_record = None
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Load).where(Load.load_id == load_id))
                load_record = result.scalars().first()
                
            if load_record and load_record.discord_thread_id:
                thread = self.bot.get_channel(int(load_record.discord_thread_id))
                if thread:
                    await thread.send(f"⏱️ **Dispatcher Update:** Temperature check interval has been changed to every {minutes} minutes.")
        else:
            await interaction.response.send_message(f"❌ Could not find active temp checks for load **{load_id}**. Are they started?", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DriverPortal(bot))
