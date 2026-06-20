import discord
from discord.ext import commands
import logging
import re
import os
import json
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
from sqlalchemy.future import select
from google import genai

from database.models import AsyncSessionLocal, Load
from utils.invoice_generator import generate_invoice
from gmail_sender import send_invoice_email

log = logging.getLogger("broker_bot.driver_portal")

DRIVERS_CHANNEL_ID = 1517447020791468122
NOTIFY_EMAIL = os.getenv("GMAIL_USER", "cavemann177@gmail.com")

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

        # Extract text from attachments if present
        extracted_text = ""
        if message.attachments:
            try:
                attachment = message.attachments[0]
                file_bytes = await attachment.read()
                filename_lower = attachment.filename.lower()
                
                is_pdf = False
                if attachment.content_type and "application/pdf" in attachment.content_type:
                    is_pdf = True
                elif filename_lower.endswith('.pdf'):
                    is_pdf = True

                if is_pdf:
                    images = convert_from_bytes(file_bytes)
                    for img in images:
                        extracted_text += pytesseract.image_to_string(img) + "\n"
                elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    img = Image.open(io.BytesIO(file_bytes))
                    extracted_text = pytesseract.image_to_string(img)
            except Exception as e:
                log.error(f"Error reading attachment in driver thread: {e}")

        # If we found the load via thread, we already know the load_id
        if load_record:
            load_id = load_record.load_id

            # Use AI to determine intent
            prompt = f"""
Analyze this message from a truck driver in a dispatch thread for Load {load_id}.
Determine the driver's intent. Return a JSON object with key 'action'.
Possible actions:
- "loaded" — driver says they've picked up the freight
- "delivered" — driver says they've delivered / sending BOL/POD
- "temp_response" — driver is responding to a temperature check (extract temp in 'temp_value')
- "issue" — driver is reporting a problem
- "unknown" — not a dispatch-related message

Return JSON like: {{"action": "loaded"}} or {{"action": "temp_response", "temp_value": "-2°F"}}
Driver Message: "{content}"
Document Text: "{extracted_text[:3000]}"
"""
            try:
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt
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
                        except Exception as e:
                            log.error(f"Failed to save BOL: {e}")

                    # Automatically start Temp Checks if it's a reefer load
                    try:
                        import asyncio
                        from services.temp_checker import start_temp_checks
                        
                        # We can check if it's a reefer load by looking at ops intel
                        # For now, start it if the temp_check flag is not active
                        if not load.temp_check_active:
                            asyncio.create_task(start_temp_checks(load.load_id, getattr(load, 'driver_phone', None), interval_minutes=180))
                            load.temp_check_active = True
                            await session.commit()
                            log.info(f"Started temp checks for {load.load_id} after BOL receipt.")
                    except Exception as e:
                        log.error(f"Failed to start temp checks: {e}")

                elif action == "delivered":
                    load.status = 'Delivered'
                    await session.commit()
                    await message.add_reaction("✅")
                    try:
                        from services.temp_checker import stop_temp_checks
                        stop_temp_checks(load_id)
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
                            
                            # Send Email to cavemann (you)
                            await send_invoice_email(
                                to=NOTIFY_EMAIL,
                                load_id=load.load_id,
                                pdf_path=pdf_path,
                                bol_path=final_bol
                            )
                            load.status = 'Invoiced'
                            await session.commit()
                            await message.reply(f"💸 **Invoice generated and sent to {NOTIFY_EMAIL}!** (Status: Invoiced)")
                        except Exception as e:
                            log.error(f"Failed to auto-invoice: {e}", exc_info=True)
                            await message.reply(f"❌ Failed to generate/send invoice: {e}")

                elif action == "temp_response":
                    temp_value = data.get("temp_value", content)
                    is_issue = "issue" in content.lower()

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

                    # Forward via email
                    try:
                        from services.twilio_sms import forward_temp_response_email
                        await forward_temp_response_email(
                            shipper_email=NOTIFY_EMAIL,
                            load_id=load_id,
                            driver_response=temp_value,
                            is_issue=is_issue
                        )
                    except Exception as e:
                        log.error(f"Failed to forward temp response email: {e}")

                    emoji = "✅" if not is_issue else "⚠️"
                    await message.add_reaction(emoji)
                    await message.reply(f"{emoji} **Temp response logged** — `{temp_value}`\nForwarded to dispatch via email.")

                elif action == "issue":
                    await message.add_reaction("🚨")
                    await message.reply("🚨 **Issue reported.** Dispatcher has been notified.")
                    # Could add email notification here too

        else:
            # No load found for this thread — might be an old or manual thread
            log.warning(f"No load found for thread {message.channel.id}")

async def setup(bot: commands.Bot):
    await bot.add_cog(DriverPortal(bot))
