import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import quote

# Load environment variables from .env
load_dotenv()

# Airtable config – ensure table name is exactly as defined in Airtable
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

# Flxpoint config – ensure this token has source-level permissions for fulfillment data
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# Vendors (source names exactly as expected)
VENDORS = ["DNA", "Muscle Food"]

def get_fulfillment_data_for_vendor(vendor):
    """
    Retrieves fulfillment requests for a vendor over the past 7 days.
    This call uses the query parameter "sourceName" so that the API returns
    only the records for that vendor.
    """
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "status": "Completed",
        "sourceName": vendor
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
        data = response.json()  # Expecting an array (list) of records
        print(f"✅ Successfully parsed JSON for {vendor} (records: {len(data)})")
    except Exception as e:
        print(f"❌ Failed to parse JSON for {vendor}: {e}")
        print("🔍 Raw response:", response.text)
        return None
    
    return data

def compute_vendor_totals(fulfillment_data):
    """
    Given a list of fulfillment request records, sum the ordered and shipped quantities.
    We assume each record contains:
      - "totalQuantity": total units ordered in that request
      - "shippedQuantity": units actually shipped
    """
    total_ordered = 0
    total_shipped = 0
    for record in fulfillment_data:
        total_ordered += record.get("totalQuantity", 0)
        total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes a record to Airtable. The table is expected to have these columns:
      - Vendor (single select)
      - Ordered QTY (number)
      - Shipped QTY (number)
      - Fill Rate (percentage as a decimal; e.g., 0.9 for 90%)
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
    for vendor in VENDORS:
        fulfillment_data = get_fulfillment_data_for_vendor(vendor)
        if fulfillment_data is None:
            print(f"⚠️ No fulfillment data returned for {vendor}")
            continue
        ordered, shipped = compute_vendor_totals(fulfillment_data)
        fill_rate = round(shipped / ordered, 4) if ordered > 0 else 0.0
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate*100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)

if __name__ == "__main__":
    main()
