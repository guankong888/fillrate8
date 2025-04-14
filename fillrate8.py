import os
import requests
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

headers = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

print("🔍 Testing Airtable connection...")
print("→ URL:", url)
print("→ Token begins with:", AIRTABLE_TOKEN[:10])

# Just do a GET request (no write) to test permissions
response = requests.get(url, headers=headers)

print("Status Code:", response.status_code)
print("Response Body:")
print(response.text)
