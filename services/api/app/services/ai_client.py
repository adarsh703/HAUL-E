from google import genai
from google.oauth2 import service_account
from app.config import settings
import os

_VERTEX_SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
_client = None

def get_gemini_client():
    global _client
    if _client is None:
        creds_file = settings.GOOGLE_CREDENTIALS_FILE
        if os.path.isfile(creds_file):
            creds = service_account.Credentials.from_service_account_file(creds_file, scopes=_VERTEX_SCOPES)
            _client = genai.Client(vertexai=True, project=settings.GOOGLE_PROJECT_ID, location=settings.GOOGLE_LOCATION, credentials=creds)
        else:
            _client = genai.Client(vertexai=True, project=settings.GOOGLE_PROJECT_ID, location=settings.GOOGLE_LOCATION)
    return _client
