import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import quote

# Load environment variables from .env
load_dotenv()

# Airtable configuration
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)  # URL-encode the table name

# Flxpoint configuration (ensure your token has source-level permissions)
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendors to track (as they appear in the Flxpoint data)
VENDORS = ["DNA", "Muscle Food"]

def get_fulfillment_data():
    """
    Retrieves fulfillment requests from Flxpoint for the past 7 days.
    We use the endpoint that returns all fulfillment requests and rely on manual filtering.
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        # Even if we pass a filter (e.g. "sourceName"), it appears the API returns all records.
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
        # Expecting an array/list of fulfillment request objects
        data = response.json()
        print("✅ Successfully parsed JSON response (total records:", len(data), ")")
    except Exception as e:
        print("❌ Failed to parse JSON:", str(e))
        print("🔍 Raw response:")
        print(response.text)
        return []
    
    return data

def compute_vendor_totals(fulfillment_data, vendor):
    """
    Filter the list of fulfillment requests to only those for the given vendor (by checking the 'sourceName' key)
    and sum their ordered and shipped quantities.
    
    We assume each fulfillment record includes:
      - "totalQuantity": the ordered quantity for that request
      - "shippedQuantity": the units actually shipped
    """
    total_ordered = 0
    total_shipped = 0
    for record in fulfillment_data:
        # Check the sourceName (if the API returns it; adjust if your field name is different)
        if record.get("sourceName") != vendor:
            continue
        total_ordered += record.get("totalQuantity", 0)
        total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes the vendor's fill rate data to Airtable.
    Expected Airtable fields:
      - Vendor (single select)
      - Ordered QTY (number)
      - Shipped QTY (number)
      - Fill Rate (percentage, expressed as a decimal, e.g. 0.9 for 90%)
      - Week (single line text)
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
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate * 100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)

if __name__ == "__main__":
    main()
