"""Flask admin application for BT Construction."""

import os
import re
import json
import time
import smtplib
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from functools import wraps

import bcrypt
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory
)
from flask_wtf.csrf import CSRFProtect

import admin_config
from config import Config
import data_manager as dm

app = Flask(__name__)
app.secret_key = admin_config.SECRET_KEY
app.config["WTF_CSRF_TIME_LIMIT"] = None

csrf = CSRFProtect(app)

# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per-IP)
# ---------------------------------------------------------------------------
_rate_limits = {}  # key -> {ip -> list of timestamps}
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60  # seconds
SUBMISSION_RATE_LIMIT_MAX = 3
SUBMISSION_RATE_LIMIT_WINDOW = 300  # 5 minutes


def _is_rate_limited(ip, bucket="login", max_attempts=RATE_LIMIT_MAX, window=RATE_LIMIT_WINDOW):
    """Return True if this IP has exceeded attempt limits for the given bucket."""
    now = time.time()
    store = _rate_limits.setdefault(bucket, {})
    attempts = store.get(ip, [])
    attempts = [t for t in attempts if now - t < window]
    store[ip] = attempts
    return len(attempts) >= max_attempts


def _record_attempt(ip, bucket="login"):
    """Record an attempt for rate limiting."""
    _rate_limits.setdefault(bucket, {}).setdefault(ip, []).append(time.time())


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(f):
    """Decorator to require authentication and enforce session timeout."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        last_active = session.get("last_active")
        if last_active:
            elapsed = datetime.utcnow() - datetime.fromisoformat(last_active)
            if elapsed > timedelta(minutes=admin_config.SESSION_TIMEOUT_MINUTES):
                session.clear()
                flash("Session expired. Please log in again.", "warning")
                return redirect(url_for("login"))
        session["last_active"] = datetime.utcnow().isoformat()
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def _get_last_rebuild():
    """Read the last rebuild timestamp, or None."""
    path = Config.REBUILD_TIMESTAMP_FILE
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    return None


def _save_rebuild_timestamp():
    """Save current timestamp as last rebuild time."""
    path = Config.REBUILD_TIMESTAMP_FILE
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(datetime.now().strftime("%Y-%m-%d %I:%M %p"))


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load_settings():
    """Load settings.json and return dict (empty dict if missing)."""
    if os.path.isfile(Config.SETTINGS_FILE):
        with open(Config.SETTINGS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def send_notification_email(subject, body, reply_to=None):
    """Send an email notification in a background thread.

    Reads SMTP config from settings.json. Silently skips if not configured.
    """
    settings = _load_settings()
    smtp = settings.get("smtp", {})
    to_email = settings.get("notification_email", "").strip()

    host = (smtp.get("host") or "").strip()
    user = (smtp.get("user") or "").strip()
    password = (smtp.get("password") or "").strip()
    port = int(smtp.get("port") or 587)

    if not host or not user or not to_email:
        return  # SMTP not configured, skip silently

    def _send():
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = to_email
            if reply_to:
                msg["Reply-To"] = reply_to

            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(user, [to_email], msg.as_string())
        except Exception:
            pass  # Fail silently — don't break form submission

    threading.Thread(target=_send, daemon=True).start()


# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(Config.OUTPUT_DIR, "index.html")


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        ip = request.remote_addr
        if _is_rate_limited(ip):
            flash("Too many login attempts. Please wait a minute.", "error")
            return render_template("admin/login.html")

        _record_attempt(ip)
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == admin_config.ADMIN_USERNAME
            and bcrypt.checkpw(
                password.encode("utf-8"),
                admin_config.ADMIN_PASSWORD_HASH.encode("utf-8"),
            )
        ):
            session["user"] = username
            session["last_active"] = datetime.utcnow().isoformat()
            flash("Welcome back, Calvin!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("admin/login.html")


@app.route("/admin/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------
@app.route("/admin/")
@login_required
def dashboard():
    counts = {
        "portfolio": dm.count_items(Config.PORTFOLIO_DIR),
        "testimonials": dm.count_items(Config.TESTIMONIALS_DIR),
        "services": dm.count_items(Config.SERVICES_DIR),
        "blog": dm.count_items(Config.BLOG_DIR),
        "contact": dm.count_items(Config.CONTACT_DIR),
        "quotes": dm.count_items(Config.QUOTES_DIR),
    }
    unread = {
        "contact": dm.count_unread(Config.CONTACT_DIR),
        "quotes": dm.count_unread(Config.QUOTES_DIR),
    }
    last_rebuild = _get_last_rebuild()
    return render_template(
        "admin/dashboard.html",
        counts=counts,
        unread=unread,
        last_rebuild=last_rebuild,
    )


# ---------------------------------------------------------------------------
# Routes — Rebuild
# ---------------------------------------------------------------------------
@app.route("/admin/rebuild", methods=["POST"])
@login_required
def rebuild():
    try:
        import generator
        generator.build()
        _save_rebuild_timestamp()
        flash("Site rebuilt successfully!", "success")
    except Exception as e:
        flash(f"Rebuild failed: {e}", "error")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Routes — Testimonials CRUD
# ---------------------------------------------------------------------------
@app.route("/admin/testimonials")
@login_required
def testimonials_list():
    items = dm.list_items(Config.TESTIMONIALS_DIR)
    return render_template("admin/testimonials_list.html", items=items)


@app.route("/admin/testimonials/new", methods=["GET", "POST"])
@login_required
def testimonial_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = dm.generate_slug(name)
        slug = dm.ensure_unique_slug(Config.TESTIMONIALS_DIR, slug)
        data = {
            "slug": slug,
            "name": name,
            "location": request.form.get("location", "").strip(),
            "project_type": request.form.get("project_type", "").strip(),
            "rating": int(request.form.get("rating", 5)),
            "text": request.form.get("text", "").strip(),
            "date": request.form.get("date", _today()),
            "featured": "featured" in request.form,
        }
        dm.save_item(Config.TESTIMONIALS_DIR, slug, data)
        flash("Testimonial created!", "success")
        return redirect(url_for("testimonials_list"))
    return render_template("admin/testimonials_form.html", item=None, today=_today())


@app.route("/admin/testimonials/<slug>/edit", methods=["GET", "POST"])
@login_required
def testimonial_edit(slug):
    item = dm.get_item(Config.TESTIMONIALS_DIR, slug)
    if not item:
        flash("Testimonial not found.", "error")
        return redirect(url_for("testimonials_list"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        new_slug = dm.generate_slug(name)
        new_slug = dm.ensure_unique_slug(Config.TESTIMONIALS_DIR, new_slug, exclude=slug)
        data = {
            "slug": new_slug,
            "name": name,
            "location": request.form.get("location", "").strip(),
            "project_type": request.form.get("project_type", "").strip(),
            "rating": int(request.form.get("rating", 5)),
            "text": request.form.get("text", "").strip(),
            "date": request.form.get("date", _today()),
            "featured": "featured" in request.form,
        }
        if new_slug != slug:
            dm.delete_item(Config.TESTIMONIALS_DIR, slug)
        dm.save_item(Config.TESTIMONIALS_DIR, new_slug, data)
        flash("Testimonial updated!", "success")
        return redirect(url_for("testimonials_list"))
    return render_template("admin/testimonials_form.html", item=item, today=_today())


@app.route("/admin/testimonials/<slug>/delete", methods=["POST"])
@login_required
def testimonial_delete(slug):
    if dm.delete_item(Config.TESTIMONIALS_DIR, slug):
        flash("Testimonial deleted.", "success")
    else:
        flash("Testimonial not found.", "error")
    return redirect(url_for("testimonials_list"))


# ---------------------------------------------------------------------------
# Routes — Services CRUD
# ---------------------------------------------------------------------------
@app.route("/admin/services")
@login_required
def services_list():
    items = dm.list_items(Config.SERVICES_DIR)
    return render_template("admin/services_list.html", items=items)


@app.route("/admin/services/new", methods=["GET", "POST"])
@login_required
def service_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = dm.generate_slug(title)
        slug = dm.ensure_unique_slug(Config.SERVICES_DIR, slug)
        features = [f.strip() for f in request.form.getlist("features") if f.strip()]
        data = {
            "slug": slug,
            "title": title,
            "short_description": request.form.get("short_description", "").strip(),
            "description": request.form.get("description", "").strip(),
            "icon": request.form.get("icon", "").strip(),
            "image": request.form.get("image", "").strip(),
            "featured": "featured" in request.form,
            "features": features,
        }
        dm.save_item(Config.SERVICES_DIR, slug, data)
        flash("Service created!", "success")
        return redirect(url_for("services_list"))
    return render_template("admin/services_form.html", item=None)


@app.route("/admin/services/<slug>/edit", methods=["GET", "POST"])
@login_required
def service_edit(slug):
    item = dm.get_item(Config.SERVICES_DIR, slug)
    if not item:
        flash("Service not found.", "error")
        return redirect(url_for("services_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        new_slug = dm.generate_slug(title)
        new_slug = dm.ensure_unique_slug(Config.SERVICES_DIR, new_slug, exclude=slug)
        features = [f.strip() for f in request.form.getlist("features") if f.strip()]
        data = {
            "slug": new_slug,
            "title": title,
            "short_description": request.form.get("short_description", "").strip(),
            "description": request.form.get("description", "").strip(),
            "icon": request.form.get("icon", "").strip(),
            "image": request.form.get("image", "").strip(),
            "featured": "featured" in request.form,
            "features": features,
        }
        if new_slug != slug:
            dm.delete_item(Config.SERVICES_DIR, slug)
        dm.save_item(Config.SERVICES_DIR, new_slug, data)
        flash("Service updated!", "success")
        return redirect(url_for("services_list"))
    return render_template("admin/services_form.html", item=item)


@app.route("/admin/services/<slug>/delete", methods=["POST"])
@login_required
def service_delete(slug):
    if dm.delete_item(Config.SERVICES_DIR, slug):
        flash("Service deleted.", "success")
    else:
        flash("Service not found.", "error")
    return redirect(url_for("services_list"))


# ---------------------------------------------------------------------------
# Routes — Portfolio CRUD
# ---------------------------------------------------------------------------
@app.route("/admin/portfolio")
@login_required
def portfolio_list():
    items = dm.list_items(Config.PORTFOLIO_DIR)
    return render_template("admin/portfolio_list.html", items=items)


@app.route("/admin/portfolio/new", methods=["GET", "POST"])
@login_required
def portfolio_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = dm.generate_slug(title)
        slug = dm.ensure_unique_slug(Config.PORTFOLIO_DIR, slug)
        images = [i.strip() for i in request.form.getlist("images") if i.strip()]
        data = {
            "slug": slug,
            "title": title,
            "category": request.form.get("category", "").strip(),
            "short_description": request.form.get("short_description", "").strip(),
            "description": request.form.get("description", "").strip(),
            "completion_date": request.form.get("completion_date", ""),
            "location": request.form.get("location", "").strip(),
            "featured": "featured" in request.form,
            "images": images,
            "before_after": "before_after" in request.form,
            "before_image": request.form.get("before_image", "").strip(),
            "after_image": request.form.get("after_image", "").strip(),
            "youtube_url": request.form.get("youtube_url", "").strip(),
        }
        dm.save_item(Config.PORTFOLIO_DIR, slug, data)
        flash("Portfolio project created!", "success")
        return redirect(url_for("portfolio_list"))
    return render_template("admin/portfolio_form.html", item=None, today=_today())


@app.route("/admin/portfolio/<slug>/edit", methods=["GET", "POST"])
@login_required
def portfolio_edit(slug):
    item = dm.get_item(Config.PORTFOLIO_DIR, slug)
    if not item:
        flash("Portfolio project not found.", "error")
        return redirect(url_for("portfolio_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        new_slug = dm.generate_slug(title)
        new_slug = dm.ensure_unique_slug(Config.PORTFOLIO_DIR, new_slug, exclude=slug)
        images = [i.strip() for i in request.form.getlist("images") if i.strip()]
        data = {
            "slug": new_slug,
            "title": title,
            "category": request.form.get("category", "").strip(),
            "short_description": request.form.get("short_description", "").strip(),
            "description": request.form.get("description", "").strip(),
            "completion_date": request.form.get("completion_date", ""),
            "location": request.form.get("location", "").strip(),
            "featured": "featured" in request.form,
            "images": images,
            "before_after": "before_after" in request.form,
            "before_image": request.form.get("before_image", "").strip(),
            "after_image": request.form.get("after_image", "").strip(),
            "youtube_url": request.form.get("youtube_url", "").strip(),
        }
        if new_slug != slug:
            dm.delete_item(Config.PORTFOLIO_DIR, slug)
        dm.save_item(Config.PORTFOLIO_DIR, new_slug, data)
        flash("Portfolio project updated!", "success")
        return redirect(url_for("portfolio_list"))
    return render_template("admin/portfolio_form.html", item=item, today=_today())


@app.route("/admin/portfolio/<slug>/delete", methods=["POST"])
@login_required
def portfolio_delete(slug):
    if dm.delete_item(Config.PORTFOLIO_DIR, slug):
        flash("Portfolio project deleted.", "success")
    else:
        flash("Portfolio project not found.", "error")
    return redirect(url_for("portfolio_list"))


# ---------------------------------------------------------------------------
# Routes — Blog CRUD
# ---------------------------------------------------------------------------
@app.route("/admin/blog")
@login_required
def blog_list():
    items = dm.list_items(Config.BLOG_DIR)
    return render_template("admin/blog_list.html", items=items)


@app.route("/admin/blog/new", methods=["GET", "POST"])
@login_required
def blog_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = dm.generate_slug(title)
        slug = dm.ensure_unique_slug(Config.BLOG_DIR, slug)
        tags = [t.strip() for t in request.form.getlist("tags") if t.strip()]
        data = {
            "slug": slug,
            "title": title,
            "author": request.form.get("author", "Calvin Berry").strip(),
            "date": request.form.get("date", _today()),
            "category": request.form.get("category", "").strip(),
            "featured_image": request.form.get("featured_image", "").strip(),
            "excerpt": request.form.get("excerpt", "").strip(),
            "content": request.form.get("content", ""),
            "tags": tags,
            "featured": "featured" in request.form,
            "youtube_url": request.form.get("youtube_url", "").strip(),
        }
        dm.save_item(Config.BLOG_DIR, slug, data)
        flash("Blog post created!", "success")
        return redirect(url_for("blog_list"))
    return render_template("admin/blog_form.html", item=None, today=_today())


@app.route("/admin/blog/<slug>/edit", methods=["GET", "POST"])
@login_required
def blog_edit(slug):
    item = dm.get_item(Config.BLOG_DIR, slug)
    if not item:
        flash("Blog post not found.", "error")
        return redirect(url_for("blog_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        new_slug = dm.generate_slug(title)
        new_slug = dm.ensure_unique_slug(Config.BLOG_DIR, new_slug, exclude=slug)
        tags = [t.strip() for t in request.form.getlist("tags") if t.strip()]
        data = {
            "slug": new_slug,
            "title": title,
            "author": request.form.get("author", "Calvin Berry").strip(),
            "date": request.form.get("date", _today()),
            "category": request.form.get("category", "").strip(),
            "featured_image": request.form.get("featured_image", "").strip(),
            "excerpt": request.form.get("excerpt", "").strip(),
            "content": request.form.get("content", ""),
            "tags": tags,
            "featured": "featured" in request.form,
            "youtube_url": request.form.get("youtube_url", "").strip(),
        }
        if new_slug != slug:
            dm.delete_item(Config.BLOG_DIR, slug)
        dm.save_item(Config.BLOG_DIR, new_slug, data)
        flash("Blog post updated!", "success")
        return redirect(url_for("blog_list"))
    return render_template("admin/blog_form.html", item=item, today=_today())


@app.route("/admin/blog/<slug>/delete", methods=["POST"])
@login_required
def blog_delete(slug):
    if dm.delete_item(Config.BLOG_DIR, slug):
        flash("Blog post deleted.", "success")
    else:
        flash("Blog post not found.", "error")
    return redirect(url_for("blog_list"))


# ---------------------------------------------------------------------------
# Routes — Contact Submissions (read-only)
# ---------------------------------------------------------------------------
@app.route("/admin/submissions/contact")
@login_required
def contact_list():
    items = dm.list_items(Config.CONTACT_DIR)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return render_template("admin/submissions_list.html", items=items,
                           kind="contact", title="Contact Messages")


@app.route("/admin/submissions/contact/<slug>")
@login_required
def contact_detail(slug):
    item = dm.get_item(Config.CONTACT_DIR, slug)
    if not item:
        flash("Submission not found.", "error")
        return redirect(url_for("contact_list"))
    dm.mark_read(Config.CONTACT_DIR, slug)
    return render_template("admin/submission_detail.html", item=item,
                           kind="contact", title="Contact Message")


@app.route("/admin/submissions/contact/<slug>/delete", methods=["POST"])
@login_required
def contact_delete(slug):
    if dm.delete_item(Config.CONTACT_DIR, slug):
        flash("Contact message deleted.", "success")
    else:
        flash("Submission not found.", "error")
    return redirect(url_for("contact_list"))


# ---------------------------------------------------------------------------
# Routes — Quote Submissions (read-only)
# ---------------------------------------------------------------------------
@app.route("/admin/submissions/quotes")
@login_required
def quotes_list():
    items = dm.list_items(Config.QUOTES_DIR)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return render_template("admin/submissions_list.html", items=items,
                           kind="quotes", title="Quote Requests")


@app.route("/admin/submissions/quotes/<slug>")
@login_required
def quotes_detail(slug):
    item = dm.get_item(Config.QUOTES_DIR, slug)
    if not item:
        flash("Submission not found.", "error")
        return redirect(url_for("quotes_list"))
    dm.mark_read(Config.QUOTES_DIR, slug)
    return render_template("admin/submission_detail.html", item=item,
                           kind="quotes", title="Quote Request")


@app.route("/admin/submissions/quotes/<slug>/delete", methods=["POST"])
@login_required
def quotes_delete(slug):
    if dm.delete_item(Config.QUOTES_DIR, slug):
        flash("Quote request deleted.", "success")
    else:
        flash("Submission not found.", "error")
    return redirect(url_for("quotes_list"))


# ---------------------------------------------------------------------------
# Routes — File Upload
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@app.route("/admin/upload", methods=["POST"])
@csrf.exempt
@login_required
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No file selected"}), 400

    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type .{ext} not allowed. Use: jpg, png, gif, webp"}), 400

    # Check size by reading into memory
    data = f.read()
    if len(data) > MAX_UPLOAD_SIZE:
        return jsonify({"error": "File too large. Max 10 MB."}), 400

    # Generate unique filename
    name = os.path.splitext(f.filename)[0]
    safe_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "image"
    timestamp = int(time.time())
    filename = f"{timestamp}-{safe_name}.{ext}"

    upload_dir = os.path.join(Config.STATIC_DIR, "img", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as fh:
        fh.write(data)

    return jsonify({"path": f"/static/img/uploads/{filename}"})


# ---------------------------------------------------------------------------
# Routes — Settings
# ---------------------------------------------------------------------------
@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    if request.method == "POST":
        service_areas = [a.strip() for a in request.form.getlist("service_areas") if a.strip()]
        data = {
            "business_name": request.form.get("business_name", "").strip(),
            "tagline": request.form.get("tagline", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "email": request.form.get("email", "").strip(),
            "address": {
                "street": request.form.get("address_street", "").strip(),
                "city": request.form.get("address_city", "").strip(),
                "state": request.form.get("address_state", "").strip(),
                "zip": request.form.get("address_zip", "").strip(),
            },
            "service_areas": service_areas,
            "years_experience": int(request.form.get("years_experience", 0) or 0),
            "license_number": request.form.get("license_number", "").strip(),
            "social": {
                "facebook": request.form.get("social_facebook", "").strip(),
                "instagram": request.form.get("social_instagram", "").strip(),
                "google_business": request.form.get("social_google_business", "").strip(),
            },
            "seo": {
                "title": request.form.get("seo_title", "").strip(),
                "description": request.form.get("seo_description", "").strip(),
                "og_image": request.form.get("seo_og_image", "").strip(),
            },
            "colors": {
                "primary": request.form.get("color_primary", "#1B3A5C").strip(),
                "secondary": request.form.get("color_secondary", "#C8963E").strip(),
                "accent": request.form.get("color_accent", "#D4A94F").strip(),
            },
            "smtp": {
                "host": request.form.get("smtp_host", "").strip(),
                "port": int(request.form.get("smtp_port", 587) or 587),
                "user": request.form.get("smtp_user", "").strip(),
                "password": request.form.get("smtp_password", "").strip(),
            },
            "notification_email": request.form.get("notification_email", "").strip(),
        }
        with open(Config.SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        flash("Settings saved!", "success")
        return redirect(url_for("admin_settings"))

    # GET — load current settings
    settings = {}
    if os.path.isfile(Config.SETTINGS_FILE):
        with open(Config.SETTINGS_FILE, "r", encoding="utf-8") as fh:
            settings = json.load(fh)
    return render_template("admin/settings_form.html", settings=settings)


# ---------------------------------------------------------------------------
# Routes — About Page
# ---------------------------------------------------------------------------
@app.route("/admin/about", methods=["GET", "POST"])
@login_required
def admin_about():
    if request.method == "POST":
        # Core values array
        cv_titles = request.form.getlist("cv_title")
        cv_descriptions = request.form.getlist("cv_description")
        cv_icons = request.form.getlist("cv_icon")
        core_values = []
        for title, desc, icon in zip(cv_titles, cv_descriptions, cv_icons):
            title, desc, icon = title.strip(), desc.strip(), icon.strip()
            if title or desc:
                core_values.append({"title": title, "description": desc, "icon": icon})

        # Milestones array
        ms_years = request.form.getlist("ms_year")
        ms_titles = request.form.getlist("ms_title")
        ms_descriptions = request.form.getlist("ms_description")
        milestones = []
        for year, title, desc in zip(ms_years, ms_titles, ms_descriptions):
            year, title, desc = year.strip(), title.strip(), desc.strip()
            if year or title:
                milestones.append({"year": year, "title": title, "description": desc})

        data = {
            "headline": request.form.get("headline", "").strip(),
            "story": request.form.get("story", "").strip(),
            "story_image": request.form.get("story_image", "").strip(),
            "core_values": core_values,
            "milestones": milestones,
        }
        with open(Config.ABOUT_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        flash("About page saved!", "success")
        return redirect(url_for("admin_about"))

    # GET — load current about data
    about = {}
    if os.path.isfile(Config.ABOUT_FILE):
        with open(Config.ABOUT_FILE, "r", encoding="utf-8") as fh:
            about = json.load(fh)
    return render_template("admin/about_form.html", about=about)


# ---------------------------------------------------------------------------
# Routes — Public Form Submissions (no login required)
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route("/submit/contact", methods=["POST"])
@csrf.exempt
def submit_contact():
    ip = request.remote_addr
    if _is_rate_limited(ip, "submit", SUBMISSION_RATE_LIMIT_MAX, SUBMISSION_RATE_LIMIT_WINDOW):
        return jsonify({"error": "Too many submissions. Please try again later."}), 429

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request."}), 400

    # Honeypot check — bots fill this, humans never see it
    if (data.get("website") or "").strip():
        return jsonify({"ok": True})

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    message = (data.get("message") or "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    elif not _EMAIL_RE.match(email):
        errors.append("Invalid email address.")
    if not message:
        errors.append("Message is required.")
    if errors:
        return jsonify({"error": " ".join(errors)}), 400

    _record_attempt(ip, "submit")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = dm.generate_slug(name) + "-" + str(int(time.time()))
    slug = dm.ensure_unique_slug(Config.CONTACT_DIR, slug)

    item = {
        "slug": slug,
        "name": name,
        "email": email,
        "phone": phone,
        "message": message,
        "date": timestamp,
        "read": False,
    }
    dm.save_item(Config.CONTACT_DIR, slug, item)

    # Send email notification
    email_body = (
        f"New contact form submission:\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone or 'Not provided'}\n\n"
        f"Message:\n{message}\n"
    )
    send_notification_email(
        f"New Contact Message — {name}",
        email_body,
        reply_to=email,
    )

    return jsonify({"ok": True})


@app.route("/submit/quote", methods=["POST"])
@csrf.exempt
def submit_quote():
    ip = request.remote_addr
    if _is_rate_limited(ip, "submit", SUBMISSION_RATE_LIMIT_MAX, SUBMISSION_RATE_LIMIT_WINDOW):
        return jsonify({"error": "Too many submissions. Please try again later."}), 429

    # Support both JSON and multipart (when photos are attached)
    is_multipart = request.content_type and "multipart/form-data" in request.content_type
    if is_multipart:
        data = request.form
    else:
        data = request.get_json(silent=True) or {}

    # Honeypot check — bots fill this, humans never see it
    if (data.get("website") or "").strip():
        return jsonify({"ok": True})

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    city = (data.get("city") or "").strip()
    service = (data.get("service") or "").strip()
    description = (data.get("description") or "").strip()
    timeline = (data.get("timeline") or "").strip()
    budget = (data.get("budget") or "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    elif not _EMAIL_RE.match(email):
        errors.append("Invalid email address.")
    if not phone:
        errors.append("Phone is required.")
    if not service:
        errors.append("Service is required.")
    if not description:
        errors.append("Description is required.")
    if errors:
        return jsonify({"error": " ".join(errors)}), 400

    _record_attempt(ip, "submit")

    # Process uploaded photos (if multipart)
    photo_paths = []
    if is_multipart:
        photos = request.files.getlist("photos")
        upload_dir = os.path.join(Config.STATIC_DIR, "img", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        for i, photo in enumerate(photos[:5]):  # max 5 photos
            if not photo.filename:
                continue
            ext = photo.filename.rsplit(".", 1)[-1].lower() if "." in photo.filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                continue
            file_data = photo.read()
            if len(file_data) > MAX_UPLOAD_SIZE:
                continue
            safe_name = re.sub(r"[^a-z0-9]+", "-",
                               os.path.splitext(photo.filename)[0].lower()).strip("-") or "photo"
            timestamp_val = int(time.time())
            filename = f"{timestamp_val}-{safe_name}-{i}.{ext}"
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as fh:
                fh.write(file_data)
            photo_paths.append(f"/static/img/uploads/{filename}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = dm.generate_slug(name) + "-" + str(int(time.time()))
    slug = dm.ensure_unique_slug(Config.QUOTES_DIR, slug)

    item = {
        "slug": slug,
        "name": name,
        "email": email,
        "phone": phone,
        "city": city,
        "service": service,
        "description": description,
        "timeline": timeline,
        "budget": budget,
        "photos": photo_paths,
        "date": timestamp,
        "read": False,
    }
    dm.save_item(Config.QUOTES_DIR, slug, item)

    # Send email notification
    email_body = (
        f"New quote request:\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone}\n"
        f"City: {city or 'Not provided'}\n"
        f"Service: {service}\n"
        f"Timeline: {timeline or 'Not specified'}\n"
        f"Budget: {budget or 'Not specified'}\n\n"
        f"Description:\n{description}\n"
    )
    if photo_paths:
        email_body += "\nPhotos:\n" + "\n".join(photo_paths) + "\n"
    send_notification_email(
        f"New Quote Request — {service}",
        email_body,
        reply_to=email,
    )

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Routes — Serve generated static site from output/
# ---------------------------------------------------------------------------
@app.route("/<path:filename>")
def serve_site(filename="index.html"):
    filepath = os.path.join(Config.OUTPUT_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(Config.OUTPUT_DIR, filename)
    return "Not found", 404


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
