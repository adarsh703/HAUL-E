import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from dotenv import load_dotenv
import os

load_dotenv()

# Resolve credentials file to absolute path and set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI
creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
if os.path.exists(creds_file):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(creds_file)

from database.models import init_db, AsyncSessionLocal, Load, Vehicle, TempCheckLog

@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database on startup
    await init_db()
    
    # Pre-populate some dummy data if empty
    async with AsyncSessionLocal() as session:
        result_v = await session.execute(select(Vehicle))
        vehicles = result_v.scalars().all()
        if not vehicles:
            session.add_all([
                Vehicle(unit_id='UNIT-101', type='Sleeper', driver='Alice S.', miles='142,000', service='150,000 mi', status='Active'),
                Vehicle(unit_id='UNIT-102', type='Day Cab', driver='Bob R.', miles='89,500', service='90,000 mi', status='Maintenance'),
                Vehicle(unit_id='UNIT-103', type='Reefer', driver='Charlie D.', miles='210,300', service='220,000 mi', status='Active'),
            ])
            
        # Re-initialize scheduler jobs for active loads on boot
        from services.temp_checker import start_temp_checks, start_location_checks, _scheduler
        
        if not _scheduler.running:
            _scheduler.start()
            
        active_loads_res = await session.execute(
            select(Load).where(Load.status.in_(["In Transit", "Dispatched"]))
        )
        active_loads = active_loads_res.scalars().all()
        for load in active_loads:
            job_id = f"temp_check_{load.load_id}"
            if not _scheduler.get_job(job_id):
                if load.temp_check_active:
                    asyncio.create_task(start_temp_checks(load.load_id, load.driver_phone, interval_minutes=180))
                else:
                    asyncio.create_task(start_location_checks(load.load_id, load.shipper_email, interval_minutes=180))
                
        await session.commit()
    yield
    # Clean up on shutdown

app = FastAPI(title="Mor Logistics TMS API", lifespan=lifespan)

# Allow CORS for React frontend (Vite defaults to 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles
os.makedirs("uploads", exist_ok=True)
os.makedirs("invoices", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/invoices", StaticFiles(directory="invoices"), name="invoices")

class LoadCreate(BaseModel):
    load_id: str
    origin_dest: str
    pickup_date: str
    driver: str
    rate: str
    status: str
    document_url: str | None = None

@app.get("/api/loads")
async def get_loads():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Load))
        loads = result.scalars().all()
        
        result_logs = await session.execute(select(TempCheckLog))
        all_logs = result_logs.scalars().all()
        
        load_list = []
        for load in loads:
            load_dict = {
                "id": load.id,
                "load_id": load.load_id,
                "origin_dest": load.origin_dest,
                "pickup_date": load.pickup_date,
                "driver": load.driver,
                "rate": load.rate,
                "status": load.status,
                "document_url": load.document_url,
                "operational_intelligence": load.operational_intelligence,
                "bol_path": load.bol_path,
                "pod_path": load.pod_path,
                "invoice_path": load.invoice_path,
                "driver_phone": load.driver_phone,
                "discord_thread_id": load.discord_thread_id,
                "temp_logs": [
                    {
                        "id": log.id,
                        "driver_response": log.driver_response,
                        "timestamp": log.timestamp.isoformat()
                    }
                    for log in all_logs if log.load_id == load.load_id
                ]
            }
            load_list.append(load_dict)
            
        return load_list

@app.post("/api/loads")
async def create_load(load: LoadCreate):
    from database.models import OperationalTask
    async with AsyncSessionLocal() as session:
        new_load = Load(**load.dict())
        if not new_load.load_id:
            import uuid
            new_load.load_id = "#L-" + str(uuid.uuid4())[:4].upper()
        
        session.add(new_load)
        
        # Create operational task for discord bot to pick up
        task = OperationalTask(
            task_type="NEW_LOAD",
            description=f"🌐 **New Web Load**: {new_load.load_id} ({new_load.origin_dest}) - Rate: ${new_load.rate}",
            status="PENDING"
        )
        session.add(task)

        await session.commit()
        await session.refresh(new_load)
        return new_load

@app.delete("/api/loads/{load_id}")
async def delete_load(load_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Load).where(Load.load_id == load_id))
        load_item = result.scalars().first()
        if not load_item:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Load not found")
            
        from database.models import TempCheckLog
        from sqlalchemy import delete
        await session.execute(delete(TempCheckLog).where(TempCheckLog.load_id == load_id))
        
        await session.delete(load_item)
        await session.commit()
        
        # Stop any active temp check loops for this load
        try:
            from services.temp_checker import stop_temp_checks
            stop_temp_checks(load_id)
        except Exception as e:
            log.error(f"Error stopping temp checks for deleted load {load_id}: {e}")
            
        return {"status": "success", "message": f"Load {load_id} deleted"}

