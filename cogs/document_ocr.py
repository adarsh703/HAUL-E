import discord
from discord.ext import commands
import logging
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

async def score_and_sort_vehicles(vehicles):
    from services.motive_service import get_vehicle_tracking
    import asyncio
    
    valid_vehicles = [v for v in vehicles if v.driver and v.driver.lower() != 'unassigned']
    unassigned_vehicles = [v for v in vehicles if not v.driver or v.driver.lower() == 'unassigned']
    
    async def score_vehicle(v):
        score = 100
        tracking = await asyncio.to_thread(get_vehicle_tracking, v.unit_id)
        reason = "Based on availability (Motive tracking skipped)."
        if tracking:
            hos = tracking.get('hos', 0)
            if hos < 3:
                score -= 100
            score += hos * 5
            loc = tracking.get('location', 'Unknown')
            reason = f"Based on ELD proximity ({loc}) and HOS ({hos} hrs)."
        else:
            score -= 50
        return (score, v, reason)

    scored_vehicles = await asyncio.gather(*(score_vehicle(v) for v in valid_vehicles))
    scored_vehicles = list(scored_vehicles)
    scored_vehicles.sort(key=lambda x: x[0], reverse=True)
    
    sorted_vehicles = [sv[1] for sv in scored_vehicles] + unassigned_vehicles
    reasons = {sv[1].unit_id: sv[2] for sv in scored_vehicles}
    return sorted_vehicles, reasons

