def get_flxpoint_fill_rates():
    headers = { "X-API-TOKEN": FLXPOINT_API_TOKEN }

    today = datetime.utcnow()
    last_week = today - timedelta(days=7)

    params = {
        "startDate": last_week.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d")
    }

    print(f"\n📅 Getting orders from {last_week.date()} to {today.date()}")
    url = "https://app.flxpoint.com/api/v2/order"  # ✅ corrected endpoint
    print("🔗 Requesting:", url)
    print("📤 Params:", params)

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print("❌ Flxpoint Error:", response.status_code)
        print(response.text)
        return {}

    try:
        json_data = response.json()
    except Exception as e:
        print("❌ Failed to decode JSON:", e)
        print("🔍 Raw response:")
        print(response.text)
        return {}

    orders = json_data.get("data", [])
    if not orders:
        print("⚠️ No orders returned from Flxpoint.")
        return {}

    vendor_totals = defaultdict(lambda: {"ordered": 0, "shipped": 0})
    for order in orders:
        vendor = order.get("source", {}).get("name", "UNKNOWN")
        for item in order.get("line_items", []):
            qty = item.get("quantity", 0)
            shipped = item.get("shipped_quantity", 0)
            vendor_totals[vendor]["ordered"] += qty
            vendor_totals[vendor]["shipped"] += shipped

    return vendor_totals
