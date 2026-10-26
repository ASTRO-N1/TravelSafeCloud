
import os
import uuid
import hashlib
import mimetypes
import requests

from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

PRIMARY_BUCKET = "travel-documents"
BACKUP_BUCKET = "travel-backups"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials are missing")


def upload_document(file_path):
    """Upload a local document to private cloud storage."""

    if not os.path.isfile(file_path):
        raise FileNotFoundError("Document does not exist")

    original_name = os.path.basename(file_path)

    # Use a unique name to prevent accidental overwriting.
    cloud_name = str(uuid.uuid4()) + "_" + original_name

    with open(file_path, "rb") as file:
        file_bytes = file.read()

    # Calculate checksum for future backup verification.
    checksum = hashlib.sha256(file_bytes).hexdigest()

    content_type = (
        mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )

    encoded_name = quote(cloud_name, safe="")

    endpoint = (
        SUPABASE_URL
        + "/storage/v1/object/"
        + PRIMARY_BUCKET
        + "/"
        + encoded_name
    )

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": content_type,
        "x-upsert": "false"
    }

    response = requests.post(
        endpoint,
        headers=headers,
        data=file_bytes,
        timeout=30
    )

    if not response.ok:
     print("Storage HTTP status:", response.status_code)
     print("Storage error:", response.text[:500])
     response.raise_for_status()

    return {
        "original_name": original_name,
        "cloud_name": cloud_name,
        "bucket": PRIMARY_BUCKET,
        "checksum": checksum,
        "size_bytes": len(file_bytes)
    }


def backup_document(cloud_name):
    """Create and verify a backup in Supabase Storage."""

    if not cloud_name or "/" in cloud_name or "\\" in cloud_name:
        raise ValueError("Invalid cloud filename")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY
    }

    # Download original document
    original_url = (
        SUPABASE_URL
        + "/storage/v1/object/authenticated/"
        + PRIMARY_BUCKET + "/"
        + quote(cloud_name, safe="")
    )

    original_response = requests.get(
        original_url, headers=headers, timeout=30
    )
    original_response.raise_for_status()

    original_bytes = original_response.content
    original_checksum = hashlib.sha256(original_bytes).hexdigest()

    # Create backup with a unique filename
    backup_name = str(uuid.uuid4()) + "_" + cloud_name

    backup_url = (
        SUPABASE_URL
        + "/storage/v1/object/"
        + BACKUP_BUCKET + "/"
        + quote(backup_name, safe="")
    )

    backup_headers = headers.copy()
    backup_headers["Content-Type"] = (
        mimetypes.guess_type(cloud_name)[0]
        or "application/octet-stream"
    )
    backup_headers["x-upsert"] = "false"

    backup_response = requests.post(
        backup_url,
        headers=backup_headers,
        data=original_bytes,
        timeout=30
    )
    backup_response.raise_for_status()

    # Download backup for independent verification
    verify_url = (
        SUPABASE_URL
        + "/storage/v1/object/authenticated/"
        + BACKUP_BUCKET + "/"
        + quote(backup_name, safe="")
    )

    verify_response = requests.get(
        verify_url, headers=headers, timeout=30
    )
    verify_response.raise_for_status()

    backup_checksum = hashlib.sha256(
        verify_response.content
    ).hexdigest()

    return {
        "original_file": cloud_name,
        "backup_file": backup_name,
        "original_bucket": PRIMARY_BUCKET,
        "backup_bucket": BACKUP_BUCKET,
        "original_checksum": original_checksum,
        "backup_checksum": backup_checksum,
        "verified": original_checksum == backup_checksum,
        "size_bytes": len(original_bytes)
    }

