

from cloud_storage import backup_document

print("TravelSafe Cloud Backup Verification")
print("------------------------------------")

cloud_name = input(
    "Enter the uploaded cloud PDF filename: "
).strip()

try:
    result = backup_document(cloud_name)

    print("\nBACKUP OPERATION COMPLETED")
    print("Original bucket:", result["original_bucket"])
    print("Backup bucket:", result["backup_bucket"])
    print("Original file:", result["original_file"])
    print("Backup file:", result["backup_file"])

    print("\nINTEGRITY VERIFICATION")
    print("Original SHA-256:", result["original_checksum"])
    print("Backup SHA-256:  ", result["backup_checksum"])

    if result["verified"]:
        print("\nSUCCESS: Backup integrity VERIFIED!")
    else:
        print("\nWARNING: Backup checksum mismatch!")

except Exception as error:
    print("\nBACKUP FAILED:", type(error).__name__)
    print("Details:", str(error)[:300])
