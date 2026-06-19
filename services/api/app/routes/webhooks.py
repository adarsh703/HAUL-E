from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter(prefix="/api/webhooks/discord", tags=["webhooks"])

class DocumentPayload(BaseModel):
    file_url: str
    filename: str
    user_id: str
    message: str

class StatusPayload(BaseModel):
    message: str
    user_id: str
    load_id: str

class OnboardPayload(BaseModel):
    company_name: str
    mc_number: str
    eld_provider: str | None = None
    accounting_software: str | None = None
    discord_user_id: str

import urllib.request
from app.services.document_parser import parse_document_file
from app.models.load import Load
import random

@router.post("/document")
async def handle_document(payload: DocumentPayload, db: AsyncSession = Depends(get_db)):
    try:
        # Download the file from Discord CDN
        req = urllib.request.Request(payload.file_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            file_bytes = response.read()
        
        # Determine mime type
        mime_type = "image/png"
        if payload.filename.lower().endswith(".jpg") or payload.filename.lower().endswith(".jpeg"):
            mime_type = "image/jpeg"
        elif payload.filename.lower().endswith(".pdf"):
            mime_type = "application/pdf"
            
        # Parse using Gemini
        parsed_data = parse_document_file(file_bytes, mime_type)
        
        # Create load in database
        load_id = f"#L-{random.randint(10000, 99999)}"
        try:
            rate = float(str(parsed_data.get('rate', '0')).replace('$', '').replace(',', ''))
        except:
            rate = 0.0
            
        new_load = Load(
            load_id=load_id,
            origin=parsed_data.get('origin', 'Unknown'),
            destination=parsed_data.get('destination', 'Unknown'),
            pickup_date=parsed_data.get('pickup_date', 'TBD'),
            rate=rate,
            status='Pending',
            document_url=payload.file_url
        )
        db.add(new_load)
        await db.commit()
        await db.refresh(new_load)
        
        return {
            "status": "ok", 
            "load_id": load_id,
            "origin": new_load.origin,
            "destination": new_load.destination,
            "rate": new_load.rate
        }
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/status-update")
async def handle_status(payload: StatusPayload, db: AsyncSession = Depends(get_db)):
    return {"status": "ok"}

@router.post("/onboard")
async def handle_onboard(payload: OnboardPayload, db: AsyncSession = Depends(get_db)):
    from app.models.company import CompanyProfile
    new_company = CompanyProfile(**payload.model_dump())
    db.add(new_company)
    await db.commit()
    return {"status": "ok", "company_id": new_company.id}
