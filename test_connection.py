


import requests
from cloud_storage import (
    SUPABASE_URL,
    SUPABASE_KEY,
    PRIMARY_BUCKET
)

url = (
    SUPABASE_URL
    + "/storage/v1/object/list/"
    + PRIMARY_BUCKET
)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": "Bearer " + SUPABASE_KEY,
    "Content-Type": "application/json"
}

print("Checking Supabase Cloud Storage...")

try:
    response = requests.post(
        url,
        headers=headers,
        json={"prefix": "", "limit": 5, "offset": 0},
        timeout=30
    )

    print("HTTP Status:", response.status_code)

    if response.ok:
        print("SUCCESS: Cloud Storage connection is working!")
        print("Objects returned:", len(response.json()))
    else:
        print("Storage request failed.")
        print("Response:", response.text[:300])

except requests.exceptions.ConnectionError:
    print("ERROR: Cloud Storage connection interrupted.")

except requests.exceptions.Timeout:
    print("ERROR: Cloud Storage connection timed out.")

except requests.exceptions.RequestException as error:
    print("Request error:", type(error).__name__)
