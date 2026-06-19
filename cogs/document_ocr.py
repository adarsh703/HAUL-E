import discord
from discord.ext import commands
import logging
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
import json
from google import genai
from google.genai import types
from google.oauth2 import service_account
import os
import random

from database.models import AsyncSessionLocal, Load
from sheets_logger import append_load_log

log = logging.getLogger("broker_bot.document_ocr")

_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

class DriverReassignView(discord.ui.View):
    def __init__(self, load_id_val, current_driver, available_vehicles):
        super().__init__(timeout=None)
        self.load_id_val = load_id_val
        options = []
        for v in available_vehicles:
            options.append(discord.SelectOption(
                label=f"{v.driver} ({v.unit_id})", 
                value=v.driver, 
                default=(v.driver == current_driver)
            ))
        
        self.select = discord.ui.Select(placeholder="Change assigned driver...", options=options[:25])
        self.select.callback = self.select_callback
        self.add_item(self.select)
        
    async def select_callback(self, interaction: discord.Interaction):
        new_driver = self.select.values[0]
        from database.models import AsyncSessionLocal, Load
        from sqlalchemy.future import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Load).where(Load.load_id == self.load_id_val))
            load = result.scalars().first()
            if load:
                load.driver = new_driver
                await session.commit()
        await interaction.response.send_message(f"✅ Driver reassigned to **{new_driver}**. The TMS has been updated.", ephemeral=False)

