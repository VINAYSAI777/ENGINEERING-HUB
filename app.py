import os, sqlite3, secrets
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DB = Path(os.environ.get("DATABASE_PATH", "engineering_hub.db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_FOLDER", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {"pdf", "png", "jpg", "jpeg", "txt", "zip"}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, is_admin INTEGER DEFAULT 0)""")
        con.execute("""CREATE TABLE IF NOT EXISTS resources(
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, branch TEXT, year TEXT,
            semester TEXT, category TEXT, description TEXT, filename TEXT,
            video_url TEXT, uploader INTEGER, approved INTEGER DEFAULT 0)""")
        admin_email = os.environ.get("ADMIN_EMAIL")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if admin_email and admin_password:
            found = con.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
            if not found:
                con.execute("INSERT INTO users(name,email,password,is_admin) VALUES(?,?,?,1)",
                            ("Administrator", admin_email, generate_password_hash(admin_password)))

init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in first.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Administrator access is required.")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    branch = request.args.get("branch", "")
    with connect() as con:
        sql = "SELECT resources.*, users.name AS uploader_name FROM resources LEFT JOIN users ON users.id=resources.uploader WHERE approved=1"
        args = []
        if q:
            sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
            args += [f"%{q}%"] * 3
        if branch:
            sql += " AND branch=?"
            args.append(branch)
        sql += " ORDER BY resources.id DESC"
        resources = con.execute(sql, args).fetchall()
    return render_template("index.html", resources=resources, q=q, branch=branch)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email, password = request.form["name"].strip(), request.form["email"].strip().lower(), request.form["password"]
        if len(password) < 8:
            flash("Use a password with at least 8 characters.")
        else:
            try:
                with connect() as con:
                    con.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                                (name, email, generate_password_hash(password)))
                flash("Account created. Please sign in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered.")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with connect() as con:
            user = con.execute("SELECT * FROM users WHERE email=?", (request.form["email"].strip().lower(),)).fetchone()
        if user and check_password_hash(user["password"], request.form["password"]):
            session.update(user_id=user["id"], name=user["name"], is_admin=bool(user["is_admin"]))
            return redirect(url_for("admin") if user["is_admin"] else url_for("index"))
        flash("Email or password is incorrect.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = request.form["title"].strip()
        video_url = request.form.get("video_url", "").strip()
        file = request.files.get("file")
        filename = None
        if file and file.filename:
            safe = secure_filename(file.filename)
            if "." not in safe or safe.rsplit(".", 1)[1].lower() not in ALLOWED:
                flash("Allowed files: PDF, PNG, JPG, TXT and ZIP.")
                return redirect(url_for("upload"))
            filename = f"{secrets.token_hex(8)}_{safe}"
            file.save(UPLOAD_DIR / filename)
        if not title or (not filename and not video_url):
            flash("Add a title and either a file or a video link.")
            return redirect(url_for("upload"))
        with connect() as con:
            con.execute("""INSERT INTO resources(title,branch,year,semester,category,description,filename,video_url,uploader)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (title, request.form.get("branch"), request.form.get("year"),
                 request.form.get("semester"), request.form.get("category"),
                 request.form.get("description"), filename, video_url, session["user_id"]))
        flash("Submitted! Your resource will appear after administrator approval.")
        return redirect(url_for("index"))
    return render_template("upload.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

@app.route("/admin")
@login_required
@admin_required
def admin():
    with connect() as con:
        resources = con.execute("SELECT * FROM resources WHERE approved=0 ORDER BY id DESC").fetchall()
    return render_template("admin.html", resources=resources)

@app.route("/approve/<int:resource_id>", methods=["POST"])
@login_required
@admin_required
def approve(resource_id):
    with connect() as con:
        con.execute("UPDATE resources SET approved=1 WHERE id=?", (resource_id,))
    flash("Resource approved.")
    return redirect(url_for("admin"))

@app.route("/delete/<int:resource_id>", methods=["POST"])
@login_required
@admin_required
def delete(resource_id):
    with connect() as con:
        row = con.execute("SELECT filename FROM resources WHERE id=?", (resource_id,)).fetchone()
        con.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    if row and row["filename"]:
        try: (UPLOAD_DIR / row["filename"]).unlink()
        except FileNotFoundError: pass
    flash("Resource deleted.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
