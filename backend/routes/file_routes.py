from flask import Blueprint, request, jsonify
import os
import uuid
import psycopg2
from config import DB_URL
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.s3_services import upload_file_to_s3  # make sure the file name matches
from services.encryption_service import encrypt_file
from services.audit_service import log_event

# for download
from flask import send_file
import io
from services.s3_services import download_file_from_s3
from services.encryption_service import decrypt_file


files = Blueprint("files", __name__)

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# Local upload route
@files.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    return jsonify({"message": "File uploaded successfully", "filename": filename})


""" # S3 upload route
@files.route("/upload_s3", methods=["POST"])
def upload_file_s3_route():  # changed function name to avoid conflict
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = f"{uuid.uuid4()}_{file.filename}"
    url = upload_file_to_s3(file, filename)  # call the function from s3_services

    return jsonify({"message": "File uploaded to S3 successfully", "url": url}) 
"""


# S3 upload route (SECURE VERSION)
@files.route("/upload_s3", methods=["POST"])
@jwt_required()
def upload_file_s3_route():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    user_id = get_jwt_identity()

    # Read file bytes
    file_bytes = file.read()
    file_size = len(file_bytes)
    # Encrypt file
    encrypted_data = encrypt_file(file_bytes)

    # Generate ID + S3 key
    file_id = str(uuid.uuid4())
    s3_key = f"{file_id}_{file.filename}"

    # Upload encrypted file to S3
    upload_file_to_s3(
        file_obj=encrypted_data,
        filename=s3_key
    )

    # Save metadata in DB
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO files (id, filename, s3_key, uploaded_by, file_size)
    VALUES (%s, %s, %s, %s, %s)
    """, (file_id, file.filename, s3_key, user_id, file_size))

    conn.commit()
    cur.close()
    conn.close()

    # Log audit event
    log_event(user_id, file_id, "UPLOAD")

    return jsonify({
        "message": "Encrypted file uploaded successfully",
        "file_id": file_id
    })


# S3 download route (SECURE VERSION)
@files.route("/download/<file_id>", methods=["GET"])
@jwt_required()
def download_file_s3(file_id):

    user_id = get_jwt_identity()

    # Connect to DB
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Get file metadata
    cur.execute("""
        SELECT filename, s3_key, uploaded_by
        FROM files
        WHERE id = %s
    """, (file_id,))

    file_record = cur.fetchone()

    if not file_record:
        cur.close()
        conn.close()
        return jsonify({"error": "File not found"}), 404

    filename, s3_key, uploaded_by = file_record

    # Authorization check (only owner can download)
    if str(uploaded_by) != str(user_id):
        cur.close()
        conn.close()
        return jsonify({"error": "Unauthorized access"}), 403

    cur.close()
    conn.close()

    # Download encrypted file from S3
    encrypted_data = download_file_from_s3(s3_key)

    # Decrypt file
    decrypted_data = decrypt_file(encrypted_data)

    # Log audit event
    log_event(user_id, file_id, "DOWNLOAD")

    # Send file to user
    return send_file(
        io.BytesIO(decrypted_data),
        download_name=filename,
        as_attachment=True
    )
    # GET all files for logged-in user
@files.route("/files", methods=["GET"])
@jwt_required()
def list_user_files():

    user_id = get_jwt_identity()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, uploaded_at, file_size
        FROM files
        WHERE uploaded_by = %s
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
    "files": [
        {
            "id": row[0],
            "filename": row[1],
            "uploaded_at": row[2],
            "file_size": row[3]
        }
        for row in rows
    ]
})
@files.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():

    user_id = get_jwt_identity()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT username
        FROM users
        WHERE id = %s
    """, (user_id,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "username": user[0]
    })
    # ================= DELETE FILE =================
@files.route("/delete/<file_id>", methods=["DELETE"])
@jwt_required()
def delete_file(file_id):

    user_id = get_jwt_identity()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT s3_key, uploaded_by
        FROM files
        WHERE id=%s
    """, (file_id,))

    file_record = cur.fetchone()

    if not file_record:
        return jsonify({"error": "File not found"}), 404

    s3_key, uploaded_by = file_record

    if str(uploaded_by) != str(user_id):
        return jsonify({"error": "Unauthorized"}), 403

    # delete from S3
    from services.s3_services import delete_file_from_s3
    delete_file_from_s3(s3_key)

    # delete DB record
    # delete audit logs first
    cur.execute(
        "DELETE FROM audit_logs WHERE file_id=%s",
        (file_id,)
    )

# then delete file record
    cur.execute(
        "DELETE FROM files WHERE id=%s",
        (file_id,)
    )

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"message": "File deleted successfully"})