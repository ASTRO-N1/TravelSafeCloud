

import os
import sqlite3
import tempfile
from datetime import timedelta

from dotenv import load_dotenv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    session
)

from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from cloud_storage import upload_document, backup_document

from supabase_client import (
    get_customers,
    add_customer,
    get_bookings,
    add_booking,
    get_travel_packages,
    add_document,
    add_backup_record,
    get_backup_records,
    get_documents
)


# ========================================
# FLASK CONFIGURATION
# ========================================

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing from the .env file"
    )

app.config["WTF_CSRF_ENABLED"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": generate_csrf}


# ========================================
# LOCAL DATABASE CONFIGURATION
# ========================================

DATABASE = "database/travelsafe.db"
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def init_db():

    os.makedirs("database", exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    connection = sqlite3.connect(DATABASE)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                aws_status TEXT DEFAULT 'Pending',
                gcp_status TEXT DEFAULT 'Pending',
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()

    finally:
        connection.close()


init_db()


# ========================================
# MAIN DASHBOARD
# ========================================

@app.route("/")
def home():
    return redirect(url_for("admin_dashboard"))


# ========================================
# TRAVEL WEBSITE
# ========================================

@app.route("/home")
def travel_home():
    return render_template("index.html")


# ========================================
# HELPER: VERIFIED BACKUP COUNT
# ========================================

def count_verified_backups(backups):

    return sum(
        1
        for backup in backups
        if (
            str(
                backup.get("verification_status", "")
            ).lower() == "verified"

            and bool(backup.get("original_checksum"))

            and backup.get("original_checksum")
            == backup.get("backup_checksum")
        )
    )


# ========================================
# ADMIN DASHBOARD
# ========================================

@app.route("/admin")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    try:
        documents = get_documents()
        customers = get_customers()
        bookings = get_bookings()
        backups = get_backup_records()

    except Exception:
        app.logger.exception(
            "Failed to load admin dashboard data from Supabase"
        )

        return (
            "Unable to load dashboard data from Supabase. "
            "Please try again.",
            503
        )

    stats = {
        "total_customers": len(customers),
        "total_bookings": len(bookings),
        "total_documents": len(documents),
        "verified_backups": count_verified_backups(backups)
    }

    # Diagnostic information for template troubleshooting
    if app.debug:
        template_path = app.jinja_loader.get_source(
            app.jinja_env,
            "admin_dashboard.html"
        )[1]

        app.logger.debug(
            "Admin dashboard template: %s",
            template_path
        )

    return render_template(
        "admin_dashboard.html",
        documents=documents,
        stats=stats
    )


# ========================================
# LOCAL DOCUMENT UPLOAD
# LEGACY FUNCTIONALITY
# ========================================

@app.route("/upload", methods=["POST"])
def upload():

    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Unauthorized"
        }), 401

    file = request.files.get("file")

    document_type = request.form.get(
        "document_type", "Travel Document"
    )

    if not file or not file.filename:
        return jsonify({
            "error": "Please select a file"
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "error": "Invalid filename"
        }), 400

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(file_path)

    connection = sqlite3.connect(DATABASE)

    try:
        connection.execute("""
            INSERT INTO documents
            (file_name, document_type)
            VALUES (?, ?)
        """, (
            filename,
            document_type
        ))

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("admin_dashboard"))


# ========================================
# CUSTOMER DASHBOARD
# ========================================

@app.route("/customers")
def customers_page():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    return render_template("customers.html")


# ========================================
# SUPABASE CUSTOMER API
# ========================================

@app.route("/api/customers", methods=["GET", "POST"])
def customers_api():

    if not session.get("admin_logged_in"):
        return jsonify({
            "success": False,
            "error": "Unauthorized"
        }), 401

    

    # GET CUSTOMERS
    if request.method == "GET":

        try:
            customers = get_customers()

            return jsonify({
                "success": True,
                "customers": customers
            }), 200

        except Exception:
            app.logger.exception(
                "Supabase customer fetch failed"
            )

            return jsonify({
                "success": False,
                "error": "Unable to retrieve customers"
            }), 502

    # ADD CUSTOMER
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "A JSON object is required"
        }), 400

    required_fields = [
        "full_name",
        "email",
        "phone",
        "preferred_destination",
        "travel_type"
    ]

    if any(
        not isinstance(data.get(field), str)
        or not data[field].strip()
        for field in required_fields
    ):
        return jsonify({
            "success": False,
            "error": "All customer fields are required"
        }), 400

    customer_data = {
        field: data[field].strip()
        for field in required_fields
    }

    if (
        len(customer_data["full_name"]) > 150
        or len(customer_data["email"]) > 254
        or len(customer_data["phone"]) > 30
        or "@" not in customer_data["email"]
    ):
        return jsonify({
            "success": False,
            "error": "Invalid customer details"
        }), 400

    try:
        saved_customer = add_customer(customer_data)

        return jsonify({
            "success": True,
            "message": "Customer saved to Supabase",
            "customer": saved_customer
        }), 201

    except Exception:
        app.logger.exception(
            "Supabase customer insert failed"
        )

        return jsonify({
            "success": False,
            "error": "Unable to save customer"
        }), 502


