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
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

# Flxpoint configuration (token must have access to fulfillment data)
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendors to track (as expected from the API)
VENDORS = ["DNA", "Muscle Food"]

def get_fulfillment_data():
    """
    Retrieves all fulfillment requests for the past 7 days.
    (We expect an array of records.)
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "status": "Completed"
        # Not filtering by sourceName here, so that we can debug vendor values manually.
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
        data = response.json()
        print(f"✅ Successfully parsed JSON response (records: {len(data)})")
        # For debugging, print out one sample record’s keys and a snippet:
        if data:
            print("🔍 Sample record:")
            print(json.dumps(data[0], indent=2)[:500])
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        print("🔍 Raw response:", response.text)
        return []
    return data

def compute_vendor_totals(fulfillment_data, vendor):
    """
    Filter fulfillment_data for records that belong to the given vendor.
    We assume that each record may contain a nested object or key that tells you the vendor.
    For example, if the record includes {"source": {"name": "DNA"}}, we use that; otherwise,
    you might need to adjust this function.
    
    Here we sum over each record’s line items if available.
    """
    total_ordered = 0
    total_shipped = 0
    for record in fulfillment_data:
        # Attempt to determine the vendor for this record.
        # First, check if a nested "source" object exists.
        rec_vendor = None
        if "source" in record and isinstance(record["source"], dict):
            rec_vendor = record["source"].get("name")
        # Alternatively, if there's a top-level key "sourceName", use that.
        elif "sourceName" in record:
            rec_vendor = record["sourceName"]
        # Otherwise, as a fallback, use the sourceId (converted to string)
        else:
            rec_vendor = str(record.get("sourceId", ""))
        
        # Skip records that do not match the vendor.
        if rec_vendor != vendor:
            continue
        
        # Instead of using the top-level totals (which might be aggregated differently),
        # sum through the "fulfillmentRequestItems" if available.
        if "fulfillmentRequestItems" in record and isinstance(record["fulfillmentRequestItems"], list):
            for item in record["fulfillmentRequestItems"]:
                total_ordered += item.get("quantity", 0)
                total_shipped += item.get("shippedQuantity", 0)
        else:
            # Fallback: use top-level totals.
            total_ordered += record.get("totalQuantity", 0)
            total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes a record to Airtable.
    The table is expected to have fields:
      - Vendor (single select)
      - Ordered QTY (number)
      - Shipped QTY (number)
      - Fill Rate (percentage as a decimal)
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
    data = get_fulfillment_data()
    if not data:
        print("⚠️ No fulfillment data returned from Flxpoint.")
        return

    for vendor in VENDORS:
        ordered, shipped = compute_vendor_totals(data, vendor)
        fill_rate = round((shipped / ordered), 4) if ordered > 0 else 0.0
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate*100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)

if __name__ == "__main__":
    main()
