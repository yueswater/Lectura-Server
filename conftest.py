import os
import sys
from pathlib import Path

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent

# Add the 'apps' directory to the Python path
sys.path.insert(0, str(BASE_DIR / "apps"))

# Set the default Django settings module for the 'pytest' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
