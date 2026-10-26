
from cloud_storage import upload_document

print("Starting cloud document upload...")

try:
    result = upload_document("sample_travel_document.pdf")

    print("SUCCESS: Document uploaded to Supabase!")
    print("Bucket:", result["bucket"])
    print("Cloud filename:", result["cloud_name"])
    print("Size:", result["size_bytes"], "bytes")
    print("SHA-256 checksum:", result["checksum"])

except Exception as error:
    print("UPLOAD FAILED:", type(error).__name__)
    print("Details:", str(error)[:300])
