import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import quote

# Load environment variables
load_dotenv()

# Airtable configuration
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

# Flxpoint configuration
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")

# OPTIONAL: A mapping from sourceId to your friendly vendor names.
# Update or add to this mapping as you learn which sourceId corresponds to what.
# (From your sample record we see 212291—currently not mapped.)
source_id_to_vendor = {
    # Example: if you know 212291 should be labeled as "DNA" or "Muscle Food",
    # update accordingly. For now, we'll leave it unmapped.
    # 210740: "Muscle Food",
    # 992648: "DNA"
}

def get_fulfillment_data():
    """
    Retrieves all fulfillment requests for the past 7 days (status: Completed).
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
        data = response.json()  # expecting a list of fulfillment requests
        print(f"✅ Successfully parsed JSON response (records: {len(data)})")
        if data:
            print("🔍 Sample record:")
            # Print first 500 characters for inspection
            print(json.dumps(data[0], indent=2)[:500])
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        print("🔍 Raw response:", response.text)
        return []
    return data

def group_fulfillments_by_source(fulfillment_data):
    """
    Groups the fulfillment requests by their 'sourceId'.
    Returns a dictionary mapping sourceId to a list of records.
    """
    groups = {}
    for record in fulfillment_data:
        src_id = record.get("sourceId")
        if src_id is None:
            continue
        groups.setdefault(src_id, []).append(record)
    print("🗂 Unique source IDs in returned data:", list(groups.keys()))
    return groups

def compute_totals_for_group(records):
    """
    Sums the ordered and shipped quantities from a list of fulfillment request records.
    If a record contains a 'fulfillmentRequestItems' array, we iterate through each item
    and sum its 'quantity' and 'shippedQuantity'. Otherwise, we fall back on top-level keys.
    """
    total_ordered = 0
    total_shipped = 0
    for record in records:
        if "fulfillmentRequestItems" in record and isinstance(record["fulfillmentRequestItems"], list):
            for item in record["fulfillmentRequestItems"]:
                total_ordered += item.get("quantity", 0)
                total_shipped += item.get("shippedQuantity", 0)
        else:
            total_ordered += record.get("totalQuantity", 0)
            total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
    """
    Pushes a record to Airtable.
    Airtable fields expected: Vendor (single select), Ordered QTY (number),
    Shipped QTY (number), Fill Rate (decimal percentage), and Week (text).
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

    groups = group_fulfillments_by_source(fulfillment_data)
    
    # For each unique source id that was returned, compute totals.
    for src_id, records in groups.items():
        ordered, shipped = compute_totals_for_group(records)
        fill_rate = round((shipped / ordered), 4) if ordered > 0 else 0.0
        vendor_label = source_id_to_vendor.get(src_id, f"Source {src_id}")
        print(f"→ {vendor_label}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate*100:.2f}%")
        post_to_airtable(vendor_label, ordered, shipped, fill_rate, week_str)

if __name__ == "__main__":
    main()
