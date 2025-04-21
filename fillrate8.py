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
