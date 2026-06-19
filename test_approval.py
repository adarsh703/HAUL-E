import os
import asyncio
from services.twilio_sms import send_whatsapp
from database.models import Load, AsyncSessionLocal

async def mock_approval():
    dispatcher_num = os.getenv("DISPATCHER_PHONE") or os.getenv("DRIVER_TEST_PHONE", "+919893602351")
    async with AsyncSessionLocal() as session:
        new_load = Load(
            load_id="#MOCK-9999",
            origin_dest="Nampa, ID -> Laredo, TX",
            pickup_date="2026-06-16",
            driver='Test Driver',
            rate="3000",
            status='Awaiting Approval',
            document_url="",
            operational_intelligence="{}",
            shipper_email="studadarsh17@gmail.com",
            hard_copy_pod_required=False,
            driver_phone=os.getenv("DRIVER_TEST_PHONE", "+919893602351"),
            dispatcher_phone=dispatcher_num,
            temp_check_active=True,
        )
        session.add(new_load)
        await session.commit()
    
    msg = (
        f"🚨 *HAUL-E Auto-Dispatch*\n"
        f"New RC detected: #MOCK-9999\n"
        f"📍 Route: Nampa, ID -> Laredo, TX\n"
        f"💵 Rate: $3000\n\n"
        f"Do you want to create this load and assign it to Test Driver?\n"
        f"Reply *APPROVE* to confirm."
    )
    await send_whatsapp(dispatcher_num, msg)
    print("Mock approval sent!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(mock_approval())
