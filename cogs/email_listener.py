import discord
from discord.ext import commands, tasks
import logging
import imaplib
import email
import os
import re
import asyncio
import json
import io
import uuid
import mimetypes

from google import genai
from google.genai import types
from gmail_sender import send_broker_email
from database.models import AsyncSessionLocal, Load
from sheets_logger import append_load_log
from services.temp_checker import start_temp_checks

log = logging.getLogger("broker_bot.email_listener")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
DRIVER_TEST_PHONE = os.getenv("DRIVER_TEST_PHONE", "")

_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class EmailListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.allowed_channel = int(os.getenv("ALLOWED_CHANNEL_ID", "1512055979259334730"))
        creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            creds_file, scopes=_VERTEX_SCOPES
        )
        self.gemini_client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_PROJECT_ID"),
            location=os.getenv("GOOGLE_LOCATION"),
            credentials=creds,
        )
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        self.gmail_user = os.getenv("GMAIL_USER", "")
        self.gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "")
        
        if self.gmail_user and self.gmail_pass:
            log.info(f"Starting email listener for {self.gmail_user}...")
            self.check_emails.start()
        else:
            log.error("GMAIL_USER or GMAIL_APP_PASSWORD missing! Email listener won't start.")

    def cog_unload(self):
        self.check_emails.cancel()

    async def generate_negotiation_reply(self, broker_email_text: str) -> str:
        try:
            prompt = f"""You are a freight dispatcher negotiating a load. 
A broker just emailed you this:
"{broker_email_text}"

If they are offering a rate, negotiate for a slightly higher rate (e.g., $100-$200 more) to cover fuel costs, but remain very polite and professional. 
If they accepted your rate, say great, please send over the Rate Confirmation.
Do NOT use placeholders like [Your Name]. Sign off as "Mor Logistics Dispatch".
Return ONLY the email body you would reply with."""

            response = self.gemini_client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            log.error(f"Error generating negotiation: {e}")
            return ""

    async def extract_load_json(self, doc_parts: list[types.Part], user_text: str = "") -> dict:
        """Extract structured load data from RC attachments using Gemini AI natively."""
        try:
            prompt = f"""
You are the intelligence layer of a modern Transportation Management System (TMS).
Extract load details from the provided text and return ONLY valid JSON.
Do NOT include markdown formatting.

Ensure the JSON has this structure:
{{
  "load_information": {{
    "broker_load_number": "",
    "customer": "",
    "load_type": "",
    "revenue": "",
    "equipment_type": "",
    "commodity": "",
    "weight": "",
    "temperature_requirements": "",
    "assigned_driver": "",
    "assigned_truck": ""
  }},
  "stops": [
    {{
      "stop_type": "Pickup/Delivery",
      "company_name": "",
      "address": "",
      "city_state": "",
      "appointment_date": "",
      "appointment_time": "",
      "instructions": ""
    }}
  ],
  "reefer_operations": {{
    "temperature_setpoint": "",
    "continuous_mode": false,
    "pre_cool_required": false,
    "temperature_monitoring_required": false
  }},
  "financials": {{
    "total_revenue": ""
  }},
  "hard_copy_pod_required": false,
  "operational_intelligence": {{
    "workflow_state": "Pending",
    "dispatcher_summary": ""
  }}
}}

CRITICAL: Check if the document mentions requiring a "hard copy" of the POD/Proof of Delivery.
If yes, set "hard_copy_pod_required" to true.

Email Body Context:
{user_text}
"""
            contents = [prompt] + doc_parts
            response = await self.gemini_client.aio.models.generate_content(
                model=self.model,
                contents=contents
            )
            raw_json = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw_json)
        except Exception as e:
            log.error(f"Error extracting JSON with Gemini: {e}")
            return {}

    def _extract_attachments(self, msg):
        """Extract PDF/image attachments from an email message."""
        attachments = []
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                continue
            filename = part.get_filename()
            if filename:
                filename_lower = filename.lower()
                if filename_lower.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    file_bytes = part.get_payload(decode=True)
                    if file_bytes:
                        attachments.append((filename, file_bytes))
        return attachments

    @tasks.loop(seconds=30.0)
    async def check_emails(self):
        try:
            results = await asyncio.to_thread(self._sync_fetch_unread_emails)
            for sender, subject, body, attachments in results:
                log.info(f"New Unread Email from: {sender} | Subject: {subject} | Attachments: {len(attachments)}")
                
                # Extract clean email address from sender
                email_match = re.search(r'<([^>]+)>', sender)
                sender_email = email_match.group(1) if email_match else sender.strip()

                if sender_email.lower() == self.gmail_user.lower():
                    log.info(f"Skipping email from self ({sender_email}) to prevent loop.")
                    continue

                # ── If email has PDF/image attachments → treat as Rate Confirmation ──
                if attachments:
                    doc_parts = []
                    saved_documents = []
                    
                    for filename, file_bytes in attachments:
                        log.info(f"Processing attachment: {filename} from {sender_email}")
                        
                        # Guess mime type
                        mime_type, _ = mimetypes.guess_type(filename)
                        if not mime_type:
                            if filename.lower().endswith('.pdf'):
                                mime_type = 'application/pdf'
                            elif filename.lower().endswith('.png'):
                                mime_type = 'image/png'
                            elif filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                                mime_type = 'image/jpeg'
                            else:
                                mime_type = 'application/octet-stream'

                        # Create Gemini Part
                        doc_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                        doc_parts.append(doc_part)

                        # Save the attachment
                        file_ext = os.path.splitext(filename)[1]
                        saved_filename = f"{uuid.uuid4().hex}{file_ext}"
                        
                        # Ensure uploads directory exists
                        uploads_dir = os.path.join(os.getcwd(), "uploads")
                        os.makedirs(uploads_dir, exist_ok=True)
                        
                        saved_filepath = os.path.join(uploads_dir, saved_filename)
                        with open(saved_filepath, "wb") as f:
                            f.write(file_bytes)
                        saved_documents.append(f"{os.getenv('VITE_API_URL', 'http://127.0.0.1:20296')}/uploads/{saved_filename}")

                    if not doc_parts:
                        log.warning(f"No valid attachments found from {sender_email}")
                        continue

                    # Extract load data with AI using native file parts and email body
                    load_data = await self.extract_load_json(doc_parts, body)
                    if not load_data:
                        log.warning(f"Could not extract load data from attachments")
                        continue

                    document_url = saved_documents[0] if saved_documents else None

                    # Map to DB fields
                    load_info = load_data.get('load_information', {})
                    stops = load_data.get('stops', [])
                    financials = load_data.get('financials', {})
                    ops_intel = load_data.get('operational_intelligence', {})

                    pickup_stop = next((s for s in stops if 'Pickup' in s.get('stop_type', '')), stops[0] if stops else {})
                    delivery_stop = next((s for s in reversed(stops) if 'Delivery' in s.get('stop_type', '')), stops[-1] if len(stops) > 1 else {})

                    origin_str = pickup_stop.get('city_state') or 'Unknown'
                    dest_str = delivery_stop.get('city_state') or 'Unknown'
                    origin_dest = f"{origin_str} → {dest_str}"

                    pickup_date = pickup_stop.get('appointment_date') or 'Unknown'
                    rate_val = financials.get('total_revenue') or load_info.get('revenue', '0')
                    broker = load_info.get('customer') or 'Unknown'

                    load_id_val = load_info.get('broker_load_number')
                    if not load_id_val:
                        load_id_val = f"#L-{uuid.uuid4().hex[:4].upper()}"
                    elif not load_id_val.startswith('#'):
                        load_id_val = f"#{load_id_val}"

                    hard_copy = load_data.get('hard_copy_pod_required', False)

                    # DB save is handled by LoadConfirmView on button click
                    # Just prepare the data for Discord confirmation

                    # Post confirmation to Discord load-creation channel
                    try:
                        from cogs.document_ocr import LoadConfirmView, score_and_sort_vehicles
                        from database.models import Vehicle, AsyncSessionLocal
                        from sqlalchemy.future import select
                        
                        # Fetch active vehicles for the dropdown
                        async with AsyncSessionLocal() as session:
                            result = await session.execute(select(Vehicle))
                            vehicles = result.scalars().all()
                        sorted_vehicles, _ = await score_and_sort_vehicles(vehicles)
                        
                        confirmation_channel = None
                        if self.allowed_channel != 0:
                            confirmation_channel = self.bot.get_channel(self.allowed_channel)
                        
                        # Fallback to the original hardcoded channel ID
                        if not confirmation_channel:
                            confirmation_channel = self.bot.get_channel(1512055979259334730)
                            
                        # Final fallback: just use the very first text channel the bot can see
                        if not confirmation_channel:
                            for guild in self.bot.guilds:
                                for channel in guild.text_channels:
                                    if channel.permissions_for(guild.me).send_messages:
                                        confirmation_channel = channel
                                        break
                                if confirmation_channel:
                                    break
                        
                        if confirmation_channel:
                            commodity = load_info.get("commodity", "Unknown")
                            weight = load_info.get("weight", "Unknown")
                            equipment = load_info.get("equipment_type", "Unknown")
                            temp = load_info.get("temperature_requirements", "N/A")
                            summary = ops_intel.get('dispatcher_summary', 'No summary generated.')
                            
                            embed = discord.Embed(
                                title=f"📧 New RC from Email — {load_id_val}",
                                description=f"Rate Confirmation received from **{sender_email}**",
                                color=0xf59e0b
                            )
                            embed.add_field(name="📍 Route", value=origin_dest, inline=False)
                            embed.add_field(name="💵 Rate", value=f"${rate_val}", inline=True)
                            embed.add_field(name="📦 Commodity", value=f"{commodity} ({weight})", inline=True)
                            embed.add_field(name="🚛 Equipment", value=equipment, inline=True)
                            embed.add_field(name="🌡️ Temp", value=temp, inline=True)
                            embed.add_field(name="🧠 Summary", value=summary, inline=False)
                            embed.set_footer(text="Awaiting Confirmation — from email")
                            
                            view = LoadConfirmView(
                                bot=self.bot,
                                load_data=load_data,
                                document_url=document_url,
                                load_id_val=load_id_val,
                                origin_dest=origin_dest,
                                pickup_date=pickup_date,
                                rate_val=rate_val,
                                ops_intel=ops_intel,
                                broker=broker,
                                original_message=None,
                                active_vehicles=sorted_vehicles
                            )
                            
                            await confirmation_channel.send(
                                f"📨 New Rate Confirmation from **{sender_email}** ({subject if subject else 'No Subject'})",
                                embed=embed,
                                view=view
                            )
                            log.info(f"Posted email RC confirmation to Discord for {load_id_val}")
                        else:
                            log.error(f"Could not find load-creation channel {LOAD_CREATION_CHANNEL_ID}")
                    except Exception as e:
                        log.error(f"Failed to post email RC to Discord: {e}", exc_info=True)

                    # Log to sheets
                    try:
                        await append_load_log(
                            load_id=load_id_val,
                            broker=broker,
                            origin_dest=origin_dest,
                            pickup_date=pickup_date,
                            rate=str(rate_val)
                        )
                    except Exception as sheet_err:
                        log.error(f"Failed to log to sheets: {sheet_err}")

                    log.info(
                        f"✅ RC processed from email | Load: {load_id_val} | "
                        f"Shipper email: {sender_email} | Hard copy POD: {hard_copy}"
                    )

                else:
                    # ── No attachments → regular negotiation reply ──
                    # DISABLED per user request: only send temp and eta updates
                    # reply_body = await self.generate_negotiation_reply(body)
                    # if reply_body:
                    #     log.info(f"Auto-negotiating with {sender_email}...")
                    #     await send_broker_email(sender_email, "Broker", subject.replace("Re: ", ""), reply_body)
                    pass

        except Exception as e:
            log.error(f"Failed to check emails: {e}", exc_info=True)

    def _sync_fetch_unread_emails(self):
        """Fetch unread emails with body text AND attachments."""
        results = []
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.gmail_user, self.gmail_pass)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            
            if status == "OK" and messages[0]:
                for num in messages[0].split():
                    status, data = mail.fetch(num, "(RFC822)")
                    if status == "OK":
                        raw_email = data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        sender = msg.get("From")
                        subject = msg.get("Subject")
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body += payload.decode(errors='ignore')
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors='ignore')
                        
                        # Also extract attachments
                        attachments = self._extract_attachments(msg)
                        
                        results.append((sender, subject, body, attachments))
        except Exception as e:
            log.error(f"IMAP fetch error: {e}")

        return results

    @discord.app_commands.command(name="force_email_check", description="Force check the inbox for new Rate Confirmations.")
    async def force_email_check(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            results = await asyncio.to_thread(self._sync_fetch_unread_emails)
            if not results:
                await interaction.followup.send("📭 No unread emails found in the inbox.")
                return
            
            summary = []
            for sender, subject, body, attachments in results:
                summary.append(f"- From: **{sender}** | Subject: *{subject}* | Attachments: {len(attachments)}")
                
            msg = "📬 **Force Check Found Emails:**\n" + "\n".join(summary) + "\n\n(Processing them now...)"
            await interaction.followup.send(msg)
            
            # Now trigger the background loop once manually to process them
            await self.check_emails()
        except Exception as e:
            await interaction.followup.send(f"❌ Error checking emails: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(EmailListener(bot))