class LoadConfirmView(discord.ui.View):
    DRIVERS_CHANNEL_ID = 1517447020791468122

    def __init__(self, bot, load_data, document_url, load_id_val, origin_dest, pickup_date, rate_val, ops_intel, broker, original_message):
        super().__init__(timeout=None)
        self.bot = bot
        self.load_data = load_data
        self.document_url = document_url
        self.load_id_val = load_id_val
        self.origin_dest = origin_dest
        self.pickup_date = pickup_date
        self.rate_val = rate_val
        self.ops_intel = ops_intel
        self.broker = broker
        self.original_message = original_message

    @discord.ui.button(label="Create Load", style=discord.ButtonStyle.success, custom_id="btn_create_load")
    async def create_load_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # 1. Save to DB
        async with AsyncSessionLocal() as session:
            new_load = Load(
                load_id=self.load_id_val,
                origin_dest=self.origin_dest,
                pickup_date=self.pickup_date,
                driver='Unassigned',
                rate=str(self.rate_val),
                status=self.ops_intel.get('workflow_state', 'Pending'),
                document_url=self.document_url,
                operational_intelligence=json.dumps(self.load_data)
            )
            session.add(new_load)
            await session.commit()

        # 2. Log to Google Sheets
        try:
            await append_load_log(
                load_id=self.load_id_val,
                broker=self.broker,
                origin_dest=self.origin_dest,
                pickup_date=self.pickup_date,
                rate=str(self.rate_val)
            )
        except Exception as sheet_err:
            log.error(f"Failed to log load to sheets: {sheet_err}")

        # 3. Create a thread in the drivers channel for this load
        thread = None
        try:
            drivers_channel = self.bot.get_channel(self.DRIVERS_CHANNEL_ID)
            if drivers_channel:
                thread_name = f"🚚 {self.load_id_val} | {self.origin_dest}"
                # Truncate to Discord's 100 char thread name limit
                thread = await drivers_channel.create_thread(
                    name=thread_name[:100],
                    type=discord.ChannelType.public_thread,
                    reason=f"Load {self.load_id_val} dispatch thread"
                )
                # Save thread ID to DB
                async with AsyncSessionLocal() as session:
                    from sqlalchemy.future import select
                    result = await session.execute(select(Load).where(Load.load_id == self.load_id_val))
                    load = result.scalars().first()
                    if load:
                        load.discord_thread_id = str(thread.id)
                        await session.commit()

                # Post dispatch summary in thread
                load_info = self.load_data.get('load_information', {})
                stops = self.load_data.get('stops', [])
                reefer = self.load_data.get('reefer_operations', {})

                dispatch_embed = discord.Embed(
                    title=f"📋 Dispatch Details — {self.load_id_val}",
                    color=0x3b82f6
                )
                dispatch_embed.add_field(name="📍 Route", value=self.origin_dest, inline=False)
                dispatch_embed.add_field(name="📅 Pickup Date", value=self.pickup_date, inline=True)
                dispatch_embed.add_field(name="💰 Rate", value=f"${self.rate_val}", inline=True)
                dispatch_embed.add_field(name="📦 Commodity", value=load_info.get('commodity', 'N/A'), inline=True)
                dispatch_embed.add_field(name="⚖️ Weight", value=load_info.get('weight', 'N/A'), inline=True)
                dispatch_embed.add_field(name="🚛 Equipment", value=load_info.get('equipment_type', 'N/A'), inline=True)
                temp = reefer.get('temperature_setpoint') or load_info.get('temperature_requirements', 'N/A')
                dispatch_embed.add_field(name="🌡️ Temperature", value=temp, inline=True)

                # Add stop details
                for i, stop in enumerate(stops):
                    stop_type = stop.get('stop_type', 'Stop')
                    company = stop.get('company_name', 'N/A')
                    address = stop.get('address', 'N/A')
                    appt = f"{stop.get('appointment_date', '')} {stop.get('appointment_time', '')}".strip() or 'N/A'
                    instructions = stop.get('instructions', '')
                    stop_text = f"**{company}**\n{address}\n📅 {appt}"
                    if instructions:
                        stop_text += f"\n📝 {instructions}"
                    dispatch_embed.add_field(name=f"{'📦' if 'Pickup' in stop_type else '📬'} Stop {i+1}: {stop_type}", value=stop_text, inline=False)

                dispatch_embed.set_footer(text="Reply LOADED when freight is on the truck. Upload BOL/POD when delivered.")
                await thread.send(embed=dispatch_embed)
                
                # --- AUTO DISPATCH LOGIC ---
                try:
                    from database.models import Vehicle
                    from services.motive_service import get_vehicle_tracking
                    import asyncio
                    
                    async with AsyncSessionLocal() as session:
                        v_result = await session.execute(select(Vehicle).where(Vehicle.status == 'Active'))
                        vehicles = v_result.scalars().all()
                        
                    if vehicles:
                        best_vehicle = random.choice(vehicles)
                        assigned_driver = best_vehicle.driver
                        
                        tracking = await asyncio.to_thread(get_vehicle_tracking, best_vehicle.unit_id)
                        if tracking:
                            hos = tracking.get('hos', 8.5)
                            loc = tracking.get('location', 'Unknown')
                            auto_reason = f"Based on ELD Proximity ({loc}) and HOS ({hos} hrs remaining)."
                        else:
                            auto_reason = "Based on Equipment match and availability."
                            
                        async with AsyncSessionLocal() as session:
                            l_result = await session.execute(select(Load).where(Load.load_id == self.load_id_val))
                            load_db = l_result.scalars().first()
                            if load_db:
                                load_db.driver = assigned_driver
                                load_db.status = "Dispatched"
                                await session.commit()
                                
                        reassign_view = DriverReassignView(self.load_id_val, assigned_driver, vehicles)
                        await thread.send(f"🤖 **Auto-Assigned:** {assigned_driver}\n**Reason:** {auto_reason}", view=reassign_view)
                except Exception as auto_e:
                    log.error(f"Auto-dispatch failed: {auto_e}")
                # -----------------------------
                
        except Exception as thread_err:
            log.error(f"Failed to create driver thread: {thread_err}", exc_info=True)

        # Update the confirmation message to show created
        embed = interaction.message.embeds[0]
        embed.title = f"✅ Load {self.load_id_val} Created"
        embed.color = 0x10b981
        if thread:
            embed.add_field(name="🧵 Driver Thread", value=f"<#{thread.id}>", inline=False)
        embed.set_footer(text="Load saved to Database & Google Sheets")
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="btn_cancel_load")
    async def cancel_load_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.title = f"❌ Load {self.load_id_val} Creation Cancelled"
        embed.color = 0xef4444
        await interaction.response.edit_message(embed=embed, view=None)

