import pytesseract
from pdf2image import convert_from_path

pdf = "/home/no_one/Downloads/Signed Carrier Rate Confirmation-Thu_14_May_2026_064042PM-1010399.pdf"
images = convert_from_path(pdf)
text = ""
for img in images:
    text += pytesseract.image_to_string(img) + "\n"
print(text)
