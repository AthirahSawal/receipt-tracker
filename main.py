from PIL import Image
import pytesseract
import re

# Path to Tesseract executable (update if installed somewhere else)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load the image
image_path = 'sample.jpg'  # Replace with your image name
img = Image.open(image_path)

# Extract text using Tesseract OCR
text = pytesseract.image_to_string(img)

print("=== Full OCR Text ===")
print(text)

# --- Extract Shop Name (assume first non-empty line) ---
lines = [line.strip() for line in text.split('\n') if line.strip()]

# Smarter Shop Name Detection
shop_name = "Not found"
for line in lines[:10]:  # Look at the first 10 lines
    clean_line = re.sub(r'[^A-Za-z0-9\s&]', '', line)  # Remove symbols
    word_count = len(clean_line.split())
    if word_count >= 2 and len(clean_line) >= 5:
        shop_name = clean_line.strip()
        break

# --- Extract Date (e.g., 05/06/2025 or 2025-06-05) ---
date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})', text)
date = date_match.group(0) if date_match else "Not found"

# --- Extract Prices (decimal format only) ---
prices = re.findall(r'\d+\.\d{2}', text)

# --- Extract Item Lines (lines with price but not keywords like "cash") ---
ignore_keywords = ['cash', 'change', 'total', 'subtotal', 'payment', 'balance', 'tax']
items = []

for line in lines:
    if re.search(r'\d+\.\d{2}', line):
        lower_line = line.lower()
        if not any(keyword in lower_line for keyword in ignore_keywords):
            items.append(line)

# --- Clean item lines ---
def clean_item_line(line):
    # Remove the pattern like "1 BE" (number + letters)
    line = re.sub(r'\b\d+\s+[A-Za-z]+\b', '', line)

    # Find the price (decimal number)
    price_match = re.search(r'(\d+\.\d{2})', line)
    price = price_match.group(1) if price_match else ''

    # Remove original price from line
    line = re.sub(r'\d+\.\d{2}', '', line).strip()

    # Return cleaned line with price and $ sign
    if price:
        return f"{line} ${price}"
    else:
        return line.strip()

cleaned_items = [clean_item_line(item) for item in items]

# --- Output Results ---
print("\n=== Extracted Info ===")
print(f"Shop Name: {shop_name}")
print(f"Date: {date}")
print("Prices found:", prices)
print("Items:")
for ci in cleaned_items:
    print(f" - {ci}")