@app.post("/api/dispatch/auto")
async def auto_dispatch():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Load).where(Load.status == 'Pending'))
        pending_loads = result.scalars().all()
        
        result_v = await session.execute(select(Vehicle).where(Vehicle.status == 'Active'))
        active_vehicles = result_v.scalars().all()
        
        if not pending_loads or not active_vehicles:
            return {"assignments": []}
            
        assignments = []
        import random
        for load in pending_loads:
            vehicle = random.choice(active_vehicles)
            load.driver = vehicle.driver
            load.status = 'In Transit'
            assignments.append({"load_id": load.load_id, "driver": vehicle.driver})
            
        await session.commit()
        return {"assignments": assignments}

class VehicleCreate(BaseModel):
    unit_id: str
    type: str
    driver: str
    miles: str
    service: str
    status: str

@app.get("/api/fleet")
async def get_fleet():
    from services.motive_service import sync_fleet_from_motive
    async with AsyncSessionLocal() as session:
        loads_res = await session.execute(select(Load).where(Load.status.in_(["Pending", "In Transit", "Dispatched"])))
        active_loads = loads_res.scalars().all()
        driver_to_load = {ld.driver: ld.load_id for ld in active_loads if ld.driver and ld.driver != "Unassigned"}
        
        motive_vehicles = sync_fleet_from_motive()
        
        result = await session.execute(select(Vehicle))
        db_vehicles = result.scalars().all()
        db_v_dict = {v.unit_id: v for v in db_vehicles}
        
        new_vehicles_added = False
        for mv in motive_vehicles:
            if mv["unit_id"] in db_v_dict:
                v_obj = db_v_dict[mv["unit_id"]]
                v_obj.driver = mv["driver"]
                v_obj.miles = mv["miles"]
                v_obj.type = mv["type"]
                v_obj.status = mv["status"]
            else:
                new_v = Vehicle(
                    unit_id=mv["unit_id"],
                    type=mv["type"],
                    driver=mv["driver"],
                    miles=mv["miles"],
                    service=mv["service"],
                    status=mv["status"]
                )
                session.add(new_v)
                db_v_dict[mv["unit_id"]] = new_v
                new_vehicles_added = True
        
        if new_vehicles_added or motive_vehicles:
            await session.commit()
            result = await session.execute(select(Vehicle))
            db_vehicles = result.scalars().all()
            
        v_list = []
        for v in db_vehicles:
            load_id = driver_to_load.get(v.driver, "None")
            v_list.append({
                "id": v.id,
                "unit_id": v.unit_id,
                "type": v.type,
                "driver": v.driver,
                "miles": v.miles,
                "service": v.service,
                "status": v.status,
                "current_load": load_id
            })
            
        return v_list

@app.post("/api/fleet")
async def create_vehicle(vehicle: VehicleCreate):
    async with AsyncSessionLocal() as session:
        new_vehicle = Vehicle(**vehicle.dict())
        session.add(new_vehicle)
        await session.commit()
        await session.refresh(new_vehicle)
        return new_vehicle

from fastapi import UploadFile, File
import random

@app.post("/api/ocr")
async def process_ocr(file: UploadFile = File(...)):
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image
    import io
    import json
    import os
    from google import genai
    from google.oauth2 import service_account

    content = await file.read()
    extracted_text = ""
    
    import uuid
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    saved_filename = f"{uuid.uuid4().hex}{file_ext}"
    saved_filepath = os.path.join("/home/no_one/Desktop/broker-bot/uploads", saved_filename)
    with open(saved_filepath, "wb") as f:
        f.write(content)
        
    document_url = f"http://127.0.0.1:8000/uploads/{saved_filename}"
    
    if file.content_type == "application/pdf":
        images = convert_from_bytes(content)
        for img in images:
            extracted_text += pytesseract.image_to_string(img) + "\\n"
    else:
        img = Image.open(io.BytesIO(content))
        extracted_text = pytesseract.image_to_string(img)
        
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
    creds = service_account.Credentials.from_service_account_file(
        creds_file, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    client = genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_PROJECT_ID"),
        location=os.getenv("GOOGLE_LOCATION"),
        credentials=creds,
    )
    
    prompt = f"""
Extract load details from the provided text and return ONLY valid JSON with keys: 'broker', 'origin', 'destination', 'pickup_date', 'rate', 'driver'. 
Do not include markdown formatting. 

CRITICAL EXTRACTION RULES:
1. **rate**: MUST be the GRAND TOTAL / Total Cost / Total Amount for the load. Rate Confirmations often break down costs (e.g. Flat Rate, Fuel, Lumper). Ignore individual line items. Find the final Total. Return it as a string formatted like "$X,XXX.XX".
2. **pickup_date**: This is the date the load is scheduled to be picked up. Look under sections like "Shipper", "Initial Pickup", "Stop 1", or "PICK UP". DO NOT use the Order Date or Document Date found at the very top of the page.
3. **origin**: Look for the City and State under the Shipper / Initial Pickup section.
4. **destination**: Look for the City and State under the Consignee / Final Destination section.
5. **driver**: Look for "Driver", "Driver's Name" or similar. If none is found, set 'driver' to 'Unassigned'.

OCR Text:
{extracted_text[:10000]}
"""
    try:
        response = await client.aio.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt
        )
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_json)
        data["document_url"] = document_url
        return data
    except Exception as e:
        print(f"OCR Error: {e}")
        return {"error": str(e)}

