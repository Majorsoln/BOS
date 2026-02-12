"""
BOS – Django Settings (Infrastructure Only)
============================================
Django serves as the framework container for BOS.
BOS architecture is the authority — Django does not dictate structure.

INSTALLED_APPS will grow as BOS modules are built, starting with
core.event_store as the first module.
"""

import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────
# BASE_DIR = bos/ (project root where manage.py lives)
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────
# TODO: Move to environment variable before any deployment
SECRET_KEY = "bos-dev-key-replace-before-deployment"

DEBUG = True

ALLOWED_HOSTS = []

# ── Installed Apps ────────────────────────────────────────────
# Django infrastructure only. BOS modules are added as they are built.
# core.event_store will be the FIRST BOS app registered here.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # ── BOS Modules (added in build order) ────────────────
    "core.event_store",
    "core.bootstrap",
]

# ── Middleware ────────────────────────────────────────────────
# Minimal middleware. BOS-specific middleware added per phase.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# ── URL & WSGI ────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ── Database ──────────────────────────────────────────────────
# SQLite for development. Production DB configured separately.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Internationalization ──────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Default Primary Key ──────────────────────────────────────
# BOS uses UUIDs explicitly. This is a Django fallback only.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
