"""Configuration for BT Construction static site generator."""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Project configuration paths and settings."""

    # Directories
    DATA_DIR = os.path.join(BASE_DIR, "data")
    TEMPLATES_DIR = os.path.join(BASE_DIR, "templates", "site")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")

    # Data subdirectories
    SERVICES_DIR = os.path.join(DATA_DIR, "services")
    PORTFOLIO_DIR = os.path.join(DATA_DIR, "portfolio")
    TESTIMONIALS_DIR = os.path.join(DATA_DIR, "testimonials")
    BLOG_DIR = os.path.join(DATA_DIR, "blog")
    SUBMISSIONS_DIR = os.path.join(DATA_DIR, "submissions")
    SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
    ABOUT_FILE = os.path.join(DATA_DIR, "about.json")

    # Admin
    ADMIN_CONFIG_FILE = os.path.join(BASE_DIR, "admin_config.py")
    REBUILD_TIMESTAMP_FILE = os.path.join(DATA_DIR, "last_rebuild.txt")
    CONTACT_DIR = os.path.join(DATA_DIR, "submissions", "contact")
    QUOTES_DIR = os.path.join(DATA_DIR, "submissions", "quotes")

    # Site defaults
    SITE_NAME = "BT Construction LLC"
    SITE_TAGLINE = "Quality Craftsmanship, Lasting Results"
