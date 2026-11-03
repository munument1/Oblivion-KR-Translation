"""Read-only, source-exact audit of historical canonical versus reviewed v2 sources.

All matching requires (plugin, record type, FormID, field, editor ID,
occurrence, exact English). No translation is applied by this script.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from oblivion_korean_codec import decode_legacy

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "canonical_translation_v2.csv"
REVIEWED = {
    "final_review": ROOT / "final_review_override.csv",
    "v2_reviewed": ROOT / "docs/v2_review/source_snapshot/V2_SOL_FINAL_OVERRIDE.csv",
}
FIELDS = ("effective_source", "record_type", "raw_formid", "field",
          "editor_id", "occurrence", "old_english")


def fingerprint(row):
    return (row["effective_source"], row["record_type"],
            f"{int(row['raw_formid'],16):08X}", row["field"],
            row.get("editor_id", ""), str(int(row.get("occurrence") or 0)),
            row["old_english"])


def abbreviation(key):
    return {"source": key[0], "record_type": key[1], "formid": key[2],
            "field": key[3], "editor_id": key[4], "occurrence": key[5],
            "english_sha256": hashlib.sha256(key[6].encode("utf-8")).hexdigest(),
            "english_excerpt": key[6][:180]}


def read_index(path):
    index, collisions = {}, []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(FIELDS + ("new_korean",)) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {missing}")
        seen = Counter()
        for row in reader:
            key = fingerprint(row)
            seen[key] += 1
            if key in index and index[key] != row["new_korean"]:
                if len(collisions) < 100:
                    collisions.append({"key": abbreviation(key), "old": index[key][:100],
                                       "new": row["new_korean"][:100]})
            else:
                index[key] = row["new_korean"]
        return index, {"rows": sum(seen.values()), "unique": len(seen),
                       "duplicate_identity_rows": sum(n-1 for n in seen.values()),
                       "conflicting_duplicate_samples": collisions}


def canonical_validation(path):
    seen = Counter()
    indexes = {}
    diagnostics = Counter()
    examples = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = set(FIELDS + ("new_korean","obcjk_unicode_text",
                                 "obcjk_utf8_hex","new_bytes_hex"))
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Canonical schema missing {required-set(reader.fieldnames or [])}")
        for row in reader:
            key = fingerprint(row)
            seen[key] += 1
            indexes[key] = row["new_korean"]
            ko = row["new_korean"]
            reasons = []
            if row["obcjk_unicode_text"] != ko:
                reasons.append("unicode_text_disagrees")
            try:
                utf = bytes.fromhex(row["obcjk_utf8_hex"])
                if not utf.endswith(b"\0") or b"\0" in utf[:-1]:
                    raise ValueError("Invalid NUL")
                decoded_utf = utf[:-1].decode("utf-8")
                if decoded_utf != ko:
                    reasons.append("utf8_hex_disagrees")
            except (ValueError, UnicodeError):
                reasons.append("invalid_utf8_hex")
            try:
                leg = bytes.fromhex(row["new_bytes_hex"])
                if not leg.endswith(b"\0") or b"\0" in leg[:-1]:
                    raise ValueError("Invalid NUL")
                decoded_legacy = decode_legacy(leg[:-1])
                if decoded_legacy != ko:
                    reasons.append("legacy_hex_disagrees")
            except (ValueError, UnicodeError):
                reasons.append("invalid_legacy_hex")
            if reasons:
                diagnostics["fields_with_any_disagreement"] += 1
                for reason in reasons:
                    diagnostics[reason] += 1
                    if len(examples[reason]) < 100:
                        examples[reason].append({
                            **abbreviation(key), "korean_excerpt": ko[:160],
                            "unicode_excerpt": row["obcjk_unicode_text"][:160],
                        })
    return indexes, {"rows": sum(seen.values()), "unique": len(seen),
                     "duplicate_identity_rows": sum(n-1 for n in seen.values()),
                     "encoding_diagnostics": dict(diagnostics),
                     "examples": dict(examples)}


def diff(source, destination, limit=120):
    matches, same, different, missing = 0, 0, 0, 0
    examples = []
    for key, target in source.items():
        if key not in destination:
            missing += 1
            continue
        matches += 1
        if destination[key] == target:
            same += 1
        else:
            different += 1
            if len(examples) < limit:
                examples.append({**abbreviation(key),
                                 "reviewed_korean": target[:280],
                                 "existing_korean": destination[key][:280]})
    return {"source_rows_unique": len(source), "exact_source_matches": matches,
            "same_translation": same, "different_translation": different,
            "no_exact_match": missing, "different_samples": examples}


def main():
    csv.field_size_limit(100_000_000)
    canonical, validation = canonical_validation(CANONICAL)
    sources = {}
    source_reports = {}
    for name, path in REVIEWED.items():
        sources[name], source_reports[name] = read_index(path)
    report = {"policy": "Read only. Never auto-apply draft or unmatched translations.",
              "identity": list(FIELDS), "canonical": validation,
              "source_statistics": source_reports,
              "reviewed_vs_canonical": {
                  k: diff(v,canonical) for k,v in sources.items()},
              "v2_vs_final_review": diff(sources["v2_reviewed"],sources["final_review"])}
    path=ROOT / "docs/translation_memory/canonical_review_alignment.json"
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "canonical_encoding": validation["encoding_diagnostics"],
        "reviewed_vs_canonical": {
            k:{k2:v2 for k2,v2 in v.items() if k2!="different_samples"}
            for k,v in report["reviewed_vs_canonical"].items()},
        "v2_vs_final":{k:v for k,v in report["v2_vs_final_review"].items()
                       if k!="different_samples"}
    },ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
