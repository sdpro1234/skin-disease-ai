import os
import sqlite3
import base64
from flask import Flask, render_template, request, redirect, session, jsonify
import google.generativeai as genai
from PIL import Image
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret")

# ==================================
# Gemini API Configuration
# ==================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

# ==================================
# Database Setup
# ==================================

DB_NAME = "users.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ==================================
# Routes
# ==================================

@app.route("/")
def home():
    return redirect("/login")

# ---------------- Register ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username","").strip()
        email = request.form.get("email","").strip()
        password = request.form.get("password","")
        confirm_password = request.form.get("confirm_password","")

        if not username or not email or not password:
            return "All fields required", 400

        if password != confirm_password:
            return "Passwords do not match", 400

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username,email,password) VALUES (?,?,?)",
                (username,email,password)
            )
            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "User already exists", 400

        conn.close()

        return redirect("/login")

    return render_template("register.html")

# ---------------- Login ----------------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username,password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return "Invalid credentials"

    return render_template("login.html")

# ---------------- Dashboard ----------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html")

# ---------------- AI Prediction ----------------

@app.route("/predict", methods=["POST"])
def predict():

    if "user" not in session:
        return jsonify({"error":"Unauthorized"}), 401

    try:
        data = request.json["image"]

        image_data = data.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        img = Image.open(BytesIO(image_bytes))

        prompt = """
Analyze this skin image and provide:

1. Possible Skin Disease
2. Severity Level (Mild / Moderate / Severe)
3. Health Recommendation
4. Preventive Measures

Answer clearly.
"""

        response = model.generate_content([prompt, img])

        result = response.text

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- Logout ----------------

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/login")

# ---------------- Run ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)