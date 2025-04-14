import os
from dotenv import load_dotenv
from utils.airtable_client import upsert_fill_rate

load_dotenv()  # Load .env credentials

# Sample test data
vendor = "MF"
ordered_qty = 200
shipped_qty = 180
fill_rate = 0.9  # 90%
week_str = "2025-04-07"

# Push to Airtable
response = upsert_fill_rate(vendor, ordered_qty, shipped_qty, fill_rate, week_str)
print("✅ Airtable push successful:", response)
