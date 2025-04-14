import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import quote

# Load environment variables from .env
load_dotenv()

# Airtable Config
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
encoded_table_name = quote(AIRTABLE_TABLE_NAME)

# Flxpoint Config
FLXPOINT_API_TOKEN = os.getenv("FLXPOINT_API_TOKEN")


def get_flxpoint_fill_rates():
    headers = { "X-API-TOKEN": FLXPOINT_API_TOKEN }

    today = datetime.utcnow()
    last_week = today - timedelta(days=7)

    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d")
    }

    print(f"\n📅 Getting orders from {last_week.date()} to {today.date()}")
    url = "https://api.flxpoint.com/api/v2/orders"
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("❌ Flxpoint Error:", response.status_code, response.text)
        return {}

    orders = response.json().get("data", [])
    vendor_totals = defaultdict(lambda: {"ordered": 0, "shipped": 0})

    for order in orders:
        vendor = order.get("source", {}).get("name", "UNKNOWN")
        for item in order.get("line_items", []):
            qty = item.get("quantity", 0)
            shipped = item.get("shipped_quantity", 0)
            vendor_totals[vendor]["ordered"] += qty
            vendor_totals[vendor]["shipped"] += shipped

    return vendor_totals


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
        print(f"✅ Pushed to Airtable for {vendor}")
    else:
        print(f"❌ Airtable Error for {vendor}:", response.status_code, response.text)


def main():
    vendor_totals = get_flxpoint_fill_rates()
    if not vendor_totals:
        print("⚠️ No data returned from Flxpoint.")
        return

    week_str = datetime.now().strftime("%Y-%m-%d")

    print("\n📊 Fill Rate Summary:")
    for vendor, stats in vendor_totals.items():
        ordered = stats["ordered"]
        shipped = stats["shipped"]
        fill_rate = round(shipped / ordered, 4) if ordered else 0.0

        print(f"→ {vendor}: {shipped}/{ordered} shipped → {fill_rate * 100:.2f}%")

        post_to_airtable(vendor, ordered, shipped, fill_rate, week_str)


if __name__ == "__main__":
    main()
