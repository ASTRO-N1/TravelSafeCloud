
from cloud_storage import restore_original_document

print("\n--- RECOVERY PROTECTION TEST ---")

try:
    result = restore_original_document(2)

except FileExistsError:
    print("SUCCESS: Original document already exists!")
    print("SUCCESS: Recovery correctly prevented overwriting.")

except Exception as error:
    print("TEST ERROR:", type(error).__name__)
    print(str(error))

else:
    print("WARNING: Recovery operation completed.")
    print("Result:", result)
    print("Check cloud storage and database records.")
