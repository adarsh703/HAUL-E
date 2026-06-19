import asyncio
import os
import pytesseract
from pdf2image import convert_from_path
from google import genai
from google.oauth2 import service_account
import json

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("google_credentials.json")

async def extract_load_json(client, model, ocr_text, user_text=""):
    prompt = f"""
Extract load details from the provided text and return ONLY valid JSON with keys: 'broker', 'origin', 'destination', 'pickup_date', 'rate', 'driver'. 
Do not include markdown formatting. 

Instructions:
1. If the User Message provides specific details (like a rate, date, lane, or driver name), prioritize them over the OCR text.
2. Fill in the rest of the details using the OCR Text from the document.
3. If no driver is mentioned in either, set 'driver' to 'Unassigned'.

User Message:
{user_text}

OCR Text:
{ocr_text[:10000]}
"""
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return str(e)

async def main():
    pdfs = [
        "/home/no_one/Downloads/Confirmation1192539.pdf",
        "/home/no_one/Downloads/Signed Carrier Rate Confirmation-Thu_14_May_2026_064042PM-1010399.pdf",
        "/home/no_one/Downloads/CarrierConfirmation#157916.pdf",
        "/home/no_one/Downloads/Signed Carrier Rate Confirmation-Thu_14_May_2026_113846PM-1010411.pdf"
    ]
    
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
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    for pdf in pdfs:
        print(f"Processing {os.path.basename(pdf)}...")
        try:
            images = convert_from_path(pdf)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
            
            print(f"--- Extracted {len(text)} chars from {os.path.basename(pdf)} ---")
            # print(text[:200] + "...")
            
            result = await extract_load_json(client, model, text)
            print(f"Result for {os.path.basename(pdf)}:")
            print(result)
            print("-" * 40)
        except Exception as e:
            print(f"Error on {pdf}: {e}")

asyncio.run(main())
