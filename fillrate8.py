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

# Optional vendor name mapping
source_id_to_vendor = {
    210740: "Muscle Food",
    992648: "DNA",
    212291: "N2G Water"
}

def get_fulfillment_data():
    headers = {"X-API-TOKEN": FLXPOINT_API_TOKEN}
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    base_url = "https://api.flxpoint.com/fulfillment-requests"

    limit = 100
    offset = 0
    page_count = 1
    all_data = []

    while True:
        params = {
            "limit": limit,
            "offset": offset
        }
        print(f"\n📦 Requesting page {page_count} (offset={offset})")
        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code != 200:
            print("❌ Flxpoint API Error:", response.text)
            break

        try:
            page_data = response.json()
            if not isinstance(page_data, list):
                print("❌ Unexpected response format (expected list)")
                print(json.dumps(page_data, indent=2)[:1000])
                break

            print(f"✅ Page {page_count} returned {len(page_data)} records")

            for record in page_data:
                sent_at_str = record.get("sentAt")
                if not sent_at_str:
                    continue
                try:
                    sent_at = datetime.strptime(sent_at_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    if last_week <= sent_at <= today:
                        all_data.append(record)
                    else:
                        print(f"⏭️ Skipped old record: {record.get('fulfillmentRequestNumber')} (sentAt: {sent_at_str})")
                except Exception as e:
                    print(f"⚠️ Failed to parse sentAt on record {record.get('fulfillmentRequestNumber')}: {e}")

            if len(page_data) < limit:
                break
            offset += limit
            page_count += 1

        except Exception as e:
            print("❌ Failed to parse JSON:", e)
            print("🔍 Raw response:", response.text)
            break

    print(f"\n📦 Total valid records fetched: {len(all_data)}")

    if all_data:
        print("\n🧾 Sample record for inspection:")
        print(json.dumps(all_data[0], indent=2)[:2000])
    else:
        print("⚠️ No valid fulfillment data found.")

    return all_data

def group_fulfillments_by_source(data):
    groups = {}
    for record in data:
        src_id = record.get("sourceId")
        ticket = record.get("fulfillmentRequestNumber")
        if not src_id:
            print(f"⚠️ Missing sourceId on ticket {ticket}")
            continue
        groups.setdefault(src_id, []).append(record)
    print(f"🗂 Grouped records by source ID: {list(groups.keys())}")
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
