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

# Flxpoint configuration (your token must have appropriate (source-level) permissions)
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendors to track and their known source IDs
vendor_source_ids = {
    "DNA": 212291,         # Example: DNA's sourceId from your sample record
    "Muscle Food": 212292  # Replace 212292 with the correct sourceId for Muscle Food
}

# Vendors list (keys of our mapping)
VENDORS = list(vendor_source_ids.keys())

def get_fulfillment_data():
    """
    Retrieves all fulfillment requests (for all sources) over the past 7 days.
    We don’t filter by vendor in the query so that we get all records and then we
    filter manually using our vendor_source_ids mapping.
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "status": "Completed"  # Adjust as needed
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
        data = response.json()  # Expect an array (list) of fulfillment request objects
        print(f"✅ Successfully parsed JSON response (records: {len(data)})")
        # Debug: print a sample record to see available fields
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
    Sums up the ordered and shipped quantities for a given vendor.
    We use our vendor_source_ids mapping to filter records:
      - Only include records whose "sourceId" equals the desired ID.
    
    This function uses the top-level keys "totalQuantity" and "shippedQuantity"
    from each fulfillment request record.
    """
    total_ordered = 0
    total_shipped = 0
    desired_source_id = vendor_source_ids.get(vendor)
    for record in fulfillment_data:
        # Use sourceId from each record (if missing, default to None)
        rec_source_id = record.get("sourceId")
        if rec_source_id != desired_source_id:
            continue
        total_ordered += record.get("totalQuantity", 0)
        total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes the vendor's fill rate data to Airtable.
    The table is expected to have fields:
      - Vendor (single select)
      - Ordered QTY (number)
      - Shipped QTY (number)
      - Fill Rate (as a decimal, e.g., 0.9 for 90%)
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
