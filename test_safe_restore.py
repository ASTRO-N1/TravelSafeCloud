
import uuid

from cloud_storage import (
    verify_recovery_backup,
    recover_document
)
from supabase_client import get_backup_records

backups = get_backup_records()

if not backups:
    raise RuntimeError("No backup records available")

backup = backups[0]

backup_name = backup["backup_file_path"].split("/")[-1]
expected_checksum = backup["original_checksum"]

print("Selected Backup ID:", backup["backup_id"])

# Verify the existing cloud backup first.
verification = verify_recovery_backup(
    backup_name,
    expected_checksum
)

if not verification["verified"]:
    raise RuntimeError("Backup integrity verification failed")

print("SUCCESS: Existing backup verified!")

# Restore to a new, unique test filename.
# No existing document will be overwritten.
restored_name = "recovered_test_" + str(uuid.uuid4()) + ".pdf"

result = recover_document(
    restored_name,
    backup_name,
    expected_checksum
)

print("\n--- DISASTER RECOVERY RESULT ---")
print("Recovered:", result["recovered"])
print("Restored filename:", result["cloud_name"])
print("SHA-256:", result["checksum"])
print("Size:", result["size_bytes"], "bytes")

print("SUCCESS: Cloud disaster recovery completed!")
