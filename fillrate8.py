import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import quote

# Load environment variables from .env
load_dotenv()

# Airtable configuration
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

# Flxpoint configuration
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendors to track (as they appear in Flxpoint)
VENDORS = ["DNA", "Muscle Food"]

def get_fulfillment_data_for_vendor(vendor):
    """
    Retrieves fulfillment request data for the vendor from Flxpoint.
    We use the endpoint for fulfillment requests and pass a query parameter
    to filter by source name and status.
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "sourceName": vendor,
        "status": "Completed"  # Adjust this filter if needed
    }
    
    url = "https://api.flxpoint.com/fulfillment-requests"
    print(f"\n📦 Requesting fulfillment data for vendor: {vendor}")
    print("🔗 URL:", url)
    print("📤 Params:", params)
    
    response = requests.get(url, headers=headers, params=params)
    print(f"🔄 Status Code ({vendor}):", response.status_code)
    
    if response.status_code != 200:
        print(f"❌ Flxpoint API Error for {vendor}:", response.text)
        return None
    
    try:
        # Expecting the API to return a JSON array (list)
        fulfillments = response.json()  
        print(f"✅ Successfully parsed JSON for {vendor}")
    except Exception as e:
        print(f"❌ Failed to parse JSON for {vendor}: {e}")
        print("🔍 Raw response:")
        print(response.text)
        return None
    
    return fulfillments

def compute_vendor_totals(fulfillment_data):
    """
    Sums the overall ordered (totalQuantity) and shipped (shippedQuantity)
    quantities from each fulfillment request record.
    """
    total_ordered = 0
    total_shipped = 0
    for fulfillment in fulfillment_data:
        total_ordered += fulfillment.get("totalQuantity", 0)
        total_shipped += fulfillment.get("shippedQuantity", 0)
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
    vendor_results = {}
    
    for vendor in VENDORS:
        fulfillment_data = get_fulfillment_data_for_vendor(vendor)
        if fulfillment_data is None:
            print(f"⚠️ No fulfillment data returned for {vendor}")
            continue
        
        # Compute totals using top-level keys
        ordered, shipped = compute_vendor_totals(fulfillment_data)
        fill_rate = round(shipped / ordered, 4) if ordered else 0.0
        
        vendor_results[vendor] = {
            "ordered": ordered,
            "shipped": shipped,
            "fill_rate": fill_rate
        }
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate * 100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)
    
    if not vendor_results:
        print("⚠️ No vendor data collected.")

if __name__ == "__main__":
    main()
