import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{encoded_table_name}"
headers = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# Define test data
data = {
    "records": [
        {
            "fields": {
                "Vendor": "MF",
                "Ordered QTY": 300,
                "Shipped QTY": 270,
                "% Fill Rate": 0.9,
                "Week": "2025-04-07"
            }
        }
    ]
}

# POST to Airtable
response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("✅ Airtable push successful:")
    print(response.json())
else:
    print("❌ Error:", response.status_code, response.text)
