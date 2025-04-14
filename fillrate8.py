import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import quote
import json

# Load environment variables from .env
load_dotenv()

# Airtable configuration
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)  # URL-encode in case of spaces

# Flxpoint configuration
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendor mapping using provided source IDs:
vendor_source_ids = {
    "Muscle Food": 210740,
    "DNA": 992648
}
VENDORS = list(vendor_source_ids.keys())

def get_fulfillment_data():
    """
    Retrieves all fulfillment requests for the past 7 days from Flxpoint.
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "status": "Completed"
    }
    url = "https://api.flxpoint.com/fulfillment-requests"
    print(f"\n📦 Requesting fulfillment data from {params['startDate']} to {params['endDate']}")
    print("🔗 URL:", url)
    print("📤 Params:", params)
    
    response = requests.get(url, headers=headers, params=params)
    print("🔄 Status Code:", response.status_code)
    if response.status_code != 200:
        print("❌ Flxpoint API Error:", response.text)
        return []
    
    try:
        data = response.json()  # Expecting a JSON array
        print(f"✅ Successfully parsed JSON response (records: {len(data)})")
        if data:
            print("🔍 Sample record:")
            # Print a snippet of the first record to check available keys.
            print(json.dumps(data[0], indent=2)[:500])
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        print("🔍 Raw response:", response.text)
        return []
    
    return data

def compute_vendor_totals(fulfillment_data, vendor):
    """
    For the given vendor, sum the total ordered and shipped quantities.
    We filter using our vendor_source_ids mapping (matching the record's sourceId).
    """
    total_ordered = 0
    total_shipped = 0
    desired_source_id = vendor_source_ids.get(vendor)
    
    for record in fulfillment_data:
        # Check if record's sourceId matches our desired source id.
        if record.get("sourceId") != desired_source_id:
            continue
        # Sum the top-level totals. (Adjust these keys if needed.)
        total_ordered += record.get("totalQuantity", 0)
        total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes vendor data to Airtable. The Airtable table is assumed to have:
      - Vendor (single select)
      - Ordered QTY (number)
      - Shipped QTY (number)
      - Fill Rate (percentage stored as a decimal, e.g. 0.9 for 90%)
      - Week (text)
    """
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{encoded_table_name}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "records": [
            {
                "fields": {
                    "Vendor": vendor,
                    "Ordered QTY": ordered,
                    "Shipped QTY": shipped,
                    "Fill Rate": fill_rate,
                    "Week": week_str
                }
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"✅ Pushed to Airtable for {vendor}")
    else:
        print(f"❌ Airtable Error for {vendor}:", response.status_code, response.text)

def main():
    week_str = datetime.now().strftime("%Y-%m-%d")
    fulfillment_data = get_fulfillment_data()
    if not fulfillment_data:
        print("⚠️ No fulfillment data returned from Flxpoint.")
        return

    for vendor in VENDORS:
        ordered, shipped = compute_vendor_totals(fulfillment_data, vendor)
        fill_rate = round(shipped / ordered, 4) if ordered > 0 else 0.0
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate*100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)

if __name__ == "__main__":
    main()
