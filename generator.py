"""Static site generator for BT Construction LLC."""

import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime

import markdown as md
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from config import Config


def load_json(filepath):
    """Load a single JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_dir(directory):
    """Load all JSON files from a directory, returning a list of dicts."""
    items = []
    if not os.path.isdir(directory):
        return items
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".json"):
            items.append(load_json(os.path.join(directory, filename)))
    return items


def markdown_filter(text):
    """Convert markdown text to HTML."""
    return Markup(md.markdown(text, extensions=["extra", "smarty"]))


def render_page(env, template_name, context, output_dir, filename):
    """Render a single template to an HTML file."""
    template = env.get_template(template_name)
    html = template.render(**context)
    filepath = os.path.join(output_dir, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Built: {filename}")


def build_detail_pages(env, template_name, items, subdir, context):
    """Generate detail pages for a list of items."""
    output_dir = context["_output_dir"]
    for item in items:
        page_context = {**context, "item": item}
        filename = os.path.join(subdir, f"{item['slug']}.html")
        render_page(env, template_name, page_context, output_dir, filename)


def link_prev_next(items):
    """Add prev/next references to a sorted list of items."""
    for i, item in enumerate(items):
        item["prev"] = items[i - 1] if i > 0 else None
        item["next"] = items[i + 1] if i < len(items) - 1 else None
    return items


def build():
    """Build the static site."""
    start_time = time.time()
    print("Building BT Construction site...")

    # Load all data
    settings = load_json(Config.SETTINGS_FILE)
    all_services = load_json_dir(Config.SERVICES_DIR)
    all_portfolio = load_json_dir(Config.PORTFOLIO_DIR)
    all_testimonials = load_json_dir(Config.TESTIMONIALS_DIR)
    all_blog_posts = load_json_dir(Config.BLOG_DIR)

    # Load about data
    about_file = os.path.join(Config.DATA_DIR, "about.json")
    about = load_json(about_file) if os.path.exists(about_file) else {}

    # Featured subsets for homepage
    featured_services = [s for s in all_services if s.get("featured", False)]
    featured_portfolio = [p for p in all_portfolio if p.get("featured", False)]
    featured_testimonials = [t for t in all_testimonials if t.get("featured", False)]

    # Sort blog posts by date descending, link prev/next
    all_blog_posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    link_prev_next(all_blog_posts)

    # Extract unique portfolio categories for filter buttons
    portfolio_categories = sorted(set(
        p["category"] for p in all_portfolio if "category" in p
    ))

    # Set up Jinja2
    env = Environment(
        loader=FileSystemLoader(Config.TEMPLATES_DIR),
        autoescape=True,
    )
    env.filters["markdown"] = markdown_filter

    # Build to a temp directory first (atomic deploy)
    temp_dir = tempfile.mkdtemp(prefix="bt_build_")

    try:
        # Common template context
        context = {
            "settings": settings,
            "current_year": datetime.now().year,
            "all_services": all_services,
            "all_portfolio": all_portfolio,
            "all_testimonials": all_testimonials,
            "all_blog_posts": all_blog_posts,
            "portfolio_categories": portfolio_categories,
            "about": about,
            "_output_dir": temp_dir,
        }

        # Homepage
        home_context = {
            **context,
            "services": featured_services,
            "portfolio": featured_portfolio,
            "testimonials": featured_testimonials,
        }
        render_page(env, "home.html", home_context, temp_dir, "index.html")

        # Services index
        render_page(env, "services.html", {**context, "services": all_services}, temp_dir, "services.html")

        # Portfolio index
        render_page(env, "portfolio.html", {**context, "portfolio": all_portfolio}, temp_dir, "portfolio.html")

        # About page
        render_page(env, "about.html", {**context, "testimonials": featured_testimonials}, temp_dir, "about.html")

        # Blog index
        render_page(env, "blog.html", context, temp_dir, "blog.html")

        # Contact page
        render_page(env, "contact.html", context, temp_dir, "contact.html")

        # Quote page
        render_page(env, "quote.html", {**context, "services": all_services}, temp_dir, "quote.html")

        # Detail pages
        build_detail_pages(env, "service_detail.html", all_services, "services", {**context, "portfolio": all_portfolio})
        build_detail_pages(env, "project_detail.html", all_portfolio, "portfolio", {**context, "portfolio": all_portfolio})
        build_detail_pages(env, "blog_post.html", all_blog_posts, "blog", context)

        # Copy static directory
        static_dest = os.path.join(temp_dir, "static")
        shutil.copytree(Config.STATIC_DIR, static_dest)
        print("  Copied: static/")

        # Atomic deploy: remove old output, move temp to output
        if os.path.exists(Config.OUTPUT_DIR):
            shutil.rmtree(Config.OUTPUT_DIR)
        shutil.move(temp_dir, Config.OUTPUT_DIR)

    except Exception:
        # Clean up temp dir on failure
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise

    elapsed = time.time() - start_time
    print(f"Build complete in {elapsed:.2f}s -> {Config.OUTPUT_DIR}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build()
    else:
        print("Usage: python generator.py build")
