from app.services.ai_client import get_gemini_client
from app.config import settings
from google.genai import types
import json
import re

def parse_document_text(ocr_text: str, user_message: str = '') -> dict:
    return {"status": "ok"}

def parse_document_file(file_bytes: bytes, mime_type: str) -> dict:
    client = get_gemini_client()
    
    prompt = """
    Extract the following details from this rate confirmation document.
    Return ONLY a raw JSON object with these exact keys, no markdown:
    {
      "broker": "Company Name",
      "origin": "City, State",
      "destination": "City, State",
      "pickup_date": "YYYY-MM-DD",
      "rate": "number only, no $",
      "commodity": "Commodity"
    }
    """
    
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ]
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"OCR Error: {e}")
        return {"broker": "Error", "origin": "", "destination": "", "pickup_date": "", "rate": "", "commodity": str(e)}
