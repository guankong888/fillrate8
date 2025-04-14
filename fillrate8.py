import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env
load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

# Define test data
data = {
    "records": [
        {
            "fields": {
                "Vendor": "MF",
                "Ordered QTY": 300,
                "Shipped QTY": 270,
                "% Fill Rate": 0.9,  # Airtable will show as 90% if field is percent
                "Week": "2025-04-07"
            }
        }
    ]
}

# Build Airtable API request
url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
headers = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# Send the request
response = requests.post(url, headers=headers, json=data)

# Handle result
if response.status_code == 200:
    print("✅ Airtable push successful:", response.json())
else:
    print("❌ Error:", response.status_code, response.text)
