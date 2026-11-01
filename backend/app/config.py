from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

STORAGE = Path(__file__).resolve().parent.parent / "storage"
ORIGINALS = STORAGE / "originals"   # immutable uploads
PROFILES = STORAGE / "profiles"     # JSON profiles
for p in (ORIGINALS, PROFILES):
    p.mkdir(parents=True, exist_ok=True)