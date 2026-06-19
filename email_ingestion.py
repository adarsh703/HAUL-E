import imaplib
import email
import os
import time
import logging
from datetime import datetime
# Assuming document_ocr is imported from your discord bot logic
# from cogs.document_ocr import process_document_with_ai 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HAUL-E-Email-Ingestion")

# ==========================================
# EMAIL CREDENTIALS (Placeholder)
# ==========================================
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "loads@yourcompany.com"
EMAIL_PASSWORD = "YOUR_APP_PASSWORD"

# ==========================================
# DOCUMENT VAULT SETUP
# ==========================================
VAULT_DIR = "/home/no_one/Desktop/broker-bot/document_vault"
if not os.path.exists(VAULT_DIR):
    os.makedirs(VAULT_DIR)

def save_attachment(msg, load_id_hint="NEW"):
    """
    Saves the PDF attachment into the unified Document Vault.
    """
    saved_paths = []
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
            continue
            
        filename = part.get_filename()
        if filename and filename.lower().endswith('.pdf'):
            # Create a dedicated folder for this load
            load_folder = os.path.join(VAULT_DIR, f"LOAD_{load_id_hint}")
            if not os.path.exists(load_folder):
                os.makedirs(load_folder)
                
            # Save the file (e.g., RateCon.pdf, BOL.pdf, POD.pdf)
            filepath = os.path.join(load_folder, f"RC_{filename}")
            with open(filepath, 'wb') as f:
                f.write(part.get_payload(decode=True))
            
            logger.info(f"Document saved securely in vault: {filepath}")
            saved_paths.append(filepath)
            
    return saved_paths

def check_inbox():
    """
    Connects to the email server, finds unread Rate Confirmations, downloads them, 
    and sends them to the Intelligence Layer.
    """
    logger.info("Checking inbox for new Rate Confirmations...")
    try:
        # NOTE: This is mocked for safety until real credentials are provided
        # mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        # mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        # mail.select('inbox')
        # status, messages = mail.search(None, 'UNSEEN')
        
        # MOCKING AN INCOMING EMAIL
        mock_has_new_email = False 
        
        if mock_has_new_email:
            logger.info("Found 1 new email from Broker!")
            # 1. Download Attachment to Vault
            # vault_path = save_attachment(msg, "TEMP_123")
            
            # 2. Send to AI Intelligence Layer (Just like Discord did)
            # intel = process_document_with_ai(vault_path)
            
            # 3. Save to Database
            # save_to_db(intel, vault_path)
            pass
            
    except Exception as e:
        logger.error(f"Error checking email: {e}")

def start_ingestion_loop():
    logger.info("HAUL-E Email Ingestion Started. Listening for RCs...")
    while True:
        check_inbox()
        time.sleep(30) # Check every 30 seconds

if __name__ == "__main__":
    start_ingestion_loop()
