"""JSON data I/O helpers for BT Construction admin."""

import json
import os
import tempfile

from slugify import slugify


def list_items(directory):
    """Load all JSON files from *directory*, return list sorted by slug."""
    if not os.path.isdir(directory):
        return []
    items = []
    for fname in os.listdir(directory):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(directory, fname)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                items.append(json.load(fh))
        except (json.JSONDecodeError, OSError):
            continue
    items.sort(key=lambda x: x.get("slug", ""))
    return items


def get_item(directory, slug):
    """Load a single JSON file by slug.  Returns dict or None."""
    path = os.path.join(directory, f"{slug}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_item(directory, slug, data):
    """Write *data* as JSON to <directory>/<slug>.json atomically."""
    os.makedirs(directory, exist_ok=True)
    target = os.path.join(directory, f"{slug}.json")
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        # On Windows, target must not exist for os.rename
        if os.path.exists(target):
            os.replace(tmp, target)
        else:
            os.rename(tmp, target)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def delete_item(directory, slug):
    """Delete the JSON file for *slug*.  Returns True if deleted."""
    path = os.path.join(directory, f"{slug}.json")
    if os.path.isfile(path):
        os.unlink(path)
        return True
    return False


def generate_slug(text):
    """Create a URL-safe slug from *text*."""
    return slugify(text, max_length=80)


def ensure_unique_slug(directory, slug, exclude=None):
    """Return *slug* if unique in *directory*, else append -2, -3, etc.

    *exclude* is an existing slug to ignore (for edits of the same item).
    """
    if not os.path.isdir(directory):
        return slug
    candidate = slug
    counter = 2
    while True:
        path = os.path.join(directory, f"{candidate}.json")
        if not os.path.isfile(path) or candidate == exclude:
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


def count_items(directory):
    """Count JSON files in *directory*."""
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory) if f.endswith(".json")])


def count_unread(directory):
    """Count JSON files where ``read`` is not ``true``."""
    if not os.path.isdir(directory):
        return 0
    count = 0
    for fname in os.listdir(directory):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(directory, fname), "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if not data.get("read", False):
                    count += 1
        except (json.JSONDecodeError, OSError):
            count += 1
    return count


def mark_read(directory, slug):
    """Set ``read=true`` on the item and save it back."""
    item = get_item(directory, slug)
    if item is None:
        return False
    item["read"] = True
    save_item(directory, slug, item)
    return True
