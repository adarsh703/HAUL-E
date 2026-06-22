import os
from datetime import datetime
import pytz

TORONTO_TZ = pytz.timezone('America/Toronto')
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def generate_invoice(load_id: str, broker_name: str, origin_dest: str, rate: str, date: str) -> str:
    """
    Generates a PDF invoice for a completed load.
    Returns the file path to the generated PDF.
    """
    os.makedirs("invoices", exist_ok=True)
    file_path = f"invoices/Invoice_{load_id.replace('#', '')}.pdf"
    
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Mor Logistics Manitoba Ltd")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, "sales@morlogistics.ca")
    c.drawString(50, height - 85, "MC #1420840")
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(450, height - 50, "INVOICE")
    
    # Invoice Details
    c.setFont("Helvetica", 12)
    c.drawString(450, height - 80, f"Date: {datetime.now(TORONTO_TZ).strftime('%b %d, %Y')}")
    c.drawString(450, height - 100, f"Invoice #: INV-{load_id.replace('#', '')}")
    
    # Bill To
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 140, "Bill To:")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 160, broker_name)
    
    # Table Header
    c.setFillColor(colors.lightgrey)
    c.rect(50, height - 220, 500, 30, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, height - 210, "Load ID")
    c.drawString(150, height - 210, "Lane (Origin → Destination)")
    c.drawString(400, height - 210, "Pickup Date")
    c.drawString(500, height - 210, "Amount")
    
    # Table Row
    c.setFont("Helvetica", 12)
    c.drawString(60, height - 240, load_id)
    c.drawString(150, height - 240, origin_dest)
    c.drawString(400, height - 240, date)
    c.drawString(500, height - 240, f"${rate}")
    
    # Total
    c.line(50, height - 260, 550, height - 260)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, height - 290, "Total Due:")
    c.drawString(500, height - 290, f"${rate}")
    
    # Footer
    c.setFont("Helvetica", 10)
    c.drawString(50, 50, "Thank you for your business. Please remit payment within 30 days.")
    c.drawString(50, 35, "Please see the attached Bill of Lading (BOL) as Proof of Delivery.")
    
    c.save()
    return file_path
