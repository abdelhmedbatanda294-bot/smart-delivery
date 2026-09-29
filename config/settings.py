"""
Django settings for the Smart Delivery & Logistics Management System.
Secrets and database credentials come from environment variables.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# =========================
# Base Directory
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# =========================
# Security
# =========================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-local-env",
)

DEBUG = os.getenv(
    "DEBUG",
    "True",
).lower() in {"1", "true", "yes"}


ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


# =========================
# Applications
# =========================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "apps.authentication",
    "apps.core",
    "apps.delivery",
    "apps.ai_agent",
]


# =========================
# Middleware
# =========================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    # Language switching
    "django.middleware.locale.LocaleMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================
# URL Configuration
# =========================

ROOT_URLCONF = "config.urls"


# =========================
# Templates
# =========================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.ui_context",
            ],
        },
    },
]


# =========================
# WSGI
# =========================

WSGI_APPLICATION = "config.wsgi.application"


# =========================
# Authentication
# =========================

AUTH_USER_MODEL = "authentication.User"

LOGIN_URL = "authentication:login"

LOGIN_REDIRECT_URL = "dashboard"

LOGOUT_REDIRECT_URL = "authentication:login"


# =========================
# Database
# =========================

# PostgreSQL is the project database.
# Tests can use SQLite so they can run
# without a local PostgreSQL password.

TESTING = (
    "test" in sys.argv
    or os.getenv(
        "DJANGO_TEST",
        "",
    ).lower() in {"1", "true"}
)


DB_ENGINE = os.getenv(
    "DB_ENGINE",
    "postgresql",
).lower()


if TESTING or DB_ENGINE in {
    "sqlite",
    "django.db.backends.sqlite3",
}:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

else:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",

            "NAME": os.getenv(
                "DB_NAME",
                "smart_delivery_db",
            ),

            "USER": os.getenv(
                "DB_USER",
                "postgres",
            ),

            "PASSWORD": os.getenv(
                "DB_PASSWORD",
                "",
            ),

            "HOST": os.getenv(
                "DB_HOST",
                "localhost",
            ),

            "PORT": os.getenv(
                "DB_PORT",
                "5432",
            ),
        }
    }


# =========================
# Password Validation
# =========================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator",
    },

    {
        "NAME":
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator",
    },
]


# =========================
# Language & Internationalization
# =========================

LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
    ("ar", "العربية"),
]


LOCALE_PATHS = [
    BASE_DIR / "locale",
]


TIME_ZONE = os.getenv(
    "TIME_ZONE",
    "Africa/Cairo",
)


USE_I18N = True

USE_TZ = True


# =========================
# Static Files
# =========================

STATIC_URL = "static/"


STATICFILES_DIRS = [
    BASE_DIR / "static",
]


STATIC_ROOT = BASE_DIR / "staticfiles"


# =========================
# Default Primary Key
# =========================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================
# Email
# =========================

# Console backend is suitable for local development.
# Emails are printed in the terminal instead of being sent.

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


# =========================
# Gemini AI
# =========================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
)


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)


# =========================
# AI Mutating Tools
# =========================

# Mutating AI tools require an explicit
# confirm=true flag from the UI.

AI_MUTATING_TOOLS = {
    "assign_delivery",
    "reassign_delivery",
    "update_delivery_status",
}