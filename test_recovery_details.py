

from supabase_client import get_recovery_details

# Previously verified backup record
details = get_recovery_details(2)

print("\n--- CLOUD STORAGE PATH VERIFICATION ---")

print("Backup ID:", details["backup_id"])
print("Document ID:", details["document_id"])

print("Original Path:", details["original_path"])
print("Backup Path:", details["backup_path"])

print("Recovery Status:", details["recovery_status"])

print("\nSUCCESS: Cloud storage paths retrieved!")
