"""Read-only forensics on remaining canonical legacy-byte mismatches.

These may be intentional archival legacy states, not UTF-8 defects.
No mutation of any translation source.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from oblivion_korean_codec import decode_legacy, encode_legacy
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/"canonical_translation_v2.csv"
OUT=ROOT/"docs/translation_memory/remaining_legacy_encoding_forensics.json"

def main():
    csv.field_size_limit(100_000_000)
    samples=[]
    rows=0
    with TARGET.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            rows+=1
            expected=row["new_korean"]
            try:
                raw=bytes.fromhex(row["new_bytes_hex"])
                if not raw.endswith(b"\0") or b"\0" in raw[:-1]:
                    raise ValueError("Invalid legacy NUL framing")
                old=decode_legacy(raw[:-1])
                if old==expected: continue
                problem="different_legacy_text"
                error=None
            except (UnicodeError,ValueError) as e:
                old=None
                problem="legacy_decode_invalid"
                error=f"{type(e).__name__}: {str(e)[:160]}"
            try:
                encoded=encode_legacy(expected)+b"\0"
                can_encode=True
                encoded_diff=(raw!=encoded)
                encoded_len=len(encoded)
            except (UnicodeError,ValueError) as e:
                can_encode=False
                encoded_diff=None
                encoded_len=None
            samples.append({
                "source":row["effective_source"],"kind":row["record_type"],
                "formid":row["raw_formid"],"field":row["field"],
                "editor_id":row.get("editor_id",""),"occurrence":row.get("occurrence",""),
                "english_excerpt":row["old_english"][:300],
                "target_korean_excerpt":expected[:600],
                "decoded_legacy_excerpt":old[:600] if old is not None else None,
                "legacy_prefix_hex":row["new_bytes_hex"][:180],
                "problem":problem,"error":error,"target_encodable_legacy":can_encode,
                "requires_binary_update":encoded_diff,"target_encoded_length":encoded_len,
                "is_technical_test_book":row["record_type"]=="BOOK" and row.get("editor_id") in {"testqabook","testFonts"},
                "obcjk_verified":row.get("obcjk_conversion_status"),
            })
    if len(samples)!=8:
        raise ValueError(f"Expected 8 legacy diagnostics; source changed: {len(samples)}")
    report={"source":TARGET.name,"rows":rows,
            "nonmatching_legacy_rows":len(samples),
            "warning":"Read-only legacy audit. UTF-8 columns are the release authority; unsafe to overwrite legacy tests without runtime context.",
            "cases":samples}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"rows":rows,"diagnostics":len(samples),
                      "technical_test_books":sum(x["is_technical_test_book"] for x in samples),
                      "unencodable_targets":sum(not x["target_encodable_legacy"] for x in samples)},
                     ensure_ascii=False))
if __name__=="__main__":main()
