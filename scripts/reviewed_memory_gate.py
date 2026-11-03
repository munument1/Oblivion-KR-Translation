"""Only explicitly human-reviewed, source-identified translations may be reused.

canonical_translation_v2.csv is a historical build input, NOT a verified
third-party mod translation memory. A matching English sentence alone is
insufficient for safe reuse.
"""
from pathlib import Path
import csv
import re

HISTORICAL = {
    "canonical_translation_v2.csv",
    "applied_translations_v2.csv",
    "patch_translation_memory.csv",
    "canonical_unofficial_translation_v2.csv",
}
REQUIRED = {
    "effective_source", "record_type", "raw_formid", "field",
    "old_english", "korean", "review_status", "review_source",
}

def load_reviewed_memory(path):
    path = Path(path)
    if path.name.lower() in HISTORICAL:
        raise ValueError(f"Historical/unsafe translation memory: {path.name}")
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("Missing explicit review evidence or source identity")
        for line, row in enumerate(reader, 2):
            if row["review_status"] != "reviewed" or not row["review_source"].strip():
                raise ValueError(f"Unreviewed candidate on line {line}")
            if not row["old_english"] or not row["korean"] or "\ufffd" in row["korean"]:
                raise ValueError(f"Invalid Korean on line {line}")
            if re.search(r"\([A-Za-z][^)]+\)", row["korean"]):
                raise ValueError(f"Old Korean(English) bilingual gloss on line {line}")
            try:
                fid = int(row["raw_formid"], 16)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid FormID on line {line}") from exc
            if not 0 <= fid < 2 ** 32:
                raise ValueError(f"Invalid FormID on line {line}")
            key = (row["effective_source"], row["record_type"], fid,
                   row["field"], row["old_english"])
            if key in result and result[key] != row["korean"]:
                raise ValueError(f"Conflicting reviewed translations on line {line}")
            result[key] = row["korean"]
    return result