class LoadConfirmView(discord.ui.View):
    DRIVERS_CHANNEL_ID = 1517447020791468122

    def __init__(self, bot, load_data, document_url, load_id_val, origin_dest, pickup_date, rate_val, ops_intel, broker, original_message, active_vehicles):
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
        self.active_vehicles = active_vehicles
        self.selected_driver = "Unassigned"
        self.selected_phone = None

        if active_vehicles:
            best_vehicle = active_vehicles[0]
            self.selected_driver = best_vehicle.driver
            self.selected_phone = getattr(best_vehicle, 'phone', None)

            options = []
            for v in active_vehicles:
                label = f"{v.driver} (Truck {v.unit_id})"
                desc = "Recommended Auto-Assign" if v == best_vehicle else None
                options.append(discord.SelectOption(label=label, value=str(v.unit_id), description=desc))

            self.driver_select = discord.ui.Select(
                placeholder=f"Auto-assigning to {best_vehicle.driver}...",
                options=options,
                min_values=1,
                max_values=1,
                row=0
            )
            self.driver_select.callback = self.driver_callback
            self.add_item(self.driver_select)

    async def driver_callback(self, interaction: discord.Interaction):
        selected_unit_id = self.driver_select.values[0]
        for v in self.active_vehicles:
            if str(v.unit_id) == selected_unit_id:
                self.selected_driver = v.driver
                self.selected_phone = getattr(v, 'phone', None)
                break
                
        # Update the embed to visually reflect the new choice
        embed = interaction.message.embeds[0]
        for idx, field in enumerate(embed.fields):
            if field.name == "🤖 Predicted Driver":
                embed.set_field_at(idx, name="🤖 Predicted Driver", value=f"**{self.selected_driver}** (Select below to change)", inline=False)
                break
                
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Create Load", style=discord.ButtonStyle.success, custom_id="btn_create_load", row=1)
    async def create_load_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # 1. Save to DB with Auto-Assign
        async with AsyncSessionLocal() as session:
            assigned_driver = self.selected_driver
            assigned_phone = self.selected_phone
            assigned_status = 'Assigned' if self.selected_driver != 'Unassigned' else 'Unassigned'
            
            new_load = Load(
                load_id=self.load_id_val,
                origin_dest=self.origin_dest,
                pickup_date=self.pickup_date,
                driver=assigned_driver,
                driver_phone=assigned_phone,
                rate=str(self.rate_val),
                status=assigned_status,
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

                # Construct Driver Dispatch Embed
                driver_name = assigned_driver if assigned_driver else "Unassigned"
                truck_number = "Unknown"
                
                if assigned_driver and assigned_driver != "Unassigned":
                    from database.models import Vehicle
                    from sqlalchemy.future import select
                    async with AsyncSessionLocal() as session:
                        v_result = await session.execute(select(Vehicle).where(Vehicle.driver == assigned_driver))
                        vehicle = v_result.scalars().first()
                        if vehicle:
                            truck_number = vehicle.unit_id

                driver_embed = discord.Embed(
                    title=f"🚚 NEW DISPATCH: Load {self.load_id_val}",
                    color=0x2b7de9,
                    description=f"**Driver:** {driver_name.upper()}  |  **Truck:** {truck_number}"
                )
                
                stops = self.load_data.get('stops', [])
                for i, stop in enumerate(stops):
                    stop_type = stop.get('stop_type', 'Stop')
                    company = stop.get('company_name', 'N/A')
                    
                    addr = stop.get('address', '')
                    city = stop.get('city_state', '')
                    address_full = f"{addr}, {city}".strip(', ') if addr or city else 'N/A'
                    
                    phone = stop.get('phone', 'N/A')
                    appt = f"{stop.get('appointment_date', '')} {stop.get('appointment_time', '')}".strip() or 'N/A'
                    instructions = stop.get('instructions', 'None')
                    
                    refs = stop.get('reference_numbers', [])
                    ref_str = ", ".join(refs) if refs else "N/A"
                    
                    emoji = "📍" if "Pick" in stop_type else "🏁"
                    num_label = "PU Number" if "Pick" in stop_type else "DO Number"
                    
                    stop_lines = [
                        f"**Name:** {company}",
                        f"**Address:** {address_full}",
                        f"**Phone:** {phone}",
                        f"**{num_label}:** {ref_str}",
                        f"**Appt:** {appt}",
                    ]
                    if instructions and instructions.lower() != 'none':
                        stop_lines.append(f"*Note: {instructions}*")
                    
                    stop_value = "\n".join(stop_lines)
                    # Truncate to Discord's 1024 char field limit
                    if len(stop_value) > 1024:
                        stop_value = stop_value[:1021] + "..."
                    driver_embed.add_field(
                        name=f"{emoji} STOP {i+1}: {stop_type.upper()}",
                        value=stop_value,
                        inline=False
                    )
                    
                ops_intel = self.load_data.get('operational_intelligence', {})
                alerts = ops_intel.get('alerts', [])
                
                # --- Dedicated Temperature Requirements Field ---
                load_info = self.load_data.get('load_information', {})
                reefer = self.load_data.get('reefer_operations', {})
                temp_setpoint = reefer.get('temperature_setpoint') or ''
                temp_range = reefer.get('temperature_range') or ''
                temp_general = load_info.get('temperature_requirements') or ''
                continuous = reefer.get('continuous_mode', False)
                precool = reefer.get('pre_cool_required', False)
                
                temp_lines = []
                if temp_setpoint and temp_setpoint.lower() != 'n/a':
                    temp_lines.append(f"🎯 **Setpoint:** {temp_setpoint}")
                if temp_range and temp_range.lower() != 'n/a':
                    temp_lines.append(f"📏 **Range:** {temp_range}")
                if temp_general and temp_general.lower() != 'n/a' and temp_general != temp_setpoint:
                    temp_lines.append(f"📋 **Requirement:** {temp_general}")
                if continuous:
                    temp_lines.append("🔄 **Mode:** Continuous")
                if precool:
                    temp_lines.append("❄️ **Pre-Cool:** Required")
                
                if temp_lines:
                    driver_embed.add_field(
                        name="🌡️ TEMPERATURE REQUIREMENTS",
                        value="\n".join(temp_lines),
                        inline=False
                    )
                    # Remove any temp-related alerts to avoid duplication
                    alerts = [a for a in alerts if 'temperature' not in a.lower() and 'temp ' not in a.lower() and 'reefer' not in a.lower()]
                
                if alerts:
                    # Split into multiple fields if needed (1024 char limit per field)
                    chunk = ""
                    chunk_idx = 1
                    for a in alerts:
                        alert_str = f"⚠️ {a}\n"
                        if len(chunk) + len(alert_str) > 1024:
                            name = "🚨 Extra Requirements" if chunk_idx == 1 else f"🚨 Extra Requirements (Cont.)"
                            driver_embed.add_field(name=name, value=chunk.strip(), inline=False)
                            chunk = alert_str
                            chunk_idx += 1
                        else:
                            chunk += alert_str
                    if chunk:
                        name = "🚨 Extra Requirements" if chunk_idx == 1 else f"🚨 Extra Requirements (Cont.)"
                        driver_embed.add_field(name=name, value=chunk.strip(), inline=False)
                
                driver_embed.set_footer(text="📄 Send BOL when loaded  •  📄 Send POD when delivered")
                
                try:
                    await thread.send(embed=driver_embed)
                except Exception as send_err:
                    log.error(f"Failed to send driver embed in thread {thread.id}: {send_err}", exc_info=True)
                    # Fallback: send as plain text if embed somehow fails
                    fallback = f"🚚 **DISPATCH: Load {self.load_id_val}**\n**Driver:** {driver_name} | **Truck:** {truck_number}\n📄 Send BOL when loaded • Send POD when delivered"
                    await thread.send(fallback[:2000])
                
                # --- AUTO DISPATCH LOGIC ---
                if self.selected_driver == 'Unassigned':
                    try:
                        from database.models import Vehicle
                        from services.motive_service import get_vehicle_tracking
                        import asyncio
                        
                        async with AsyncSessionLocal() as session:
                            v_result = await session.execute(select(Vehicle).where(Vehicle.status == 'Active'))
                            vehicles = v_result.scalars().all()
                            
                        valid_vehicles = [v for v in vehicles if v.driver and v.driver.lower() != 'unassigned']
                        
                        best_vehicle = None
                        best_score = -1
                        auto_reason = ""
                        
                        for v in valid_vehicles:
                            score = 100
                            # Real Motive API check
                            tracking = await asyncio.to_thread(get_vehicle_tracking, v.unit_id)
                            
                            if tracking:
                                hos = tracking.get('hos', 0)
                                if hos < 3:
                                    continue # Skip drivers with low HOS
                                score += hos * 5 # Prioritize drivers with more HOS
                            else:
                                score -= 50 # Penalize if no tracking available
                                
                            if score > best_score:
                                best_score = score
                                best_vehicle = v
                                if tracking:
                                    loc = tracking.get('location', 'Unknown')
                                    hos = tracking.get('hos', 8.5)
                                    auto_reason = f"Based on ELD tracking ({loc}) and HOS ({hos} hrs)."
                                else:
                                    auto_reason = "Based on driver availability (Motive API unavailable)."
                                    
                        if best_vehicle:
                            assigned_driver = best_vehicle.driver
                                
                            async with AsyncSessionLocal() as session:
                                l_result = await session.execute(select(Load).where(Load.load_id == self.load_id_val))
                                load_db = l_result.scalars().first()
                                if load_db:
                                    load_db.driver = assigned_driver
                                    load_db.status = "Assigned"
                                    self.selected_driver = assigned_driver # Update state
                                    await session.commit()
                                    
                            reassign_view = DriverReassignView(self.load_id_val, assigned_driver, vehicles)
                            await thread.send(f"🤖 **Auto-Assigned:** {assigned_driver}\n**Reason:** {auto_reason}", view=reassign_view)
                    except Exception as auto_e:
                        log.error(f"Auto-dispatch failed: {auto_e}")
                    
                # --- AUTOMATED TRACKING ---
                try:
                    from services.twilio_sms import forward_silent_location_email
                    import asyncio
                    
                    # Start initial ETA/Location update right now for demonstration
                    shipper_email = os.getenv("GMAIL_USER", "cavemann177@gmail.com")
                    asyncio.create_task(forward_silent_location_email(shipper_email, self.load_id_val))
                    
                except Exception as tracker_e:
                    log.error(f"Failed to start auto-tracking: {tracker_e}")
                # -----------------------------
        except Exception as thread_err:
            log.error(f"Failed to create driver thread: {thread_err}", exc_info=True)

        # Update the confirmation message to show created
        embed = interaction.message.embeds[0]
        embed.title = f"✅ Load {self.load_id_val} Created"
        embed.color = 0x10b981
        if thread:
            embed.add_field(name="🧵 Driver Thread", value=f"<#{thread.id}>", inline=False)
            
        for idx, field in enumerate(embed.fields):
            if field.name == "🤖 Predicted Driver":
                embed.set_field_at(idx, name="🤖 Assigned Driver", value=f"**{self.selected_driver}**", inline=False)
                break
                
        embed.set_footer(text="Load saved to Database & Google Sheets")
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="btn_cancel_load", row=1)
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

    async def extract_load_json(self, file_bytes: bytes, mime_type: str, user_text: str) -> dict:
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
    "temperature_requirements": "",
    "broker_phone": "",
    "broker_email": ""
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
- For `operational_intelligence.alerts`, extract a comprehensive list of all penalties, fines, temperature rules, and equipment requirements. BUT you must synthesize them into clear, concise, actionable points. **CRITICAL FORMAT:** Each alert MUST be formatted with a short bolded heading, followed by a colon and the detail. Example: "**Temperature Control**: Maintain continuous reefer operation at 35F." Do not just copy/paste raw text; make it highly readable for a driver.