class PredictionRequest(BaseModel):
    origin: str
    destination: str
    rate: str | float

@app.post("/api/predict")
@app.post("/api/dispatch/predict")
async def predict_profit(req: PredictionRequest):
    await asyncio.sleep(1) # Simulate AI prediction
    try:
        if isinstance(req.rate, (int, float)):
            rate_num = float(req.rate)
        else:
            rate_num = float(req.rate.replace(',', '').replace('$', '')) if req.rate else 4000.0
    except ValueError:
        rate_num = 4000.0
    fuel = rate_num * 0.25
    driver = rate_num * 0.40
    tolls = rate_num * 0.05
    overhead = rate_num * 0.10
    profit = rate_num - (fuel + driver + tolls + overhead)
    
    return {
        "fuel": f"${fuel:.2f}",
        "driver": f"${driver:.2f}",
        "tolls": f"${tolls:.2f}",
        "overhead": f"${overhead:.2f}",
        "profit": f"${profit:.2f}",
        "margin": f"{(profit/rate_num)*100:.1f}%",
        "recommendation": "Accept Load" if profit > 500 else "Reject / Negotiate"
    }

@app.get("/api/track/{unit_id}")
async def track_vehicle(unit_id: str):
    from services.motive_service import get_vehicle_tracking
    import datetime
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Vehicle).where(Vehicle.unit_id == unit_id))
        vehicle = result.scalars().first()
        
        if not vehicle:
            return {"error": "Vehicle not found"}
            
        motive_data = get_vehicle_tracking(unit_id)
        
        if motive_data:
            current_location = motive_data["location"]
            speed = motive_data["speed"]
            status = motive_data["status"]
            hos_remaining = motive_data["hos"]
        else:
            current_location = "Location Unavailable"
            speed = 0
            status = "Disconnected"
            hos_remaining = 0.0
        
        return {
            "unit_id": vehicle.unit_id,
            "driver": vehicle.driver,
            "location": current_location,
            "speed": speed,
            "status": status,
            "hos": hos_remaining,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }

# ---------------------------------------------------------------------------
# Twilio SMS / WhatsApp Webhook
# ---------------------------------------------------------------------------
TEMP_KEYWORDS = {"yes", "no", "temp", "temperature", "degrees", "°f", "°c", "issue"}


