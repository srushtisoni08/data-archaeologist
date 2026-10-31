from pathlib import Path

STORAGE = Path(__file__).resolve().parent.parent / "storage"
ORIGINALS = STORAGE / "originals"   # immutable uploads
PROFILES = STORAGE / "profiles"     # JSON profiles
for p in (ORIGINALS, PROFILES):
    p.mkdir(parents=True, exist_ok=True)