import django
from pathlib import Path
from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "db/db.sqlite3"
print(f"Using database: {DATABASE_PATH}")
settings.configure(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATABASE_PATH,
        }
    },
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
    ],
)
django.setup()