# ========================================
# BOOKINGS PAGE
# ========================================

@app.route("/bookings", methods=["GET", "POST"])
def bookings_page():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        is_json = request.is_json
        data = request.get_json(silent=True) if is_json else request.form

        try:
            customer_id = int(data.get("customer_id", 0))
            package_id = int(data.get("package_id", 0))
            travel_start_date = (data.get("travel_start_date") or "").strip()
            travel_end_date = (data.get("travel_end_date") or "").strip()
            number_of_travelers = int(data.get("number_of_travelers", 1))
            total_amount = float(data.get("total_amount", 0))
            special_requests = (data.get("special_requests") or "").strip() or None
            booking_status = (data.get("booking_status") or "Confirmed").strip()

            if not customer_id or not package_id or not travel_start_date or not travel_end_date:
                error_msg = "Customer, package, start date, and end date are required."
                if is_json:
                    return jsonify({"success": False, "error": error_msg}), 400
                return render_template(
                    "bookings.html",
                    error=error_msg,
                    bookings=get_bookings(),
                    customers=get_customers(),
                    packages=get_travel_packages()
                ), 400

            booking_payload = {
                "customer_id": customer_id,
                "package_id": package_id,
                "travel_start_date": travel_start_date,
                "travel_end_date": travel_end_date,
                "number_of_travelers": number_of_travelers,
                "total_amount": total_amount,
                "booking_status": booking_status,
                "payment_status": "Pending",
                "approval_status": "Approved" if booking_status == "Confirmed" else "Pending",
                "special_requests": special_requests
            }

            saved_rows = add_booking(booking_payload)
            saved_booking = saved_rows[0] if saved_rows else booking_payload

            if is_json:
                return jsonify({
                    "success": True,
                    "message": "Booking created successfully in Supabase",
                    "booking": saved_booking
                }), 201

            return redirect(url_for("bookings_page"))

        except Exception as ex:
            app.logger.exception("Failed to create booking in Supabase")
            if is_json:
                return jsonify({"success": False, "error": str(ex)}), 500
            try:
                bookings = get_bookings()
                customers = get_customers()
                packages = get_travel_packages()
            except Exception:
                bookings, customers, packages = [], [], []
            return render_template(
                "bookings.html",
                error="Failed to create booking: " + str(ex),
                bookings=bookings,
                customers=customers,
                packages=packages
            ), 500

    try:
        bookings = get_bookings()
        customers = get_customers()
        packages = get_travel_packages()

    except Exception:
        app.logger.exception(
            "Failed to load cloud bookings"
        )

        return (
            "Unable to load bookings from Supabase.",
            503
        )

    return render_template(
        "bookings.html",
        bookings=bookings,
        customers=customers,
        packages=packages
    )


# ========================================
# CLOUD UPLOAD PAGE
# ========================================

@app.route("/cloud-upload", methods=["GET"])
def cloud_upload_page():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    try:
        bookings = get_bookings()

    except Exception:
        app.logger.exception(
            "Failed to load bookings for cloud upload"
        )

        return (
            "Unable to load bookings from Supabase.",
            503
        )

    return render_template(
        "cloud_upload.html",
        bookings=bookings
    )


# ========================================
# CLOUD DOCUMENT UPLOAD
# ========================================

