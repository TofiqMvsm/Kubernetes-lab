import os
from datetime import datetime, timedelta, timezone
import requests

now_utc = datetime.now(timezone.utc)

start_dt = now_utc.replace(hour=21, minute=0, second=0, microsecond=0)
end_dt = start_dt + timedelta(days=1)

start_param = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
end_param = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

print("Start:", start_param)
print("End:  ", end_param)

# Use the Elering JSON API endpoint directly to avoid CSV parsing steps
url = "https://dashboard.elering.ee/api/nps/price"
params = {
    "start": start_param,
    "end": end_param
}

response = requests.get(url, params=params)
response.raise_for_status()
data = response.json()

# Extract Estonian prices from the JSON response
# Elering structure usually returns items under data['data']['ee']
prices_data = []
if "data" in data and "ee" in data["data"]:
    for entry in data["data"]["ee"]:
        # entry format typically has 'timestamp' and 'price'
        timestamp = entry.get("timestamp")
        price = entry.get("price")
        
        # Calculate estonian_time (UTC+3 or using timestamp)
        dt_obj = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        estonian_time = dt_obj.isoformat()

        prices_data.append({
            "estonian_time": estonian_time,
            "price": price,
            "timestamp": timestamp
        })

# Determine the day string for the API query parameter (e.g., 2025-09-29 format)
day_str = (start_dt + timedelta(days=1)).strftime('%Y-%m-%d')

# Get history server URI from environment variable
history_server_uri = os.environ.get("HISTORY_SERVER_URI", "http://history-server.production.svc.cluster.local:80")
target_url = f"{history_server_uri}/api/prices?day={day_str}"

print(f"Sending {len(prices_data)} records to {target_url}...")

# Send POST request with JSON payload
post_response = requests.post(target_url, json=prices_data)
print("Response status:", post_response.status_code)
print("Response body:", post_response.text)