@app.post("/api/sms/incoming")
async def incoming_sms(
    From: str = Form(...),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None),
):
    """
    Twilio webhook – called when a driver replies via SMS or WhatsApp.

    • Temperature replies  → logged as TempCheckLog, forwarded to shipper (email)
                             and dispatcher (WhatsApp).
    • Media attachments    → saved as BOL / POD documents, emailed to shipper.
    """
    import logging
    import re

    logger = logging.getLogger("haul-e.sms")

    # Normalize WhatsApp prefix — Twilio sends "whatsapp:+919893602351"
    driver_phone = From.replace("whatsapp:", "").strip()
    logger.info(f"Incoming message from {driver_phone}: {Body!r} (media={NumMedia})")

    async with AsyncSessionLocal() as session:
        # ----- 1. Look up the active load for this driver phone -----
        result = await session.execute(
            select(Load).where(
                Load.driver_phone == driver_phone,
                Load.status.in_(["In Transit", "Dispatched", "Active", "Awaiting Approval", "Delivered"]),
            )
            .order_by(Load.id.desc())
        )
        load = result.scalars().first()

        body_lower = Body.strip().lower()

        # Check if dispatcher is approving load creation
        dispatcher_load_res = await session.execute(
            select(Load).where(
                Load.dispatcher_phone == driver_phone,
                Load.status == "Awaiting Approval"
            )
        )
        disp_load = dispatcher_load_res.scalars().first()
        
        if disp_load and ("approve" in body_lower or body_lower.isdigit()):
            assigned_truck = "N/A"
            if body_lower.isdigit():
                idx = int(body_lower) - 1
                from services.motive_service import sync_fleet_from_motive
                import asyncio
                vehicles = await asyncio.to_thread(sync_fleet_from_motive)
                active_drivers = [v for v in vehicles if v.get('driver') and v['driver'] != "Unassigned"]
                
                if 0 <= idx < min(15, len(active_drivers)):
                    disp_load.driver = active_drivers[idx]["driver"]
                    assigned_truck = active_drivers[idx].get("vehicle", "N/A")
                else:
                    disp_load.driver = "Test Driver"
                    
            disp_load.status = "Dispatched"
            await session.commit()
            
            # Send actual dispatch message to driver
            from services.twilio_sms import send_load_details_to_driver
            load_data = disp_load.operational_intelligence or {}
            await send_load_details_to_driver(
                disp_load.driver_phone, 
                load_data,
                driver_name=disp_load.driver,
                truck=assigned_truck,
                trailer="N/A"  # Pulling trailer requires deeper Motive API, N/A for now
            )
            
            # Send confirmation back to dispatcher
            await send_whatsapp(disp_load.dispatcher_phone, f"✅ Load {disp_load.load_id} assigned to {disp_load.driver} and dispatched!")
            
            logger.info(f"Load {disp_load.load_id} approved and dispatched to {disp_load.driver}.")
            return Response(content="<Response></Response>", media_type="application/xml")
            
        elif disp_load and "reject" in body_lower:
            disp_load.status = "Rejected"
            await session.commit()
            
            from services.twilio_sms import send_whatsapp
            await send_whatsapp(disp_load.dispatcher_phone, f"❌ Load {disp_load.load_id} has been REJECTED and won't be dispatched.")
            logger.info(f"Load {disp_load.load_id} rejected by dispatcher.")
            return Response(content="<Response></Response>", media_type="application/xml")

            
        # If no active driver load found, return empty
        if not load:
            logger.warning(f"No active load found for phone {driver_phone}")
            return Response(
                content="<Response></Response>", media_type="application/xml"
            )

        # AI Intent Parsing for Text Messages
        if NumMedia == 0 and Body.strip():
            try:
                import json
                from google import genai
                from google.oauth2 import service_account
                creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
                creds = service_account.Credentials.from_service_account_file(creds_file, scopes=["https://www.googleapis.com/auth/cloud-platform"])
                client = genai.Client(vertexai=True, project=os.getenv("GOOGLE_PROJECT_ID"), location=os.getenv("GOOGLE_LOCATION"), credentials=creds)
                
                prompt = f"""You are HAUL-E, an AI dispatcher for Mor Logistics.
A driver for Load #{load.load_id} (Status: {load.status}) sent you this message: "{Body.strip()}"

Determine their intent.
If they say they picked up the load or are loaded, intent="loaded".
If they say they delivered or dropped it off, intent="delivered".
If they provide a temperature reading (e.g. "34", "0 F"), intent="temperature", and extract the value.
If they are correcting a document mistake (e.g. "no that was a bol", "the last photo was pod"), intent="document_correction", and extract which one it actually was (BOL or POD).
Otherwise, intent="chat" and provide a helpful, natural, and brief response to their message as an AI dispatcher.

Respond ONLY with a valid JSON object:
{{
    "intent": "loaded" | "delivered" | "temperature" | "document_correction" | "chat",
    "temperature_value": "extracted temp or null",
    "corrected_doc_type": "BOL" | "POD" | null,
    "chat_response": "your reply if intent is chat, else null"
}}"""
                response = await client.aio.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt
                )
                
                intent_data = json.loads(response.text.strip('```json\n').strip('```').strip())
                intent = intent_data.get("intent", "chat")
                
                if intent == "loaded":
                    body_lower = "loaded"
                elif intent == "delivered":
                    body_lower = "delivered"
                elif intent == "temperature":
                    body_lower = str(intent_data.get("temperature_value", Body)).lower()
                elif intent == "document_correction":
                    correct_doc = intent_data.get("corrected_doc_type")
                    if correct_doc == "BOL" and load.pod_path and not load.bol_path:
                        load.bol_path = load.pod_path
                        load.pod_path = None
                        await session.commit()
                        from services.twilio_sms import send_whatsapp
                        await send_whatsapp(load.driver_phone, "✅ Got it! I've corrected that document to a BOL. Please send the POD when you have it.")
                        return Response(content="<Response></Response>", media_type="application/xml")
                    elif correct_doc == "POD" and load.bol_path and not load.pod_path:
                        load.pod_path = load.bol_path
                        load.bol_path = None
                        await session.commit()
                        from services.twilio_sms import send_whatsapp
                        await send_whatsapp(load.driver_phone, "✅ Got it! I've corrected that document to a POD. Please send the BOL when you have it.")
                        return Response(content="<Response></Response>", media_type="application/xml")
                    else:
                        from services.twilio_sms import send_whatsapp
                        await send_whatsapp(load.driver_phone, f"I couldn't find a document to swap to a {correct_doc}. Make sure you upload it first!")
                        return Response(content="<Response></Response>", media_type="application/xml")
                elif intent == "chat":
                    from services.twilio_sms import send_whatsapp
                    await send_whatsapp(load.driver_phone, intent_data.get("chat_response", "I'm here to help with your dispatch!"))
                    return Response(content="<Response></Response>", media_type="application/xml")
            except Exception as e:
                logger.error(f"AI Intent parsing failed: {e}")
        
        # Check if driver picked up
        if "picked up" in body_lower or "loaded" in body_lower:
            if load.status == "In Transit":
                from services.twilio_sms import send_whatsapp
                await send_whatsapp(load.driver_phone, "⚠️ Your load is already marked as *In Transit*. Reply *delivered* when you arrive.")
                return Response(content="<Response></Response>", media_type="application/xml")
            elif load.status in ["Delivered", "Completed"]:
                from services.twilio_sms import send_whatsapp
                await send_whatsapp(load.driver_phone, f"⚠️ This load is already marked as *{load.status}*.")
                return Response(content="<Response></Response>", media_type="application/xml")

            load.status = "In Transit"
            logger.info(f"Load {load.load_id} marked as In Transit by driver.")
            
            if load.temp_check_active:
                from services.temp_checker import start_temp_checks
                # Start temp checks immediately upon pickup, and then every 3 hours (180 minutes)
                import asyncio
                asyncio.create_task(start_temp_checks(load.load_id, load.driver_phone, interval_minutes=180))
                logger.info(f"Started 3-hour temp checks for {load.load_id}")
            else:
                from services.temp_checker import start_location_checks
                import asyncio
                asyncio.create_task(start_location_checks(load.load_id, load.shipper_email, interval_minutes=180))
                logger.info(f"Started 3-hour silent tracking for {load.load_id}")
            
            from services.twilio_sms import send_whatsapp
            reply_msg = (
                f"✅ Pick-up confirmed! Your status is now *In Transit*.\n"
                f"Drive safe! Reply *delivered* when you drop it off."
            )
            await send_whatsapp(load.driver_phone, reply_msg)
            from services.temp_checker import schedule_delivery_check
            from datetime import datetime, timedelta
            run_date = datetime.now() + timedelta(minutes=2)
            schedule_delivery_check(load.load_id, load.driver_phone, run_date)
            logger.info(f"Scheduled auto-delivery check for {load.load_id} at {run_date}")
            
            await session.commit()
            return Response(content="<Response></Response>", media_type="application/xml")

        # Check if driver delivered
        if "delivered" in body_lower or "completed" in body_lower or "dropped" in body_lower or "empty" in body_lower:
            if load.status == "Delivered":
                from services.twilio_sms import send_whatsapp
                await send_whatsapp(load.driver_phone, "⚠️ Your load is already marked as *Delivered*. Please send your documents if you haven't yet.")
                return Response(content="<Response></Response>", media_type="application/xml")
            elif load.status == "Completed":
                from services.twilio_sms import send_whatsapp
                await send_whatsapp(load.driver_phone, "⚠️ This load is completely finished!")
                return Response(content="<Response></Response>", media_type="application/xml")

            load.status = "Delivered"
            logger.info(f"Load {load.load_id} marked as Delivered by driver.")
            
            # Stop temp checks
            if load.temp_check_active:
                from services.temp_checker import stop_temp_checks
                import asyncio
                asyncio.create_task(stop_temp_checks(load.load_id))
                logger.info(f"Stopped temp checks for {load.load_id}")
            
            # Ask for BOL/POD if missing
            missing_docs = []
            if not load.bol_path:
                missing_docs.append("BOL")
            if not load.pod_path:
                missing_docs.append("POD")
            
            from services.twilio_sms import _send_whatsapp_sync
            import asyncio
            if missing_docs:
                docs_str = " and ".join(missing_docs)
                reply_msg = f"Awesome! 🎉 Please reply with a clear photo of the {docs_str} so we can get you paid."
            else:
                reply_msg = "Awesome! 🎉 We have all your documents. Have a safe next trip!"
                
            asyncio.create_task(asyncio.to_thread(_send_whatsapp_sync, load.driver_phone, reply_msg))
            
            await session.commit()
            return Response(content="<Response></Response>", media_type="application/xml")

        is_temp_reply = any(kw in body_lower for kw in TEMP_KEYWORDS) or bool(
            re.search(r"-?\d+\.?\d*", body_lower)
        )

        if is_temp_reply and load.temp_check_active:
            temp_log = TempCheckLog(
                load_id=load.load_id,
                driver_response=Body.strip()[:500],
                forwarded_to_shipper=False,
                forwarded_to_dispatcher=False,
            )
            session.add(temp_log)
            logger.info(
                f"Temp check logged for load {load.load_id}: {Body.strip()!r}"
            )

            # --- AI EVALUATION OF TEMPERATURE ---
            is_issue = False
            try:
                import json
                from google import genai
                from google.oauth2 import service_account
                
                ops_data = json.loads(load.operational_intelligence or "{}")
                req_temp = ops_data.get("reefer_operations", {}).get("temperature_setpoint") or ops_data.get("load_information", {}).get("temperature_requirements") or "Unknown"
                
                creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
                creds = service_account.Credentials.from_service_account_file(creds_file, scopes=["https://www.googleapis.com/auth/cloud-platform"])
                client = genai.Client(
                    vertexai=True,
                    project=os.getenv("GOOGLE_PROJECT_ID"),
                    location=os.getenv("GOOGLE_LOCATION"),
                    credentials=creds,
                )
                
                prompt = f"""
You are a freight dispatcher AI. 
The required temperature for the load is: {req_temp}
The driver just replied to a temperature check with: "{Body.strip()}"

Analyze if the driver's response indicates the temperature is CORRECT and WITHIN RANGE, or if there is an ISSUE (e.g., out of range, broken reefer, wrong number).
IMPORTANT RULES:
1. Allow a tolerance of +/- 0.5 to 1.0 degrees. For example, if the required range is 34-35°F, a response of 33, 33.5, 35.5, or 36 is acceptable and NOT an issue.
2. However, anything more than 1 degree off (like 30, 32, or 38) is an ISSUE.
Respond with exactly one word: 'OK' or 'ISSUE'.
"""
                response = await client.aio.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt
                )
                is_issue = "ISSUE" in response.text.upper()
                logger.info(f"AI Temp Evaluation -> Required: {req_temp} | Driver: {Body.strip()} | is_issue: {is_issue}")
            except Exception as e:
                logger.error(f"AI Evaluation failed: {e}")
                # Fallback
                if "issue" in body_lower or "no" == body_lower or "problem" in body_lower or "wrong" in body_lower:
                    is_issue = True

            # Forward to shipper via email
            if load.shipper_email:
                try:
                    from services.twilio_sms import forward_temp_response_email
                    await forward_temp_response_email(
                        load.shipper_email, load.load_id, Body.strip(), is_issue=is_issue
                    )
                    temp_log.forwarded_to_shipper = True
                    logger.info(f"Temp response forwarded to shipper: {load.shipper_email}")
                except Exception as e:
                    logger.error(f"Failed to forward temp to shipper: {e}")

            # Also forward to the broker (who received the RC) if there is an issue
            if is_issue:
                broker_email = os.getenv("GMAIL_USER")
                if broker_email:
                    try:
                        from services.twilio_sms import forward_temp_response_email
                        await forward_temp_response_email(
                            broker_email, load.load_id, Body.strip(), is_issue=is_issue
                        )
                        logger.info(f"Temp issue alert sent to broker: {broker_email}")
                    except Exception as e:
                        logger.error(f"Failed to forward temp alert to broker: {e}")

            # Forward to dispatcher via WhatsApp
            if load.dispatcher_phone:
                try:
                    from services.twilio_sms import forward_temp_response_whatsapp
                    await forward_temp_response_whatsapp(
                        load.dispatcher_phone, load.load_id, Body.strip(), is_issue=is_issue
                    )
                    temp_log.forwarded_to_dispatcher = True
                    logger.info(f"Temp response forwarded to dispatcher: {load.dispatcher_phone}")
                except Exception as e:
                    logger.error(f"Failed to forward temp to dispatcher: {e}")
            
            await session.commit()
            return Response(content="<Response></Response>", media_type="application/xml")

        # ----- 3. Media attachments (BOL / POD) -----
        if NumMedia > 0 and MediaUrl0:
            import httpx
            import uuid

            load_dir = os.path.join(
                "/home/no_one/Desktop/broker-bot/uploads", load.load_id
            )
            os.makedirs(load_dir, exist_ok=True)

            ext = ".pdf"
            if MediaContentType0:
                ext_map = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "application/pdf": ".pdf",
                    "image/webp": ".webp",
                }
                ext = ext_map.get(MediaContentType0, ".bin")

            # Download file first to a temp path
            temp_name = f"temp_{uuid.uuid4().hex[:8]}{ext}"
            temp_path = os.path.join(load_dir, temp_name)
            
            try:
                # Twilio media requires basic auth to download and uses redirects
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    auth=(
                        os.getenv("TWILIO_ACCOUNT_SID", ""),
                        os.getenv("TWILIO_AUTH_TOKEN", ""),
                    )
                ) as http:
                    resp = await http.get(MediaUrl0)
                    resp.raise_for_status()
                    with open(temp_path, "wb") as f:
                        f.write(resp.content)
                        
                # Determine doc type via AI Vision if not explicitly typed
                body_upper = Body.strip().upper()
                if "BOL" in body_upper:
                    doc_type = "BOL"
                elif "POD" in body_upper:
                    doc_type = "POD"
                else:
                    # AI Image Classification
                    try:
                        from google import genai
                        from google.oauth2 import service_account
                        from PIL import Image
                        
                        creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "google_credentials.json")
                        creds = service_account.Credentials.from_service_account_file(
                            creds_file, scopes=["https://www.googleapis.com/auth/cloud-platform"]
                        )
                        client = genai.Client(
                            vertexai=True,
                            project=os.getenv("GOOGLE_PROJECT_ID"),
                            location=os.getenv("GOOGLE_LOCATION"),
                            credentials=creds,
                        )
                        
                        img = Image.open(temp_path)
                        prompt = "Look at this trucking document. Does it look like a Bill of Lading (BOL) or a Proof of Delivery (POD) with a receiver's signature? Reply ONLY with the word 'BOL' or 'POD'."
                        
                        response = await client.aio.models.generate_content(
                            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                            contents=[img, prompt]
                        )
                        res_text = response.text.strip().upper()
                        if res_text == "POD":
                            doc_type = "POD"
                        else:
                            doc_type = "BOL"
                        logger.info(f"AI Vision classified image as {doc_type} (raw: {res_text})")
                    except Exception as ai_e:
                        logger.warning(f"AI Vision classification failed: {ai_e}")
                        # Fallback
                        doc_type = "BOL" if not load.bol_path else "POD"
                        
                if (doc_type == "BOL" and load.bol_path) or (doc_type == "POD" and load.pod_path):
                    from services.twilio_sms import send_whatsapp
                    await send_whatsapp(load.driver_phone, f"⚠️ We already have a {doc_type} on file for this load! Ignoring duplicate.")
                    os.remove(temp_path)
                    await session.commit()
                    return Response(content="<Response></Response>", media_type="application/xml")

                saved_name = f"{doc_type}_{uuid.uuid4().hex[:8]}{ext}"
                saved_path = os.path.join(load_dir, saved_name)
                os.rename(temp_path, saved_path)

                if doc_type == "BOL":
                    load.bol_path = saved_path
                else:
                    load.pod_path = saved_path

                logger.info(
                    f"Saved {doc_type} for load {load.load_id} → {saved_path}"
                )

                # Email BOL/POD to shipper
                if load.shipper_email or load.broker_email:
                    try:
                        from gmail_sender import _send_invoice_via_smtp
                        import asyncio
                        recipient = load.shipper_email or load.broker_email
                        subject = f"{doc_type} Received — Load {load.load_id} | Mor Logistics Manitoba Ltd"
                        email_body = (
                            f"Hello,\n\n"
                            f"Please find the attached {doc_type} for Load {load.load_id}.\n\n"
                            f"Thank you,\nMor Logistics Manitoba Ltd"
                        )
                        await asyncio.to_thread(
                            _send_invoice_via_smtp, recipient, subject, email_body, saved_path
                        )
                        logger.info(f"{doc_type} emailed to {recipient}")
                    except Exception as e:
                        logger.error(f"Failed to email {doc_type}: {e}")

                # Check for hard copy POD charge
                # if doc_type == "POD" and load.hard_copy_pod_required:
                #     try:
                #         from gmail_sender import _send_via_smtp
                #         import asyncio
                #         recipient = load.broker_email or load.shipper_email
                #         if recipient:
                #             subject = f"Hard Copy POD — Load {load.load_id} | Mor Logistics Manitoba Ltd"
                #             charge_body = (
                #                 f"Hello,\n\n"
                #                 f"As noted in the Rate Confirmation for Load {load.load_id}, "
                #                 f"a hard copy of the Proof of Delivery has been requested.\n\n"
                #                 f"Please note there will be a $90.00 charge for the physical hard copy.\n\n"
                #                 f"Please confirm and we will ship it out promptly.\n\n"
                #                 f"Thank you,\nMor Logistics Manitoba Ltd"
                #             )
                #             await asyncio.to_thread(
                #                 _send_via_smtp, recipient, subject, charge_body
                #             )
                #             logger.info(f"Hard copy POD charge notice sent to {recipient}")
                #     except Exception as e:
                #         logger.error(f"Failed to send hard copy charge notice: {e}")

                # Send confirmation to driver
                from services.twilio_sms import send_whatsapp
                
                msg_text = f"✅ Received your {doc_type}!"
                
                if load.bol_path and load.pod_path:
                    load.status = "Completed"
                    msg_text += "\nWe have all your paperwork. This load is officially Completed. Great job and drive safe! 🚚💨"
                    
                    if load.temp_check_active:
                        from services.temp_checker import stop_temp_checks
                        stop_temp_checks(load.load_id)
                    else:
                        from services.temp_checker import stop_location_checks
                        stop_location_checks(load.load_id)
                        
                    # Trigger invoice generation and approval flow via Discord
                    from database.models import OperationalTask
                    task = OperationalTask(
                        task_type="INVOICE_APPROVAL",
                        reference_id=load.load_id,
                        description=f"Approve Invoice for Load {load.load_id}",
                        status="PENDING"
                    )
                    session.add(task)
                else:
                    missing = []
                    if not load.bol_path: missing.append("BOL")
                    if not load.pod_path: missing.append("POD")
                    if missing:
                        msg_text += f"\nWe are still missing your {' and '.join(missing)}."

                await send_whatsapp(load.driver_phone, msg_text)

            except Exception as exc:
                logger.error(f"Failed to download media from Twilio: {exc}")

            await session.commit()
            return Response(content="<Response></Response>", media_type="application/xml")

        # --- Catch-all for unrecognized messages ---
        from services.twilio_sms import send_whatsapp
        fallback_msg = (
            "🤖 I didn't quite catch that.\n"
            "• Reply *loaded* if you have picked up the load.\n"
            "• Reply *delivered* if you have dropped it off.\n"
            "• If this is a temperature update, just send the numbers (e.g., '34').\n"
            "• To send documents, simply attach a photo to this chat."
        )
        await send_whatsapp(load.driver_phone, fallback_msg)
        await session.commit()
        return Response(content="<Response></Response>", media_type="application/xml")

