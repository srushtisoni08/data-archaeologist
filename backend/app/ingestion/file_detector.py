import csv
from pathlib import Path
from charset_normalizer import from_bytes

FORMATS = {
    ".csv": "csv", ".tsv": "csv", ".txt": "csv",
    ".xlsx": "excel", ".xls": "excel", ".xlsm": "excel",
    ".json": "json", ".jsonl": "jsonl", ".ndjson": "jsonl",
    ".parquet": "parquet",
}


def detect_format(path: Path) -> str:
    fmt = FORMATS.get(path.suffix.lower())
    if not fmt:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    return fmt


def detect_encoding(path: Path) -> str:
    raw = path.read_bytes()[:200_000]
    best = from_bytes(raw).best()
    return best.encoding if best else "utf-8"


def detect_delimiter(path: Path, encoding: str) -> str:
    with open(path, encoding=encoding, errors="replace") as f:
        sample = f.read(20_000)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","