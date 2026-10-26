
from cloud_storage import verify_recovery_backup
from supabase_client import get_backup_records

# Retrieve backup records from Supabase PostgreSQL
backups = get_backup_records()

if not backups:
    print("No backup records found.")
else:
    # Select the most recent backup record
    backup = backups[0]

    backup_path = backup["backup_file_path"]
    expected_checksum = backup["original_checksum"]

    # Extract filename from the stored bucket path
    backup_name = backup_path.split("/")[-1]

    print("Checking backup ID:", backup["backup_id"])
    print("Backup file:", backup_name)

    result = verify_recovery_backup(
        backup_name,
        expected_checksum
    )

    print("\n--- RECOVERY VERIFICATION RESULT ---")
    print("Backup verified:", result["verified"])
    print("Ready for recovery:", result["ready_for_recovery"])
    print("Backup size:", result["size_bytes"], "bytes")

    if result["verified"]:
        print("SUCCESS: Cloud backup is safe for recovery!")
    else:
        print("FAILED: Backup checksum mismatch!")
