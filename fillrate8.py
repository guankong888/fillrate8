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

if not AIRTABLE_TABLE_NAME:
    raise ValueError("❌ Missing AIRTABLE_TABLE_NAME in environment variables.")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

# Flxpoint configuration
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")
if not FLXPOINT_API_TOKEN:
    raise ValueError("❌ Missing FLXPOINT_API_TOKEN in environment variables.")

# Included statuses for fill rate tracking
INCLUDED_STATUSES = {"Completed", "Partially Shipped", "Acknowledged"}

# Allowed source IDs (only include these in results)
ALLOWED_SOURCE_IDS = {210740, 992648}  # Replace with actual source IDs you care about

# Map source IDs to vendor names
source_id_to_vendor = {
    210740: "Muscle Food",
    992648: "DNA"
}

def get_fulfillment_data():
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d")
    }
    url = "https://api.flxpoint.com/fulfillment-requests"
    print(f"\n📦 Requesting fulfillment data from {params['startDate']} to {params['endDate']}")
    
    response = requests.get(url, headers=headers, params=params)
    print("🔄 Status Code:", response.status_code)
    if response.status_code != 200:
        print("❌ Flxpoint API Error:", response.text)
        return []

    try:
        data = response.json()
        print(f"✅ Parsed {len(data)} records from Flxpoint")

        filtered_data = []
        for record in data:
            status = record.get("status")
            source_id = record.get("sourceId")
            request_number = record.get("fulfillmentRequestNumber")
            if status not in INCLUDED_STATUSES:
                print(f"⏭️ Skipped: Status = {status}, Ticket = {request_number}")
                continue
            print(f"✅ Included: Status = {status}, Source = {source_id}, Ticket = {request_number}")
            filtered_data.append(record)

        print(f"📊 Records after filtering by status: {len(filtered_data)}")
        return filtered_data
    except Exception as e:
        print("❌ JSON Parsing Error:", e)
        print("🔍 Raw Response:", response.text)
        return []

def group_fulfillments_by_source(data):
    groups = {}
    for record in data:
        src_id = record.get("sourceId")
        ticket = record.get("fulfillmentRequestNumber")
        if not src_id:
            print(f"⚠️ Missing sourceId on ticket {ticket}")
            continue
        if src_id not in ALLOWED_SOURCE_IDS:
            print(f"⛔ Excluded sourceId {src_id} on ticket {ticket}")
            continue
        groups.setdefault(src_id, []).append(record)
    print(f"🗂 Grouped records by source: {list(groups.keys())}")
    return groups

def compute_totals_for_group(records):
    total_ordered = 0
    total_shipped = 0
    for record in records:
        items = record.get("fulfillmentRequestItems", [])
        if isinstance(items, list):
            for item in items:
                total_ordered += item.get("quantity", 0)
                total_shipped += item.get("shippedQuantity", 0)
        else:
            total_ordered += record.get("totalQuantity", 0)
            total_shipped += record.get("shippedQuantity", 0)
    return total_ordered, total_shipped

def post_to_airtable(vendor, ordered, shipped, fill_rate, week_str):
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
        print(f"✅ Airtable updated for {vendor}")
    else:
        print(f"❌ Airtable error for {vendor}: {response.status_code} - {response.text}")

def main():
    week_str = datetime.now().strftime("%Y-%m-%d")
    data = get_fulfillment_data()
    if not data:
        print("⚠️ No valid fulfillment records found.")
        return

    grouped = group_fulfillments_by_source(data)

    for src_id, records in grouped.items():
        vendor = source_id_to_vendor.get(src_id, f"Source {src_id}")
        ordered, shipped = compute_totals_for_group(records)
        fill_rate = round((shipped / ordered), 4) if ordered > 0 else 0.0
        print(f"→ {vendor}: Ordered = {ordered}, Shipped = {shipped}, Fill Rate = {fill_rate*100:.2f}%")
        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)

if __name__ == "__main__":
    main()
