
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase credentials are missing from .env"
    )

BASE_URL = SUPABASE_URL + "/rest/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": "Bearer " + SUPABASE_KEY,
    "Content-Type": "application/json"
}


def get_customers():
    """Retrieve customers from Supabase PostgreSQL."""

    response = requests.get(
        BASE_URL + "/customers",
        headers=HEADERS,
        params={
            "select": (
                "customer_id,full_name,email,phone,"
                "preferred_destination,travel_type,created_at"
            ),
            "order": "created_at.desc"
        },
        timeout=15
    )
    print("CUSTOMER GET STATUS:", response.status_code, flush=True)
    print("CUSTOMER GET RESPONSE:", response.text[:1000], flush=True)
    response.raise_for_status()
    return response.json()


def add_customer(customer_data):
    """Save a new customer to Supabase PostgreSQL."""

    headers = HEADERS.copy()
    headers["Prefer"] = "return=representation"

    response = requests.post(
        BASE_URL + "/customers",
        headers=headers,
        json=customer_data,
        timeout=15
    )

    if not response.ok:
        raise RuntimeError(
            "Supabase customer insert failed. "
            f"HTTP {response.status_code}: {response.text}"
        )

    return response.json()
    
def add_document(document_data):
    """Save cloud document metadata to Supabase PostgreSQL."""

    headers = HEADERS.copy()
    headers["Prefer"] = "return=representation"

    response = requests.post(
        BASE_URL + "/documents",
        headers=headers,
        json=document_data,
        timeout=15
    )

    response.raise_for_status()
    return response.json()
    
def add_backup_record(backup_data):
    """Save cloud backup metadata to Supabase PostgreSQL."""

    headers = HEADERS.copy()
    headers["Prefer"] = "return=representation"

    response = requests.post(
        BASE_URL + "/backup_records",
        headers=headers,
        json=backup_data,
        timeout=15
    )

    response.raise_for_status()
    return response.json()

def get_backup_records():
    """Retrieve cloud backup records from Supabase."""

    response = requests.get(
        BASE_URL + "/backup_records",
        headers=HEADERS,
        params={
            "select": (
                "backup_id,document_id,backup_file_path,"
                "backup_status,verification_status,"
                "original_checksum,backup_checksum,"
                "backup_date,last_verified_at,recovery_status"
            ),
            "order": "backup_id.desc"
        },
        timeout=15
    )

    response.raise_for_status()
    return response.json()

def get_documents():
    """Retrieve cloud document metadata from Supabase."""

    response = requests.get(
        BASE_URL + "/documents",
        headers=HEADERS,
        params={
            "select": (
                "document_id,booking_id,file_name,"
                "file_path,document_type,file_size,"
                "upload_date,verification_status,"
                "storage_status,checksum_sha256"
            ),
            "order": "document_id.desc"
        },
        timeout=15
    )

    response.raise_for_status()
    return response.json()




def update_recovery_status(backup_id, status):
    """Update recovery status in Supabase PostgreSQL."""

    allowed_statuses = (
        "Not Required",
        "Recovered",
        "Failed"
    )

    if status not in allowed_statuses:
        raise ValueError("Invalid recovery status")

    url = BASE_URL + "/backup_records"

    params = {
        "backup_id": "eq." + str(backup_id)
    }

    headers = HEADERS.copy()
    headers["Prefer"] = "return=representation"

    response = requests.patch(
        url,
        params=params,
        headers=headers,
        json={"recovery_status": status},
        timeout=30
    )

    if response.status_code >= 400:
        print("Database HTTP Status:", response.status_code)
        print("Supabase Error:", response.text[:1000])

    response.raise_for_status()

    updated_records = response.json()

    if len(updated_records) != 1:
        raise RuntimeError(
            "Expected exactly one backup record to be updated"
        )

    return updated_records[0]

def record_successful_recovery(backup_id, recovery_result):
    """
    Record a completed original-document recovery.

    Only call this after restoring the original
    document, not after creating a separate test copy.
    """

    if recovery_result.get("recovered") is not True:
        raise ValueError("Recovery has not succeeded")

    if not recovery_result.get("cloud_name"):
        raise ValueError("Recovered filename is missing")

    return update_recovery_status(
        backup_id,
        "Recovered"
    )


def get_recovery_details(backup_id):
    """
    Find a backup and its associated original document.
    This function does not modify cloud files or database records.
    """

    backups = get_backup_records()
    documents = get_documents()

    backup = next(
        (
            b for b in backups
            if str(b["backup_id"]) == str(backup_id)
        ),
        None
    )

    if backup is None:
        raise ValueError("Backup record not found")

    document = next(
        (
            d for d in documents
            if str(d["document_id"]) == str(backup["document_id"])
        ),
        None
    )

    if document is None:
        raise ValueError("Original document record not found")

    if not document.get("file_path"):
        raise ValueError("Original document path is missing")

    if not backup.get("backup_file_path"):
        raise ValueError("Backup file path is missing")

    if not document.get("checksum_sha256"):
        raise ValueError("Original document checksum is missing")

    if (
        backup.get("original_checksum")
        != document["checksum_sha256"]
    ):
        raise ValueError(
            "Backup checksum does not match document metadata"
        )

    return {
        "backup_id": backup["backup_id"],
        "document_id": document["document_id"],
        "original_path": document["file_path"],
        "backup_path": backup["backup_file_path"],
        "expected_checksum": document["checksum_sha256"],
        "recovery_status": backup.get("recovery_status")
    }

def get_bookings():
    """Retrieve bookings from Supabase PostgreSQL."""

    response = requests.get(
        BASE_URL + "/bookings",
        headers=HEADERS,
        params={
            "select": "*",
            "order": "booking_id.desc"
        },
        timeout=15
    )

    response.raise_for_status()
    return response.json()

