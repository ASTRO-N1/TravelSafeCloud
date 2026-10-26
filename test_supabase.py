
import os
import requests
from dotenv import load_dotenv

# Load credentials securely from .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("Missing Supabase environment variables.")

# Supabase automatically exposes PostgreSQL tables
# through its REST API.
endpoint = SUPABASE_URL + "/rest/v1/customers"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": "Bearer " + SUPABASE_KEY
}

print("Connecting to Supabase Cloud...")

try:
    response = requests.get(
        endpoint,
        headers=headers,
        params={"select": "customer_id", "limit": "1"},
        timeout=15
    )

    if response.status_code == 200:
        print("SUCCESS: Supabase connection established!")
        print("SUCCESS: Customers table is accessible.")
        print("HTTP Status:", response.status_code)
        print("Database response:", response.json())

    else:
        print("Connection request failed.")
        print("HTTP Status:", response.status_code)
        print("Error:", response.text[:300])

except requests.exceptions.RequestException as error:
    print("Network or connection error:", error)