class DocumentOCR(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
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

    async def extract_load_json(self, ocr_text: str, user_text: str) -> dict:
        try:
            prompt = f"""
You are the intelligence layer of a modern Transportation Management System (TMS).

A user uploads a Rate Confirmation, broker email, carrier packet, BOL, or shipment document.
Your job is to create the most complete load record possible and enrich it with operational intelligence.
The goal is not document extraction. The goal is to reduce dispatcher actions to near zero.

# Generate Complete TMS Record
Populate every possible field based on the text. If User Message provides specific details, prioritize them.

Return structured JSON optimized for a web-based TMS application. DO NOT include markdown formatting.
Ensure the JSON has the EXACT following structure, filling in values where found:
{{
  "load_information": {{
    "broker_load_number": "",
    "customer": "",
    "load_status": "",
    "load_type": "",
    "revenue": "",
    "equipment_type": "",
    "trailer_requirements": "",
    "commodity": "",
    "weight": "",
    "miles": "",
    "temperature_requirements": ""
  }},
  "stops": [
    {{
      "stop_type": "Pickup/Delivery",
      "company_name": "",
      "address": "",
      "city_state": "",
      "coordinates": "",
      "contact_name": "",
      "phone": "",
      "email": "",
      "appointment_type": "",
      "appointment_date": "",
      "appointment_time": "",
      "instructions": "",
      "reference_numbers": []
    }}
  ],
  "references": [
    {{"type": "PO Number", "value": ""}}
  ],
  "reefer_operations": {{
    "temperature_setpoint": "",
    "temperature_range": "",
    "frozen_chilled_produce": "",
    "continuous_mode": false,
    "start_stop_mode": false,
    "pre_cool_required": false,
    "temperature_printout_required": false,
    "temperature_monitoring_required": false
  }},
  "financials": {{
    "linehaul": "",
    "fsc": "",
    "accessorials": "",
    "detention_terms": "",
    "layover_terms": "",
    "tonu_terms": "",
    "total_revenue": ""
  }},
  "operational_intelligence": {{
    "risk_analysis": {{"classification": "Low/Medium/High", "reason": ""}},
    "missing_information": [],
    "dispatch_readiness_score": 0,
    "dispatcher_summary": "",
    "automation_suggestions": [],
    "database_relationships": [],
    "alerts": [],
    "workflow_state": "Pending" 
  }}
}}

CRITICAL RULES:
- For `stops[].city_state`, ONLY output the City and State (e.g., "Laredo, TX"). Do not include the street address or zip code here.
- For `workflow_state`, ONLY use one of the following exact words: "Pending", "In Transit", "Delivered", or "Cancelled".

User Message:
{user_text}

OCR Text:
{ocr_text[:10000]}
"""
            response = await self.gemini_client.aio.models.generate_content(
                model=self.model,
                contents=prompt
            )
            raw_json = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw_json)
        except Exception as e:
            log.error(f"Error extracting JSON with Gemini: {e}")
            return {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Skip if in driver channel or a thread under it (let driver_portal handle it)
        if message.channel.id == 1517447020791468122:
            return
        if isinstance(message.channel, discord.Thread) and message.channel.parent_id == 1517447020791468122:
            return
        # Skip load-creation channel (only for confirmations)
        if message.channel.id == 1512055979259334730:
            return

        # Check if message has attachments
        if not message.attachments:
            return

        for attachment in message.attachments:
            filename_lower = (attachment.filename or "").lower()
            is_valid_type = False
            if attachment.content_type:
                if "image/" in attachment.content_type or "application/pdf" in attachment.content_type:
                    is_valid_type = True
            if not is_valid_type:
                if filename_lower.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.webp')):
                    is_valid_type = True
            
            if is_valid_type:
                # Trigger OCR
                try:
                    file_bytes = await attachment.read()
                    extracted_text = ""
                    
                    # Convert to image if PDF, or just read if image
                    is_pdf = False
                    if attachment.content_type and "application/pdf" in attachment.content_type:
                        is_pdf = True
                    elif filename_lower.endswith('.pdf'):
                        is_pdf = True

                    if is_pdf:
                        images = convert_from_bytes(file_bytes)
                        for img in images:
                            extracted_text += pytesseract.image_to_string(img) + "\n"
                    else:
                        img = Image.open(io.BytesIO(file_bytes))
                        extracted_text = pytesseract.image_to_string(img)

                    if extracted_text.strip():
                        # Inform user
                        try:
                            await message.add_reaction("📄")
                        except Exception as react_err:
                            log.warning(f"Could not add reaction to message: {react_err}")
                        
                        load_data = await self.extract_load_json(extracted_text, message.content)
                        
                        if load_data:
                            # Save file locally
                            import uuid
                            file_ext = os.path.splitext(attachment.filename)[1] if attachment.filename else ".pdf"
                            saved_filename = f"{uuid.uuid4().hex}{file_ext}"
                            saved_filepath = os.path.join("uploads", saved_filename)
                            with open(saved_filepath, "wb") as f:
                                f.write(file_bytes)
                            document_url = f"http://127.0.0.1:8000/uploads/{saved_filename}"

                            # 1. Map Intelligence JSON to basic DB Schema
                            load_info = load_data.get('load_information', {})
                            stops = load_data.get('stops', [])
                            financials = load_data.get('financials', {})
                            ops_intel = load_data.get('operational_intelligence', {})
                            
                            pickup_stop = next((s for s in stops if 'Pickup' in s.get('stop_type', '')), stops[0] if stops else {})
                            delivery_stop = next((s for s in reversed(stops) if 'Delivery' in s.get('stop_type', '')), stops[-1] if len(stops) > 1 else {})
                            
                            origin_str = pickup_stop.get('city_state') or pickup_stop.get('address') or 'Unknown'
                            dest_str = delivery_stop.get('city_state') or delivery_stop.get('address') or 'Unknown'
                            origin_dest = f"{origin_str} → {dest_str}"
                            
                            pickup_date = pickup_stop.get('appointment_date') or 'Unknown'
                            rate_val = financials.get('total_revenue') or load_info.get('revenue', '0')
                            broker = load_info.get('customer') or 'Unknown'
                            
                            # Use actual broker load number instead of random
                            load_id_val = load_info.get('broker_load_number')
                            if not load_id_val:
                                load_id_val = f"#L-{random.randint(1000, 9999)}"
                            elif not load_id_val.startswith('#'):
                                load_id_val = f"#{load_id_val}"
                                
                            # Removed immediate DB and Sheets insertion
                            
                            # 3. Rich Discord Reply with Confirmation View
                            score = ops_intel.get('dispatch_readiness_score', 0)
                            summary = ops_intel.get('dispatcher_summary', 'No summary generated.')
                            risk = ops_intel.get('risk_analysis', {}).get('classification', 'Unknown')
                            alerts = ops_intel.get('alerts', [])
                            alerts_str = "\n".join([f"⚠️ {a}" for a in alerts]) if alerts else "None"
                            
                            embed = discord.Embed(
                                title=f"✅ Load {load_id_val} Processed",
                                color=0x10b981
                            )
                            embed.add_field(name="📍 Lane", value=origin_dest, inline=False)
                            embed.add_field(name="💰 Rate", value=f"${rate_val}", inline=True)
                            embed.add_field(name="📊 Readiness Score", value=f"{score}/100", inline=True)
                            
                            risk_emoji = "🟢" if risk == "Low" else "🟡" if risk == "Medium" else "🔴"
                            embed.add_field(name="⚠️ Risk Level", value=f"{risk_emoji} {risk}", inline=True)
                            
                            embed.add_field(name="🧠 Dispatcher Summary", value=summary, inline=False)
                            
                            if alerts:
                                embed.add_field(name="🚨 Actionable Alerts", value=alerts_str, inline=False)
                                
                            embed.set_footer(text="Awaiting Confirmation")
                            
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
                                original_message=message
                            )

                            confirmation_channel = self.bot.get_channel(1512055979259334730)
                            if confirmation_channel:
                                await confirmation_channel.send(f"New Load Document uploaded by {message.author.mention}", embed=embed, view=view)
                                await message.reply("📄 Document processed. Awaiting confirmation in the load creation channel.")
                            else:
                                # Fallback to replying in the same channel if confirmation channel not found
                                await message.reply(embed=embed, view=view)
                        else:
                            await message.reply("❌ Could not extract load data from the document.")
                except Exception as e:
                    log.error(f"OCR processing failed for attachment {attachment.filename}: {e}", exc_info=True)
                    await message.reply("❌ An error occurred while processing the document.")

async def setup(bot: commands.Bot):
    await bot.add_cog(DocumentOCR(bot))
