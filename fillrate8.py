import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import quote

# Load environment variables from .env
load_dotenv()

# Airtable config
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)  # URL-encode the table name in case it contains spaces

# Flxpoint config
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendors to track – exactly as they appear in Flxpoint
VENDORS = ["DNA", "Muscle Food"]

def get_fulfillment_data_for_vendor(vendor):
    """
    Calls Flxpoint's v2 API to retrieve fulfillment requests for a given vendor.
    (This endpoint is assumed to be 'GET /fulfillment-requests' and supports filtering by sourceName and status.)
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "sourceName": vendor,
        "status": "Completed"  # Adjust status filter as needed
    }
    # The correct endpoint based on Flxpoint v2 docs for fulfillment data is assumed to be below.
    url = "https://api.flxpoint.com/fulfillment-requests"
    print(f"\n📦 Requesting fulfillment data for vendor: {vendor}")
    print("🔗 URL:", url)
    print("📤 Params:", params)
    
    response = requests.get(url, headers=headers, params=params)
    print("🔄 Status Code:", response.status_code)
    
    if response.status_code != 200:
        print(f"❌ Flxpoint API Error for {vendor}:", response.text)
        return None
    
    try:
        data = response.json().get("data", [])
        print(f"✅ Successfully parsed JSON for {vendor}")
    except Exception as e:
        print(f"❌ JSON parse error for {vendor}: {e}")
        print("🔍 Raw response:", response.text)
        return None
    return data

def compute_vendor_totals(fulfillment_data):
    """
    Loops through the returned fulfillment requests and aggregates ordered and shipped quantities.
    
    Expected JSON structure per fulfillment request (simplified):
    {
       "id": ...,
       "sourceName": "DNA",
       "lineItems": [
           { "sku": "...", "quantity": 10, "quantityShipped": 9 },
           { ... }
       ],
       ... other fields ...
    }
    """
    total_ordered = 0
    total_shipped = 0
    for fulfillment in fulfillment_data:
        line_items = fulfillment.get("lineItems", [])
        for item in line_items:
            total_ordered += item.get("quantity", 0)
            total_shipped += item.get("quantityShipped", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes the vendor's fill rate data to Airtable. The table is expected to have these columns:
      - Vendor (single select)
      - Ordered QTY (number)
      - Shipped QTY (number)
      - Fill Rate (percentage; value expressed as 0.0–1.0)
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
    overall_totals = {}
    
    # Iterate through each vendor, retrieve fulfillment data, and compute totals.
    for vendor in VENDORS:
        fulfillment_data = get_fulfillment_data_for_vendor(vendor)
        if not fulfillment_data:
            print(f"⚠️ No fulfillment data returned for {vendor}")
            continue
        
        ordered, shipped = compute_vendor_totals(fulfillment_data)
        fill_rate = round(shipped / ordered, 4) if ordered else 0.0
        overall_totals[vendor] = {"ordered": ordered, "shipped": shipped, "fill_rate": fill_rate}
        
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate * 100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)
    
    if not overall_totals:
        print("⚠️ No vendor data collected.")

if __name__ == "__main__":
    main()