def recover_document(cloud_name, backup_name, expected_checksum):
    """Restore a document from a SHA-256 verified cloud backup."""

    if not cloud_name or not backup_name:
        raise ValueError("Document and backup names are required")

    for name in (cloud_name, backup_name):
        if "/" in name or "\\" in name:
            raise ValueError("Invalid cloud filename")

    if (
        not isinstance(expected_checksum, str)
        or len(expected_checksum) != 64
        or any(c not in "0123456789abcdef"
               for c in expected_checksum.lower())
    ):
        raise ValueError("Invalid SHA-256 checksum")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY
    }

    # Download the backup from private cloud storage.
    backup_url = (
        SUPABASE_URL
        + "/storage/v1/object/authenticated/"
        + BACKUP_BUCKET + "/"
        + quote(backup_name, safe="")
    )

    response = requests.get(
        backup_url,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    backup_bytes = response.content
    recovered_checksum = hashlib.sha256(
        backup_bytes
    ).hexdigest()

    # Verify backup integrity before attempting recovery.
    if recovered_checksum != expected_checksum.lower():
        raise ValueError(
            "Recovery blocked: SHA-256 checksum mismatch"
        )

    # Check whether the original document already exists.
    original_url = (
        SUPABASE_URL
        + "/storage/v1/object/authenticated/"
        + PRIMARY_BUCKET + "/"
        + quote(cloud_name, safe="")
    )

    original_response = requests.get(
        original_url,
        headers=headers,
        timeout=30
    )

    
    
    if original_response.status_code == 200:
        raise FileExistsError(
            "Destination file already exists. "
            "Recovery was not performed."
        )

    # Supabase Storage may return HTTP 400 with
    # a 404/NoSuchKey response for a missing object.
    error_data = {}
    try:
        error_data = original_response.json()
    except ValueError:
        pass

    missing_object = (
        original_response.status_code in (400, 404)
        and str(error_data.get("statusCode")) == "404"
        and error_data.get("code") == "NoSuchKey"
    )

    if not missing_object:
        original_response.raise_for_status()
        raise RuntimeError(
            "Could not confirm that the destination is missing."
        )

    print("SUCCESS: Recovery destination is available!")




    # Restore to the primary bucket without overwriting.
    restore_url = (
        SUPABASE_URL
        + "/storage/v1/object/"
        + PRIMARY_BUCKET + "/"
        + quote(cloud_name, safe="")
    )

    restore_headers = headers.copy()
    restore_headers["Content-Type"] = (
        mimetypes.guess_type(cloud_name)[0]
        or "application/octet-stream"
    )
    restore_headers["x-upsert"] = "false"

    restore_response = requests.post(
        restore_url,
        headers=restore_headers,
        data=backup_bytes,
        timeout=30
    )
    restore_response.raise_for_status()

    return {
        "recovered": True,
        "cloud_name": cloud_name,
        "backup_name": backup_name,
        "checksum": recovered_checksum,
        "size_bytes": len(backup_bytes)
    }

def verify_recovery_backup(backup_name, expected_checksum):
    """Check whether a cloud backup is safe for recovery."""

    if not backup_name or "/" in backup_name or "\\" in backup_name:
        raise ValueError("Invalid backup filename")

    if (
        not isinstance(expected_checksum, str)
        or len(expected_checksum) != 64
        or any(c not in "0123456789abcdef"
               for c in expected_checksum.lower())
    ):
        raise ValueError("Invalid SHA-256 checksum")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY
    }

    backup_url = (
        SUPABASE_URL
        + "/storage/v1/object/authenticated/"
        + BACKUP_BUCKET + "/"
        + quote(backup_name, safe="")
    )

    response = requests.get(
        backup_url,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    actual_checksum = hashlib.sha256(
        response.content
    ).hexdigest()

    return {
        "backup_name": backup_name,
        "verified": actual_checksum == expected_checksum.lower(),
        "actual_checksum": actual_checksum,
        "size_bytes": len(response.content),
        "ready_for_recovery": (
            actual_checksum == expected_checksum.lower()
        )
    }

def restore_original_document(backup_id):
    """
    Restore a missing original document from its
    verified cloud backup and record the result.
    """

    from supabase_client import (
        get_recovery_details,
        record_successful_recovery
    )

    details = get_recovery_details(backup_id)

    original_prefix = "travel-documents/"
    backup_prefix = "travel-backups/"

    original_path = details["original_path"]
    backup_path = details["backup_path"]

    if not original_path.startswith(original_prefix):
        raise ValueError("Invalid original storage path")

    if not backup_path.startswith(backup_prefix):
        raise ValueError("Invalid backup storage path")

    original_name = original_path[len(original_prefix):]
    backup_name = backup_path[len(backup_prefix):]

    if not original_name or not backup_name:
        raise ValueError("Missing storage object name")

    expected_checksum = details["expected_checksum"]

    verification = verify_recovery_backup(
        backup_name,
        expected_checksum
    )

    if verification["verified"] is not True:
        raise RuntimeError(
            "Backup integrity verification failed"
        )

    result = recover_document(
        original_name,
        backup_name,
        expected_checksum
    )

    if result["recovered"] is not True:
        raise RuntimeError("Document recovery failed")

    if result["checksum"] != expected_checksum:
        raise RuntimeError("Recovered checksum mismatch")

    record_successful_recovery(
        backup_id,
        result
    )

    return result
