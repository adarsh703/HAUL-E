import asyncio
import os
import pytesseract
from pdf2image import convert_from_path
from google import genai
from google.oauth2 import service_account
import json

async def main():
    pdf_path = "/home/no_one/Downloads/Order Confirmation for Order 0099974.pdf"
    print("Converting PDF to images...")
    images = convert_from_path(pdf_path)
    extracted_text = ""
    for img in images:
        extracted_text += pytesseract.image_to_string(img) + "\n"
    
    print("Extracted Text Length:", len(extracted_text))
    
    creds_file = "google_credentials.json"
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

OCR Text:
{extracted_text[:10000]}
"""
    print("Sending to Gemini...")
    response = await client.aio.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt
    )
    print("Response:", response.text)

asyncio.run(main())
