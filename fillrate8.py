import requests
from datetime import datetime, timedelta

# Function to get current week's Monday with year set to 0001
def get_ordered_after_date():
    today = datetime.utcnow()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    monday_with_0001_year = this_monday.replace(year=1)
    return monday_with_0001_year.isoformat()

# Config
FLXPOINT_API_URL = "https://api.flxpoint.com/orders"
API_TOKEN = "wmPdfGqOC8JthJUxHoejguWIQUsy1mtsvX8hJ6nn6bxA8DgyShlpdFfJrXkOsM8OCGXr3rejP6soI3QyqIYTFZ8G6KHHVsOPZOYk"
headers = {
    "X-API-TOKEN": API_TOKEN,
    "Content-Type": "application/json"
}

# Params
params = {
    "pageSize": 1000,
    "orderedAfter": get_ordered_after_date()
}

# API request
response = requests.get(FLXPOINT_API_URL, headers=headers, params=params)

# Handle the response
if response.status_code == 200:
    orders = response.json()
    print("Successfully retrieved orders:", orders)
else:
    print("Error fetching orders:", response.status_code, response.text)
