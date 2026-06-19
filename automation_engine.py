import sqlite3
import time
import json
import logging
from datetime import datetime
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("HAUL-E-Automation")

DB_PATH = 'bot_database.db'

# ==========================================
# PLACEHOLDERS (API Keys needed from you)
# ==========================================
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_SID_HERE"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_TOKEN_HERE"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+1234567890"

# Gmail SMTP Credentials
GMAIL_ADDRESS = "cavemann177@gmail.com"  # Put your email here
GMAIL_APP_PASSWORD = "sljggszdwxlrlrju" # Put your 16-digit app password here

# ==========================================
# DATABASE HELPERS
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# 1. DISPATCH AUTOMATION (SMS)
# ==========================================
def run_dispatch_automation():
    """
    Finds NEW/Pending loads and automatically texts an available driver.
    """
    logger.info("Running Dispatch Automation...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Find loads that haven't been dispatched yet
    cur.execute("SELECT * FROM loads WHERE status = 'Pending'")
    loads = cur.fetchall()
    
    for load in loads:
        load_id = load['load_id']
        rate = load['rate']
        route = load['origin_dest']
        intel = json.loads(load['operational_intelligence']) if load['operational_intelligence'] else {}
        
        # --- MOCK DRIVER ASSIGNMENT ---
        # In the future, this will query the 'vehicles' table for the closest empty driver
        assigned_driver = "John Doe"
        driver_phone = "+15550199999" # Placeholder
        
        # --- GENERATE WHATSAPP MESSAGE WITH BUTTONS ---
        # The WhatsApp Business API allows interactive buttons!
        pickup_info = intel.get("stops", [{}])[0].get("company_name", "Shipper")
        dropoff_info = intel.get("stops", [-1])[0].get("company_name", "Receiver") if len(intel.get("stops", [])) > 1 else "Receiver"
        
        msg_body = (
            f"🚛 *HAUL-E DISPATCH*\\n\\n"
            f"*Route:* {route}\\n"
            f"*Rate:* {rate}\\n"
            f"*Pickup:* {pickup_info}\\n"
            f"*Dropoff:* {dropoff_info}\\n\\n"
            f"Tap below to accept or decline:"
        )
        
        # --- SEND WHATSAPP (Twilio API Call) ---
        logger.info(f"[WHATSAPP -> {assigned_driver}]: Sent Load Details with ACCEPT/DECLINE buttons.")
        # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     from_=TWILIO_WHATSAPP_NUMBER,
        #     body=msg_body,
        #     to=f"whatsapp:{driver_phone}",
        #     # Note: Twilio uses Content Templates for WhatsApp buttons in production
        # )
        
        # --- UPDATE DATABASE ---
        # We instantly mark it as dispatched (assuming they auto-accept for this demo)
        cur.execute("UPDATE loads SET status = 'Dispatched', driver = ? WHERE id = ?", (assigned_driver, load['id']))
        conn.commit()
        logger.info(f"Load {load_id} successfully auto-dispatched to {assigned_driver}.")
        
    conn.close()

# ==========================================
# 2. BROKER TRACKING AUTOMATION (EMAIL)
# ==========================================
def run_tracking_automation():
    """
    Sends automated ETA / Location updates to the broker email.
    """
    logger.info("Running Broker Tracking Automation...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM loads WHERE status = 'Dispatched' OR status = 'In Transit'")
    loads = cur.fetchall()
    
    for load in loads:
        load_id = load['load_id']
        route = load['origin_dest']
        intel = json.loads(load['operational_intelligence']) if load['operational_intelligence'] else {}
        
        # --- EXTRACT BROKER EMAIL ---
        broker_email = None
        # Try to find an email in the intel
        refs = intel.get("references", {})
        # For this demo, we'll just mock a broker email if we don't find one
        broker_email = "broker@example.com" 
        
        # --- GET GPS LOCATION ---
        # In the future, ping Samsara/Motive API here
        current_location = "En Route - GPS Placeholder" 
        
        # --- GENERATE EMAIL ---
        subject = f"Tracking Update: Load {load_id} ({route})"
        body = f"""
        Good morning,
        
        Here is the automated location update for your load.
        
        Load Number: {load_id}
        Status: {load['status']}
        Current Location: {current_location}
        
        We will notify you immediately once the driver arrives at the receiver.
        
        Thank you,
        HAUL-E Automated Dispatch
        """
        
        # --- SEND EMAIL (Using Gmail SMTP) ---
        logger.info(f"[EMAIL -> {broker_email}]: {subject}")
        # try:
        #     import smtplib
        #     from email.mime.text import MIMEText
        #     msg = MIMEText(body)
        #     msg['Subject'] = subject
        #     msg['From'] = GMAIL_ADDRESS
        #     msg['To'] = broker_email
        #
        #     with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        #         server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        #         server.send_message(msg)
        #     logger.info("Email sent successfully via Gmail!")
        # except Exception as e:
        #     logger.error(f"Failed to send email: {e}")
        
        # Note: We don't update the status here, it stays In Transit until delivered.

# ==========================================
# 3. AUTOMATED 3-HOUR CHECK CALLS (DRIVER REMINDERS)
# ==========================================
def run_check_call_automation():
    """
    Sends an automated SMS to the driver every 3 hours asking for a status update,
    UNLESS we already have live GPS from Samsara/Motive.
    """
    logger.info("Running 3-Hour Check Call Automation...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM loads WHERE status = 'Dispatched' OR status = 'In Transit'")
    loads = cur.fetchall()
    
    for load in loads:
        load_id = load['load_id']
        driver_phone = "+15550199999" # Mock driver phone
        
        # MOCK LOGIC: Check if 3 hours have passed since the last text
        # In production, we query a 'last_contacted' timestamp from the database
        three_hours_passed = True 
        
        if three_hours_passed:
            sms_body = (
                f"HAUL-E UPDATE REQUIRED:\\n"
                f"Load {load_id} - Reply with your current City/State\\n"
                f"or reply 'AT PICKUP', 'LOADED', 'AT DELIVERY', 'EMPTY'."
            )
            logger.info(f"[3-HOUR SMS -> Driver {driver_phone}]: {sms_body}")
            # client.messages.create(body=sms_body, from_=TWILIO_PHONE_NUMBER, to=driver_phone)
            
            # Update 'last_contacted' timestamp in database here
            
    conn.close()

# ==========================================
# 4. BILLING / INVOICING AUTOMATION
# ==========================================
def run_billing_automation():
    """
    Generates PDF Invoice and emails it to factoring once delivered.
    """
    logger.info("Running Billing Automation...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM loads WHERE status = 'Delivered'")
    loads = cur.fetchall()
    
    for load in loads:
        load_id = load['load_id']
        rate = load['rate']
        
        # --- GENERATE PDF (Placeholder) ---
        # In reality, we use ReportLab or wkhtmltopdf to render an invoice template
        pdf_filename = f"Invoice_{load_id}.pdf"
        logger.info(f"Generating PDF Invoice: {pdf_filename} for {rate}...")
        # create_pdf(pdf_filename, load_data)
        
        # --- SEND EMAIL TO FACTORING ---
        subject = f"New Invoice - Load {load_id}"
        logger.info(f"[EMAIL -> {FACTORING_COMPANY_EMAIL}]: Attached {pdf_filename}")
        
        # --- UPDATE STATUS TO INVOICED ---
        cur.execute("UPDATE loads SET status = 'Invoiced' WHERE id = ?", (load['id'],))
        conn.commit()
        logger.info(f"Load {load_id} successfully auto-invoiced.")
        
    conn.close()

# ==========================================
# MAIN LOOP
# ==========================================
def start_engine():
    logger.info("HAUL-E Automation Engine Started. Waiting for tasks...")
    while True:
        try:
            run_dispatch_automation()
            run_tracking_automation()
            run_check_call_automation()
            run_billing_automation()
        except Exception as e:
            logger.error(f"Error in automation loop: {e}")
            
        # Run every 60 seconds (for testing). In production, this might be every 5 mins.
        time.sleep(60)

if __name__ == "__main__":
    start_engine()
