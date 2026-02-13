"""
Criminal Detection System - Web Application
Flask backend: auth, criminal registration, face detection/recognition, CCTV frame API.
"""
import os

# Ensure process CWD is project root (for face_samples, face_cascade.xml)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.getcwd() != BASE_DIR:
    os.chdir(BASE_DIR)

import json
import base64
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps

# Local modules (face recognition, registration, DB)
from facerec import train_model, detect_faces, recognize_face
from register import registerCriminal
from dbHandler import insertData, retrieveData

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "criminal-detection-web-secret-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

USERS_FILE = os.path.join(BASE_DIR, "users.json")
FACE_SAMPLES_DIR = os.path.join(BASE_DIR, "face_samples")
PROFILE_PICS_DIR = os.path.join(BASE_DIR, "profile_pics")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# In-memory store for recent detections (per server); optional: persist to file/DB
recent_detections = []

for d in (UPLOAD_FOLDER, PROFILE_PICS_DIR):
    os.makedirs(d, exist_ok=True)


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def save_users(users):
    if "admin@1234" not in users:
        users["admin@1234"] = "12345678"
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET"])
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/register-criminal")
@login_required
def register_criminal_page():
    return render_template("register_criminal.html")


@app.route("/detect")
@login_required
def detect_page():
    return render_template("detect.html")


@app.route("/cctv")
@login_required
def cctv_page():
    return render_template("cctv.html")


# ---------- Auth API ----------
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password required"}), 400
    users = load_users()
    if users.get(username) != password:
        return jsonify({"ok": False, "error": "Invalid username or password"}), 401
    session["logged_in"] = True
    session["username"] = username
    return jsonify({"ok": True, "redirect": url_for("dashboard")})


@app.route("/api/auth/signup", methods=["POST"])
def api_signup():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm") or ""
    if not username or not password or not confirm:
        return jsonify({"ok": False, "error": "All fields are required"}), 400
    if password != confirm:
        return jsonify({"ok": False, "error": "Passwords do not match"}), 400
    if len(password) < 4:
        return jsonify({"ok": False, "error": "Password must be at least 4 characters"}), 400
    users = load_users()
    if username in users:
        return jsonify({"ok": False, "error": "Username already exists"}), 400
    users[username] = password
    save_users(users)
    return jsonify({"ok": True, "message": "Account created. Please login.", "redirect": url_for("login_page")})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True, "redirect": url_for("login_page")})


