"""
BOS – Django Settings (Infrastructure Only)
============================================
Django serves as the framework container for BOS.
BOS architecture is the authority — Django does not dictate structure.

INSTALLED_APPS will grow as BOS modules are built, starting with
core.event_store as the first module.

Environment variables required for production:
  BOS_SECRET_KEY       — Django secret key (required in production)
  BOS_DEBUG            — "true"/"false" (default: "true" for dev)
  BOS_ALLOWED_HOSTS    — comma-separated hostnames (default: empty)
  BOS_DB_NAME          — PostgreSQL database name
  BOS_DB_USER          — PostgreSQL username
  BOS_DB_PASSWORD      — PostgreSQL password
  BOS_DB_HOST          — PostgreSQL host (default: localhost)
  BOS_DB_PORT          — PostgreSQL port (default: 5432)
"""

import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────
# BASE_DIR = bos/ (project root where manage.py lives)
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────
SECRET_KEY = os.environ.get("BOS_SECRET_KEY", "bos-dev-key-replace-before-deployment")

DEBUG = os.environ.get("BOS_DEBUG", "true").lower() == "true"

_allowed_hosts = os.environ.get("BOS_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(",") if h.strip()]

# ── Installed Apps ────────────────────────────────────────────
# Django infrastructure only. BOS modules are added as they are built.
# core.event_store will be the FIRST BOS app registered here.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # ── BOS Modules (added in build order) ────────────────
    "core.event_store",
    "core.auth.apps.CoreAuthConfig",
    "core.identity_store.apps.CoreIdentityStoreConfig",
    "core.permissions_store.apps.CorePermissionsStoreConfig",
    "core.replay",
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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get("BOS_DB_NAME", "bos_project"),
        'USER': os.environ.get("BOS_DB_USER", "postgres"),
        'PASSWORD': os.environ.get("BOS_DB_PASSWORD", ""),
        'HOST': os.environ.get("BOS_DB_HOST", "localhost"),
        'PORT': os.environ.get("BOS_DB_PORT", "5432"),
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
