
import uuid
from cloud_storage import (
    upload_document,
    backup_document,
    recover_document,
)

# Use a fictional test PDF only.
local_file = "sample_travel_document.pdf"

# Step 1: Upload a separate test document.
uploaded = upload_document(local_file)
print("Test document uploaded:", uploaded["cloud_name"])

# Step 2: Create and verify its cloud backup.
backup = backup_document(uploaded["cloud_name"])

if not backup["verified"]:
    raise RuntimeError("Backup verification failed")

if uploaded["checksum"] != backup["original_checksum"]:
    raise RuntimeError("Original checksum mismatch")

print("Backup verified successfully!")

# Step 3: Choose a NEW recovery destination.
# The original document remains untouched.
restored_name = (
    "recovered_test_"
    + str(uuid.uuid4())
    + ".pdf"
)

# Step 4: Restore the verified backup.
result = recover_document(
    restored_name,
    backup["backup_file"],
    backup["original_checksum"]
)

print("\n--- DISASTER RECOVERY RESULT ---")
print("Recovered:", result["recovered"])
print("Restored filename:", result["cloud_name"])
print("SHA-256:", result["checksum"])
print("Size:", result["size_bytes"], "bytes")

if result["recovered"]:
    print("SUCCESS: Cloud disaster recovery completed!")