from database.models import Settings

@app.get("/api/settings")
async def get_settings():
    async with get_db_session() as session:
        result = await session.execute(select(Settings))
        settings_rows = result.scalars().all()
        return {row.key: row.value for row in settings_rows}

class SettingsUpdate(BaseModel):
    gmail_user: str | None = None
    gmail_app_password: str | None = None

@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    from dotenv import set_key
    env_file = "/home/no_one/Desktop/broker-bot/.env"
    
    async with get_db_session() as session:
        if settings.gmail_user is not None:
            await session.merge(Settings(key="gmail_user", value=settings.gmail_user))
            set_key(env_file, "GMAIL_USER", settings.gmail_user)
            os.environ["GMAIL_USER"] = settings.gmail_user
            
        if settings.gmail_app_password is not None:
            await session.merge(Settings(key="gmail_app_password", value=settings.gmail_app_password))
            set_key(env_file, "GMAIL_APP_PASSWORD", settings.gmail_app_password)
            os.environ["GMAIL_APP_PASSWORD"] = settings.gmail_app_password
            
        await session.commit()
        return {"status": "success", "message": "Settings updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)



import json
import os
import httpx

GEO_CACHE_FILE = "geo_cache.json"

def get_geo_cache():
    if os.path.exists(GEO_CACHE_FILE):
        try:
            with open(GEO_CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_geo_cache(cache):
    with open(GEO_CACHE_FILE, "w") as f:
        json.dump(cache, f)

async def geocode_city(city_str: str):
    cache = get_geo_cache()
    if city_str in cache:
        return cache[city_str]
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city_str, "format": "json", "limit": 1},
                headers={"User-Agent": "Haul-E-TMS/1.0"}
            )
            if resp.status_code == 200 and resp.json():
                data = resp.json()[0]
                res = {"lat": float(data["lat"]), "lon": float(data["lon"])}
                cache[city_str] = res
                save_geo_cache(cache)
                return res
    except Exception as e:
        print(f"Geocode error for {city_str}: {e}")
    
    # Fallback to center of US if failed
    res = {"lat": 39.8283, "lon": -98.5795}
    return res

