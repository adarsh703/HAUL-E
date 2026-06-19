"""
Quick test script — sends a test SMS to your personal number via Twilio.
Run: python test_twilio.py
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from services.twilio_sms import send_sms, send_load_details_to_driver

# Test with a simple SMS first
async def main():
    test_phone = os.getenv("DRIVER_TEST_PHONE", "+919893602351")
    
    print(f"📱 Sending test SMS to {test_phone}...")
    try:
        sid = await send_sms(test_phone, "🚛 HAUL-E Bot is online! This is a test message from Mor Logistics Manitoba Ltd.")
        print(f"✅ SMS sent successfully! SID: {sid}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return

    # Test with a mock load dispatch
    print(f"\n📋 Sending mock load dispatch to {test_phone}...")
    mock_load_data = {
        "load_information": {
            "broker_load_number": "TEST-001",
            "customer": "Test Broker Inc.",
            "equipment_type": "Reefer 53'",
            "commodity": "Frozen Chicken",
            "weight": "42,000 lbs",
            "temperature_requirements": "-10°F"
        },
        "stops": [
            {
                "stop_type": "Pickup",
                "company_name": "Tyson Foods Distribution",
                "address": "456 Industrial Blvd",
                "city_state": "Springdale, AR",
                "appointment_date": "June 16, 2026",
                "appointment_time": "08:00 AM",
                "instructions": "Check in at guard shack. Lumper on site."
            },
            {
                "stop_type": "Delivery",
                "company_name": "Sysco Toronto DC",
                "address": "789 Logistics Pkwy",
                "city_state": "Toronto, ON",
                "appointment_date": "June 18, 2026",
                "appointment_time": "06:00 AM",
                "instructions": "Dock 12. Temp printout required."
            }
        ],
        "reefer_operations": {
            "temperature_setpoint": "-10°F",
            "continuous_mode": True,
            "pre_cool_required": True
        }
    }

    try:
        sid = await send_load_details_to_driver(test_phone, mock_load_data)
        print(f"✅ Load dispatch sent! SID: {sid}")
    except Exception as e:
        print(f"❌ Failed: {e}")

asyncio.run(main())
