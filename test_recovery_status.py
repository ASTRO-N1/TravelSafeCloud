


from supabase_client import (
    get_backup_records,
    update_recovery_status
)

backups = get_backup_records()

backup = next(
    (
        b for b in backups
        if b.get("recovery_status") == "Not Required"
    ),
    None
)

if backup is None:
    raise RuntimeError("No suitable backup record found")

backup_id = backup["backup_id"]
original_status = backup["recovery_status"]

print("Testing Backup ID:", backup_id)
print("Original Status:", original_status)

try:
    result = update_recovery_status(
        backup_id,
        "Recovered"
    )

    if result["recovery_status"] != "Recovered":
        raise RuntimeError("Update verification failed")

    print("SUCCESS: Database update works!")

finally:
    restored = update_recovery_status(
        backup_id,
        original_status
    )

    print("Restored Status:", restored["recovery_status"])

print("SUCCESS: Recovery status test completed!")
