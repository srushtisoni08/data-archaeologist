import json
from pathlib import Path
import pandas as pd
from .file_detector import detect_format, detect_encoding, detect_delimiter


def load_dataframe(path: Path) -> tuple[pd.DataFrame, dict]:
    """Returns (dataframe, meta). Never modifies the original file."""
    fmt = detect_format(path)
    meta = {"format": fmt}
    if fmt == "csv":
        enc = detect_encoding(path)
        delim = detect_delimiter(path, enc)
        meta.update(encoding=enc, delimiter=delim)
        df = pd.read_csv(path, encoding=enc, sep=delim, low_memory=False,
                         encoding_errors="replace", on_bad_lines="warn")
    elif fmt == "excel":
        xl = pd.ExcelFile(path)
        meta["sheets"] = xl.sheet_names
        df = xl.parse(xl.sheet_names[0])
    elif fmt == "jsonl":
        df = pd.read_json(path, lines=True)
    elif fmt == "json":
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(obj, dict):
            lists = [v for v in obj.values() if isinstance(v, list)]
            obj = lists[0] if lists else [obj]
        df = pd.json_normalize(obj)
    else:
        df = pd.read_parquet(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df, meta