User Message:
{user_text}

Extract data directly from the attached document.
"""
            document_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            response = await self.gemini_client.aio.models.generate_content(
                model=self.model,
                contents=[document_part, prompt]
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
        if isinstance(message.channel, discord.Thread) and getattr(message.channel, 'parent_id', None) == 1517447020791468122:
            return

        # No other hardcoded channel skips. If a user uploads a valid document, we process it.

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
                    
                    # Inform user
                    try:
                        await message.add_reaction("📄")
                    except Exception as react_err:
                        log.warning(f"Could not add reaction to message: {react_err}")
                        
                    mime_type = attachment.content_type
                    if not mime_type:
                        if filename_lower.endswith('.pdf'):
                            mime_type = 'application/pdf'
                        elif filename_lower.endswith(('.jpg', '.jpeg')):
                            mime_type = 'image/jpeg'
                        elif filename_lower.endswith('.png'):
                            mime_type = 'image/png'
                        elif filename_lower.endswith('.webp'):
                            mime_type = 'image/webp'
                        else:
                            mime_type = 'application/pdf'

                    load_data = await self.extract_load_json(file_bytes, mime_type, message.content)
                        
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
                        alerts = ops_intel.get('alerts', [])
                        summary = ops_intel.get('dispatcher_summary', 'No summary generated.')
                        
                        # --- Deterministic Logic for Score and Risk ---
                        calc_score = 100
                        if not pickup_stop.get('appointment_time'): calc_score -= 15
                        if not delivery_stop.get('appointment_time'): calc_score -= 15
                        if str(rate_val) == '0' or not rate_val: calc_score -= 20
                        if load_data.get('reefer_operations', {}).get('temperature_setpoint') == "": calc_score -= 10
                        calc_score -= min(len(alerts) * 4, 30) # deduct for alerts
                        score = max(0, calc_score)
                        
                        if len(alerts) >= 8 or str(rate_val) == '0' or score < 70:
                            risk = "High"
                        elif len(alerts) >= 4 or score < 90:
                            risk = "Medium"
                        else:
                            risk = "Low"
                        # ----------------------------------------------
                        # ----------------------------------------------
                        
                        embed = discord.Embed(
                            title=f"✅ Load {load_id_val} Processed",
                            color=0x10b981
                        )
                        embed.add_field(name="📍 Origin", value=origin_str, inline=True)
                        embed.add_field(name="🏁 Destination", value=dest_str, inline=True)
                        embed.add_field(name="💰 Rate", value=f"${rate_val}", inline=True)
                        embed.add_field(name="📊 Readiness Score", value=f"{score}/100", inline=True)
                        
                        risk_emoji = "🟢" if risk == "Low" else "🟡" if risk == "Medium" else "🔴"
                        embed.add_field(name="⚠️ Risk Level", value=f"{risk_emoji} {risk}", inline=True)
                        
                        # --- Dedicated Temperature Requirements Field ---
                        reefer = load_data.get('reefer_operations', {})
                        temp_setpoint = reefer.get('temperature_setpoint') or ''
                        temp_range = reefer.get('temperature_range') or ''
                        temp_general = load_info.get('temperature_requirements') or ''
                        continuous = reefer.get('continuous_mode', False)
                        precool = reefer.get('pre_cool_required', False)
                        
                        temp_lines = []
                        if temp_setpoint and temp_setpoint.lower() != 'n/a':
                            temp_lines.append(f"🎯 **Setpoint:** {temp_setpoint}")
                        if temp_range and temp_range.lower() != 'n/a':
                            temp_lines.append(f"📏 **Range:** {temp_range}")
                        if temp_general and temp_general.lower() != 'n/a' and temp_general != temp_setpoint:
                            temp_lines.append(f"📋 **Requirement:** {temp_general}")
                        if continuous:
                            temp_lines.append("🔄 **Mode:** Continuous")
                        if precool:
                            temp_lines.append("❄️ **Pre-Cool:** Required")
                        
                        if temp_lines:
                            embed.add_field(
                                name="🌡️ TEMPERATURE REQUIREMENTS",
                                value="\n".join(temp_lines),
                                inline=False
                            )
                            # Remove temp-related items from alerts to avoid duplication
                            alerts = [a for a in alerts if 'temperature' not in a.lower() and 'temp ' not in a.lower() and 'reefer' not in a.lower()]
                        
                        broker_contact = []
                        if load_info.get('broker_email'): broker_contact.append(f"📧 {load_info['broker_email']}")
                        if load_info.get('broker_phone'): broker_contact.append(f"📞 {load_info['broker_phone']}")
                        if broker_contact:
                            embed.add_field(name="👔 Broker Contact", value="\n".join(broker_contact), inline=False)
                        
                        embed.add_field(name="🧠 Dispatcher Summary", value=summary[:1021] + "..." if len(summary) > 1024 else summary, inline=False)
                        
                        if alerts:
                            chunk = ""
                            chunk_idx = 1
                            for a in alerts:
                                alert_str = f"⚠️ {a}\n"
                                if len(chunk) + len(alert_str) > 1024:
                                    name = "🚨 Actionable Alerts" if chunk_idx == 1 else f"🚨 Actionable Alerts (Cont. {chunk_idx})"
                                    embed.add_field(name=name, value=chunk.strip(), inline=False)
                                    chunk = alert_str
                                    chunk_idx += 1
                                else:
                                    chunk += alert_str
                            if chunk:
                                name = "🚨 Actionable Alerts" if chunk_idx == 1 else f"🚨 Actionable Alerts (Cont. {chunk_idx})"
                                embed.add_field(name=name, value=chunk.strip(), inline=False)
                            
                        # Query vehicles to pass into the view
                        from database.models import Vehicle, AsyncSessionLocal
                        from sqlalchemy.future import select
                        async with AsyncSessionLocal() as session:
                            v_result = await session.execute(select(Vehicle).where(Vehicle.status == 'Active'))
                            active_vehicles = v_result.scalars().all()
                            
                        # Score and sort using Motive API
                        active_vehicles, driver_reasons = await score_and_sort_vehicles(active_vehicles)

                        if active_vehicles:
                            best_vehicle = active_vehicles[0]
                            reason_str = driver_reasons.get(best_vehicle.unit_id, "Based on availability.")
                            embed.add_field(name="🤖 Predicted Driver", value=f"**{best_vehicle.driver}** (Select below to change)\n> *{reason_str}*", inline=False)
                        else:
                            embed.add_field(name="🤖 Predicted Driver", value="**Unassigned** (No active trucks)", inline=False)
                            
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
                            original_message=message,
                            active_vehicles=active_vehicles
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
