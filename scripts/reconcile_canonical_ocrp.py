"""Reconcile reviewed OCRP corrections into the historical canonical CSV.

Only exact English + existing Korean matches from OCRP's audited 55-row review
are eligible. Unicode/legacy encodings are checked together. A failed guard
leaves the canonical file untouched. This does NOT make all canonical entries
independently reviewed for reuse in third-party mods.

Usage:
  python scripts/reconcile_canonical_ocrp.py --check
  python scripts/reconcile_canonical_ocrp.py --apply
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from oblivion_korean_codec import decode_legacy, encode_legacy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "mods/ocrp/legacy_retranslation_20261103.json"
DEFAULT_CANONICAL = ROOT / "canonical_translation_v2.csv"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reviewed_rules(path):
    data = json.loads(Path(path).read_text("utf-8"))
    entries = list(data["corrections"]) + list(data.get("additional_semantic_fixes", []))
    if len(entries) != 55:
        raise ValueError("Expected exactly 55 OCRP reviewed edits; review a new audit first")
    rules = {}
    for item in entries:
        old = item.get("previous_korean", item.get("old"))
        new = item.get("reviewed_korean", item.get("new"))
        english = item["english"]
        if not english or not old or not new or old == new:
            raise ValueError("Malformed source-anchored OCRP review")
        key = (english, old)
        if key in rules and rules[key] != new:
            raise ValueError("Conflicting source-anchored OCRP translations")
        rules[key] = new
    return rules


def decode_target(hex_value, mode):
    raw = bytes.fromhex(hex_value)
    if not raw.endswith(b"\0") or b"\0" in raw[:-1]:
        raise ValueError("Expected exactly one terminal NUL")
    return raw[:-1].decode("utf-8") if mode == "utf8" else decode_legacy(raw[:-1])


def encode_target(text, mode):
    if "\0" in text:
        raise ValueError("NUL in approved text")
    return ((text.encode("utf-8") if mode == "utf8" else encode_legacy(text)) + b"\0").hex()


def reconcile(path, audit, apply=False):
    path = Path(path)
    if path.name != "canonical_translation_v2.csv":
        raise ValueError("Only the explicitly named legacy canonical CSV is supported")
    rules = reviewed_rules(audit)
    original_sha = sha256(path)
    with path.open("rb") as f:
        head = f.read(131072)
    newline = "\r\n" if b"\r\n" in head else "\n"
    required = {"record_type", "field", "raw_formid", "old_english", "new_korean",
                "obcjk_utf8_hex", "new_bytes_hex"}
    count = 0
    changed = []
    skipped = Counter()
    fd, temp_name = tempfile.mkstemp(prefix="canonical_review_", suffix=".csv", dir=str(path.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        csv.field_size_limit(100_000_000)
        with path.open("r", encoding="utf-8-sig", newline="") as input_file, \
                temp.open("w", encoding="utf-8", newline="") as output_file:
            reader = csv.DictReader(input_file)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError(f"Canonical CSV schema drift: {required-set(reader.fieldnames or [])}")
            writer = csv.DictWriter(output_file, fieldnames=reader.fieldnames, lineterminator=newline)
            writer.writeheader()
            for row in reader:
                count += 1
                old = row["new_korean"]
                replacement = rules.get((row["old_english"], old))
                if replacement is not None:
                    if row["record_type"] not in {"INFO", "QUST"} or row["field"] not in {"NAM1", "CNAM"}:
                        skipped["wrong_record_field"] += 1
                    else:
                        valid = True
                        for column, mode in (("obcjk_utf8_hex", "utf8"), ("new_bytes_hex", "legacy")):
                            if row[column]:
                                try:
                                    decoded = decode_target(row[column], mode)
                                except (ValueError, UnicodeError):
                                    valid = False
                                    skipped["bad_encoding"] += 1
                                    break
                                if decoded not in (old, replacement):
                                    valid = False
                                    skipped["encoded_content_disagrees"] += 1
                                    break
                        marks = re.compile(r"<[^>]*>|%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+")
                        if marks.findall(old) != marks.findall(replacement) or \
                           [x for x in old if x in "\r\n"] != [x for x in replacement if x in "\r\n"]:
                            valid = False
                            skipped["markup_or_newline_drift"] += 1
                        if valid:
                            try:
                                utf8_hex = encode_target(replacement, "utf8")
                                legacy_hex = encode_target(replacement, "legacy")
                            except (ValueError, UnicodeError):
                                skipped["unencodable_legacy"] += 1
                            else:
                                row["new_korean"] = replacement
                                row["obcjk_utf8_hex"] = utf8_hex
                                row["new_bytes_hex"] = legacy_hex
                                changed.append({"kind": row["record_type"], "formid": row["raw_formid"],
                                                "field": row["field"],
                                                "english_sha256": hashlib.sha256(row["old_english"].encode()).hexdigest(),
                                                "old_korean_sha256": hashlib.sha256(old.encode()).hexdigest()})
                writer.writerow(row)
        if sha256(path) != original_sha:
            raise RuntimeError("The canonical input changed during reconciliation")
        if apply and skipped:
            raise ValueError(f"Fail closed: {dict(skipped)}")
        if apply and changed:
            os.replace(temp, path)
        return {"canonical": path.name, "audit": Path(audit).name,
                "old_sha256": original_sha,
                "candidate_sha256": sha256(path) if apply else sha256(temp),
                "applied": bool(apply), "rows": count, "corrected": len(changed),
                "skipped": dict(skipped), "changed_record_identities": changed}
    finally:
        if temp.exists():
            temp.unlink()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    p.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    p.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = reconcile(args.canonical, args.audit, apply=args.apply)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "changed_record_identities"}, ensure_ascii=False))
    if result["skipped"]:
        raise SystemExit("Cannot safely apply every matching row; inspect the report")


if __name__ == "__main__":
    main()
