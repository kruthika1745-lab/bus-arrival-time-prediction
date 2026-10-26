from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import joblib

app = Flask(__name__)
app.secret_key = "bus_prediction_secret"


# =========================================================
# DATABASE INITIALIZATION
# =========================================================
def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # ---------------- USERS TABLE ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # ---------------- PREDICTIONS TABLE ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            destination TEXT,
            distance REAL,
            traffic INTEGER,
            weather INTEGER,
            speed REAL,
            prediction REAL,
            created_at TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [col[1] for col in cursor.fetchall()]
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE predictions ADD COLUMN user_id INTEGER")
    conn.commit()
    conn.close()


# Initialize database
init_db()


# =========================================================
# LOAD MACHINE LEARNING MODEL
# =========================================================
model = joblib.load("model/model.pkl")


# =========================================================
# REGISTER
# =========================================================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # Check empty fields
        if not username or not email or not password or not confirm:

            flash("Please fill all fields!", "danger")

            return redirect(url_for("register"))

        # Check password
        if password != confirm:

            flash("Passwords do not match!", "danger")

            return redirect(url_for("register"))

        # Connect database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        )

        user = cursor.fetchone()

        if user:

            conn.close()

            flash("Email already exists! Please login.", "warning")

            return redirect(url_for("login"))

        # Hash password
        hashed_password = generate_password_hash(password)

        # Insert user
        cursor.execute("""
            INSERT INTO users(username, email, password)
            VALUES (?, ?, ?)
        """, (
            username,
            email,
            hashed_password
        ))

        conn.commit()
        conn.close()

        flash("Registration Successful! Please Login.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # Get email and password
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Debug messages
        print("================================")
        print("Entered Email:", email)
        print("Entered Password:", password)

        # Check empty fields
        if not email or not password:

            flash("Please enter email and password!", "danger")

            return render_template("login.html")

        # Connect database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Search user by email
        cursor.execute("""
            SELECT id, username, email, password
            FROM users
            WHERE email = ?
        """, (email,))

        user = cursor.fetchone()

        conn.close()

        print("User from database:", user)
        print("================================")

        # Email not found
        if user is None:

            flash("Email not registered!", "danger")

            return render_template("login.html")

        # Check password
        if check_password_hash(user[3], password):

            # Store login information
            session["user"] = user[0]
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["email"] = user[2]

            flash("Login successful!", "success")

            return redirect(url_for("home"))

        else:

            flash("Incorrect password!", "danger")

            return render_template("login.html")

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully!", "success")

    return redirect(url_for("login"))


# =========================================================
# HOME
# =========================================================
@app.route("/")
def home():

    # Check login
    if "user" not in session:

        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Total predictions
    cursor.execute("""
        SELECT COUNT(*)
        FROM predictions
    """)

    total_predictions = cursor.fetchone()[0]

    # Average prediction
    cursor.execute("""
        SELECT AVG(prediction)
        FROM predictions
    """)

    avg = cursor.fetchone()[0]

    average_prediction = round(avg, 2) if avg else 0

    # Latest prediction
    cursor.execute("""
        SELECT prediction
        FROM predictions
        ORDER BY id DESC
        LIMIT 1
    """)

    latest = cursor.fetchone()

    latest_prediction = round(latest[0], 2) if latest else 0

    conn.close()

    return render_template(
        "index.html",
        total_predictions=total_predictions,
        average_prediction=average_prediction,
        latest_prediction=latest_prediction
    )


# =========================================================
# PREDICTION
# =========================================================
@app.route("/predict", methods=["POST"])
def predict():

    # Check login
    if "user" not in session:

        return redirect(url_for("login"))

    source = request.form.get("source")
    destination = request.form.get("destination")

    distance = float(request.form["distance"])
    traffic = int(request.form["traffic"])
    weather = int(request.form["weather"])
    speed = float(request.form["speed"])

    # ML prediction
    prediction = model.predict([
        [distance, traffic, weather, speed]
    ])[0]

    # Current date and time
    current_time = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    # Save prediction
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO predictions
        (source, destination, distance, traffic, weather, speed, prediction, created_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source, destination, distance, traffic, weather, speed,
        float(prediction), current_time, session["user_id"]
    ))
    

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        prediction=round(float(prediction), 2)
    )


# =========================================================
# HISTORY
# =========================================================
@app.route("/history")
def history():

    # Check login
    if "user" not in session:

        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],))

    predictions = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        predictions=predictions
    )


# =========================================================
# CONTACT
# =========================================================
@app.route("/contact")
def contact():

    # Check login
    if "user" not in session:

        return redirect(url_for("login"))

    return render_template("contact.html")


# =========================================================
# RUN APPLICATION
# =========================================================
if __name__ == "__main__":

    app.run(debug=True)