"""Paths and settings; the database values come from .env in the project root."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB = {
    "host": "127.0.0.1",
    "port": os.environ["POSTGRES_PORT"],
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
}
SCHEMA_FILE = ROOT / "schema.sql"
REPORT_DIR = ROOT / "report"
THUMBS_DIR = REPORT_DIR / "thumbs"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
WORKERS = 8             # files fingerprinted at the same time
THUMB_SIZE = 320        # longest side of a preview picture in the report, pixels
