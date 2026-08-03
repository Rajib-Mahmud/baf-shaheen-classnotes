import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///classnotes.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads live OUTSIDE any web-served static folder; images are served
    # only through the scope-checked /image/<id> route.
    UPLOAD_FOLDER = str(BASE_DIR / os.environ.get("UPLOAD_FOLDER", "uploads"))
    MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB per image, enforced per file
    MAX_IMAGES_PER_NOTE = 10
    # Request cap: 10 images x 8 MB + form overhead.
    MAX_CONTENT_LENGTH = MAX_IMAGES_PER_NOTE * MAX_IMAGE_BYTES + 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    THUMBNAIL_MAX_SIZE = 400  # px, longest side

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    WTF_CSRF_TIME_LIMIT = None  # CSRF token valid for the whole session
