# maintcommit
import requests
from datetime import datetime, timedelta
import pytz

# Function to get Monday at 12:01 AM Mountain Time and convert to UTC ISO string
def get_monday_1201_mtn_to_utc():
    mtn = pytz.timezone("US/Mountain")
    today = datetime.now(mtn)
    monday = today - timedelta(days=today.weekday())
    monday_1201_mtn = mtn.localize(datetime(monday.year, monday.month, monday.day, 0, 1))
    monday_utc = monday_1201_mtn.astimezone(pytz.utc)
    return monday_utc.isoformat()

# Config
FLXPOINT_API_URL = "https://api.flxpoint.com/orders"
API_TOKEN = "wmPdfGqOC8JthJUxHoejguWIQUsy1mtsvX8hJ6nn6bxA8DgyShlpdFfJrXkOsM8OCGXr3rejP6soI3QyqIYTFZ8G6KHHVsOPZOYk"
headers = {
    "X-API-TOKEN": API_TOKEN,
    "Content-Type": "application/json"
}

# Params
params = {
    "pageSize": 100,
    "orderedAfter": get_monday_1201_mtn_to_utc()
}

# API request
response = requests.get(FLXPOINT_API_URL, headers=headers, params=params)

# Handle the response
if response.status_code == 200:
    orders = response.json()
    print("Successfully retrieved orders.")
    # Add logic here to parse/export orders if needed
else:
    print("Error fetching orders:", response.status_code, response.text)

import csv
import os

# Set your output path and file name
output_path = os.path.join(os.getcwd(), "flxpoint_orders_export.csv")

# Flattened list of orders with line items
rows = []

for order in orders:
    order_number = order.get("orderNumber")
    order_date = order.get("orderedAt")
    status = order.get("status")
    channel = order.get("channel", {}).get("name")

    for line in order.get("lineItems", []):
        sku = line.get("sku")
        title = line.get("title")
        quantity = line.get("quantityOrdered")
        rows.append({
            "Order Number": order_number,
            "Order Date": order_date,
            "Status": status,
            "Channel": channel,
            "SKU": sku,
            "Title": title,
            "Qty Ordered": quantity
        })

# Define headers
headers = ["Order Number", "Order Date", "Status", "Channel", "SKU", "Title", "Qty Ordered"]

# Write to CSV
with open(output_path, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ CSV export complete: {output_path}")