@app.route("/cloud-upload", methods=["POST"])
def cloud_upload():

    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Unauthorized"
        }), 401

    file = request.files.get("file")

    document_type = request.form.get(
        "document_type",
        "Travel Document"
    )

    booking_id = request.form.get(
        "booking_id", ""
    ).strip()

    if not file or not file.filename:
        return jsonify({
            "error": "Please select a PDF"
        }), 400

    if not booking_id.isdigit():
        return jsonify({
            "error": "Valid booking ID required"
        }), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Only PDF files allowed"
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "error": "Invalid filename"
        }), 400

    file_bytes = file.read(
        10 * 1024 * 1024 + 1
    )

    if len(file_bytes) > 10 * 1024 * 1024:
        return jsonify({
            "error": "Maximum PDF size is 10 MB"
        }), 413

    if not file_bytes.startswith(b"%PDF-"):
        return jsonify({
            "error": "Invalid PDF file"
        }), 400

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False
        ) as temp_file:

            temp_file.write(file_bytes)
            temp_path = temp_file.name

        # Upload original document
        uploaded = upload_document(temp_path)

        # Create cloud backup
        backup = backup_document(
            uploaded["cloud_name"]
        )

        if not backup["verified"]:
            raise ValueError(
                "Backup SHA-256 verification failed"
            )

        if (
            uploaded["checksum"]
            != backup["original_checksum"]
        ):
            raise ValueError(
                "Original file checksum mismatch"
            )

        # Save document metadata
        document_data = {
            "booking_id": int(booking_id),
            "file_name": filename,
            "file_path": (
                uploaded["bucket"]
                + "/"
                + uploaded["cloud_name"]
            ),
            "document_type": document_type,
            "file_size": uploaded["size_bytes"],
            "verification_status": "Verified",
            "storage_status": "Uploaded",
            "checksum_sha256": uploaded["checksum"]
        }

        document_rows = add_document(document_data)

        if not document_rows:
            raise RuntimeError(
                "Document record was not returned"
            )

        document_id = document_rows[0]["document_id"]

        # Save backup metadata
        backup_data = {
            "document_id": document_id,
            "backup_file_path": (
                backup["backup_bucket"]
                + "/"
                + backup["backup_file"]
            ),
            "backup_status": "Completed",
            "verification_status": "Verified",
            "original_checksum": backup["original_checksum"],
            "backup_checksum": backup["backup_checksum"],
            "recovery_status": "Not Required"
        }

        backup_rows = add_backup_record(backup_data)

        if not backup_rows:
            raise RuntimeError(
                "Backup record was not returned"
            )

        return jsonify({
            "success": True,
            "message": (
                "Cloud upload and verified backup completed"
            ),
            "document_id": document_id,
            "backup_id": backup_rows[0]["backup_id"],
            "verified": True
        }), 201

    except Exception:
        app.logger.exception(
            "Cloud upload failed"
        )

        return jsonify({
            "success": False,
            "error": (
                "Cloud upload could not be completed. "
                "Check the server log for details."
            )
        }), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ========================================
# CLOUD DASHBOARD
# ========================================

@app.route("/cloud-dashboard")
def cloud_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    try:
        documents = get_documents()
        backups = get_backup_records()

        verified_backups = count_verified_backups(
            backups
        )

        failed_backups = sum(
            1
            for backup in backups
            if (
                str(
                    backup.get("verification_status", "")
                ).lower() == "failed"
                or
                str(
                    backup.get("backup_status", "")
                ).lower() == "failed"
            )
        )

        stats = {
            "total_documents": len(documents),
            "total_backups": len(backups),
            "verified_backups": verified_backups,
            "failed_backups": failed_backups,
            "pending_backups": max(
                0,
                len(backups)
                - verified_backups
                - failed_backups
            )
        }

        return render_template(
            "cloud_dashboard.html",
            stats=stats,
            documents=documents,
            backups=backups
        )

    except Exception:
        app.logger.exception(
            "Cloud dashboard failed"
        )

        return jsonify({
            "error": "Unable to load cloud dashboard"
        }), 500


# ========================================
# RECOVERY STATUS
# ========================================

@app.route(
    "/recovery-status/<int:backup_id>",
    methods=["GET"]
)
def recovery_status_check(backup_id):

    if not session.get("admin_logged_in"):
        return jsonify({
            "error": "Unauthorized"
        }), 401

    from supabase_client import get_recovery_details

    try:
        details = get_recovery_details(
            backup_id
        )

        return jsonify({
            "success": True,
            "backup_id": details["backup_id"],
            "document_id": details["document_id"],
            "recovery_status": details["recovery_status"],
            "message": "Recovery metadata retrieved"
        }), 200

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 404

    except Exception:
        app.logger.exception(
            "Recovery status check failed"
        )

        return jsonify({
            "success": False,
            "error": "Unable to retrieve recovery status"
        }), 500


# ========================================
# ADMIN LOGIN
# ========================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
@limiter.limit(
    "5 per minute",
    methods=["POST"]
)
def admin_login():

    if session.get("admin_logged_in"):
        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "POST":

        password = request.form.get(
            "password", ""
        )

        stored_hash = os.getenv(
            "ADMIN_PASSWORD_HASH"
        )

        if not stored_hash:
            app.logger.error(
                "Admin password hash is missing"
            )

            return render_template(
                "admin_login.html",
                error=(
                    "Administrator login is unavailable."
                )
            ), 503

        if check_password_hash(
            stored_hash,
            password
        ):

            session.clear()
            session.permanent = True
            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )

        return render_template(
            "admin_login.html",
            error="Incorrect administrator password."
        ), 401

    return render_template(
        "admin_login.html"
    )


# ========================================
# ADMIN LOGOUT
# ========================================

@app.route("/admin-logout", methods=["GET"])
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ========================================
# RUN APPLICATION
# ========================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