@app.get("/api/live_map")
async def get_live_map():
    from services.motive_service import get_vehicle_tracking_raw
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Load).where(Load.status.in_(["In Transit", "Assigned"])))
        active_loads = result.scalars().all()
        
        result_v = await session.execute(select(Vehicle))
        db_vehicles = result_v.scalars().all()
        db_v_dict = {v.driver: v.unit_id for v in db_vehicles if v.driver}
        
        routes = []
        for load in active_loads:
            od = load.origin_dest or ""
            origin_str, dest_str = "", ""
            if " to " in od:
                parts = od.split(" to ", 1)
            elif " → " in od:
                parts = od.split(" → ", 1)
            elif "->" in od:
                parts = od.split("->", 1)
            else:
                parts = [od, od]
                
            if len(parts) == 2:
                origin_str, dest_str = parts[0].strip(), parts[1].strip()
                
            if not origin_str or not dest_str:
                continue
                
            origin_geo = await geocode_city(origin_str)
            dest_geo = await geocode_city(dest_str)
            
            truck_geo = None
            if load.driver and load.driver in db_v_dict:
                unit_id = db_v_dict[load.driver]
                truck_data = get_vehicle_tracking_raw(unit_id)
                if truck_data and truck_data.get("lat") and truck_data.get("lon"):
                    truck_geo = {
                        "lat": truck_data["lat"],
                        "lon": truck_data["lon"],
                        "description": truck_data.get("description", ""),
                        "speed": truck_data.get("speed", 0)
                    }
            
            # If no live truck geo, place truck at origin
            if not truck_geo:
                truck_geo = {
                    "lat": origin_geo["lat"],
                    "lon": origin_geo["lon"],
                    "description": "Location Unavailable (Idle at Origin)",
                    "speed": 0
                }
                
            routes.append({
                "load_id": load.load_id,
                "driver": load.driver,
                "origin": {"name": origin_str, "lat": origin_geo["lat"], "lon": origin_geo["lon"]},
                "destination": {"name": dest_str, "lat": dest_geo["lat"], "lon": dest_geo["lon"]},
                "truck": truck_geo
            })
            
        return {"routes": routes}