# ---------- Criminal registration (multipart: images + form) ----------
@app.route("/api/criminal/register", methods=["POST"])
@login_required
def api_register_criminal():
    if "images[]" not in request.files and "images" not in request.files:
        return jsonify({"ok": False, "error": "No images uploaded"}), 400

    files = request.files.getlist("images[]") or request.files.getlist("images")
    if len(files) < 5:
        return jsonify({"ok": False, "error": "At least 5 images are required"}), 400

    # Build entry_data from form
    entry_data = {
        "Name": request.form.get("name", "").strip().lower(),
        "Father's Name": request.form.get("father_name", "").strip().lower(),
        "Mother's Name": request.form.get("mother_name", "").strip().lower(),
        "Gender": request.form.get("gender", "").strip().lower(),
        "DOB(yyyy-mm-dd)": request.form.get("dob", "").strip(),
        "Blood Group": request.form.get("blood_group", "").strip().lower(),
        "Identification Mark": request.form.get("identification_mark", "").strip().lower(),
        "Nationality": request.form.get("nationality", "").strip().lower(),
        "Religion": request.form.get("religion", "").strip().lower(),
        "Crimes Done": request.form.get("crimes_done", "").strip().lower(),
    }
    required = ["Name", "Gender", "Identification Mark", "Nationality", "Religion", "Crimes Done"]
    for field in required:
        if not entry_data.get(field):
            return jsonify({"ok": False, "error": f"Required field missing: {field}"}), 400

    path = os.path.join(FACE_SAMPLES_DIR, "temp_criminal")
    os.makedirs(path, exist_ok=True)
    img_list = []

    try:
        for i, f in enumerate(files):
            if not f.filename:
                continue
            buf = f.read()
            if not buf:
                continue
            nparr = np.frombuffer(buf, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                continue
            img_list.append(img)
        if len(img_list) < 5:
            return jsonify({"ok": False, "error": "At least 5 valid images are required"}), 400

        no_face = []
        for i, img in enumerate(img_list):
            idx = registerCriminal(img, path, i + 1)
            if idx is not None:
                no_face.append(idx)
        if no_face:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
            return jsonify({"ok": False, "error": f"Images without face or too small: {no_face}"}), 400

        row_id = insertData(entry_data)
        if row_id <= 0:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
            return jsonify({"ok": False, "error": "Database error while storing data"}), 500

        dest_dir = os.path.join(FACE_SAMPLES_DIR, entry_data["Name"])
        if os.path.exists(dest_dir):
            import shutil
            shutil.rmtree(dest_dir, ignore_errors=True)
        os.rename(path, dest_dir)

        profile_idx = min(int(request.form.get("profile_image_index", 1)) - 1, len(img_list) - 1)
        profile_img = img_list[profile_idx]
        cv2.imwrite(os.path.join(PROFILE_PICS_DIR, "criminal %d.png" % row_id), profile_img)

        return jsonify({"ok": True, "message": "Criminal registered successfully", "id": row_id})
    except Exception as e:
        import shutil
        shutil.rmtree(path, ignore_errors=True)
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------- Detect criminal from single image ----------
@app.route("/api/criminal/detect", methods=["POST"])
@login_required
def api_detect():
    if "image" not in request.files and not request.get_data():
        return jsonify({"ok": False, "error": "No image provided"}), 400

    img = None
    if "image" in request.files:
        f = request.files["image"]
        if f.filename:
            buf = f.read()
            nparr = np.frombuffer(buf, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None and request.get_data():
        # Base64 from body (e.g. canvas data URL)
        try:
            data = request.get_json() or {}
            b64 = data.get("image") or request.get_data().decode()
            if b64.startswith("data:image"):
                b64 = b64.split(",", 1)[-1]
            buf = base64.b64decode(b64)
            nparr = np.frombuffer(buf, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            pass

    if img is None:
        return jsonify({"ok": False, "error": "Invalid or missing image"}), 400

    frame = cv2.flip(img, 1, 0)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_coords = detect_faces(gray)
    if len(face_coords) == 0:
        return jsonify({"ok": False, "error": "No face found in image or face too small"}), 400

    model, names = train_model()
    frame, recognized = recognize_face(model, frame, gray, face_coords, names)
    if not recognized:
        return jsonify({"ok": False, "error": "No criminal recognized"}), 200

    for name, _ in recognized:
        recent_detections.insert(0, (name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        if len(recent_detections) > 20:
            recent_detections.pop()

    return jsonify({"ok": True, "recognized": [{"name": r[0], "confidence": float(r[1])} for r in recognized]})


# ---------- Recognize from base64 frame (CCTV) ----------
@app.route("/api/criminal/recognize-frame", methods=["POST"])
@login_required
def api_recognize_frame():
    data = request.get_json() or {}
    b64 = data.get("frame")
    if not b64:
        return jsonify({"ok": False, "error": "No frame"}), 400
    try:
        if b64.startswith("data:image"):
            b64 = b64.split(",", 1)[-1]
        buf = base64.b64decode(b64)
        nparr = np.frombuffer(buf, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({"ok": False, "error": "Invalid image: " + str(e)}), 400
    if img is None:
        return jsonify({"ok": False, "error": "Could not decode image"}), 400

    frame = cv2.flip(img, 1, 0)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_coords = detect_faces(gray)
    if len(face_coords) == 0:
        return jsonify({"ok": True, "recognized": []})

    model, names = train_model()
    _, recognized = recognize_face(model, frame, gray, face_coords, names)
    for name, _ in recognized:
        recent_detections.insert(0, (name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    while len(recent_detections) > 20:
        recent_detections.pop()

    return jsonify({"ok": True, "recognized": [{"name": r[0], "confidence": float(r[1])} for r in recognized]})


# ---------- Criminal profile by name ----------
@app.route("/api/criminal/<name>")
@login_required
def api_criminal_profile(name):
    id_val, criminaldata = retrieveData(name)
    if id_val is None:
        return jsonify({"ok": False, "error": "Not found"}), 404
    profile_path = os.path.join(PROFILE_PICS_DIR, "criminal %d.png" % id_val)
    has_photo = os.path.isfile(profile_path)
    return jsonify({
        "ok": True,
        "id": id_val,
        "data": criminaldata,
        "profile_url": url_for("profile_pic", id=id_val) if has_photo else None,
    })


@app.route("/profile_pics/<int:id>.png")
@login_required
def profile_pic(id):
    return send_from_directory(PROFILE_PICS_DIR, "criminal %d.png" % id, mimetype="image/png")


# ---------- Recent detections (for CCTV page) ----------
@app.route("/api/recent-detections")
@login_required
def api_recent_detections():
    return jsonify({"ok": True, "detections": recent_detections[:10]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print("\n  Open in your browser: http://127.0.0.1:{}\n".format(port))
    app.run(host="127.0.0.1", port=port, debug=True)
