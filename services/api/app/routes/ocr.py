from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.document_parser import parse_document_file

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

@router.post("")
async def parse_ocr(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    file_bytes = await file.read()
    parsed_data = parse_document_file(file_bytes, file.content_type)
    return parsed_data
