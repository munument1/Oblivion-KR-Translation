"""Fail-closed classification of the eight remaining historical legacy-codec cases.

The release uses verified UTF-8. Six entries require plain ASCII quotation
marks in the historical codec; two deliberately test font characters whose
raw byte sequence is valid for the encoder but intentionally ambiguous for
the decoder. Neither class should be normalized by copying UTF-8 to legacy.
"""
from pathlib import Path
import csv, hashlib, json
from oblivion_korean_codec import encode_legacy,decode_legacy
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"canonical_translation_v2.csv"
EXPECTED_SHA="97072941553ae611903c604cf6c14d78e5afbf61cae4ffc45016950e01b060c1"
REPORT=ROOT/"docs/translation_memory/legacy_codec_exception_policy.json"
TECHNICAL={("Oblivion.esm","BOOK","00088935","DESC","testqabook"),
           ("Oblivion.esm","BOOK","000C810E","DESC","testFonts")}
QUOTE_FORMS={
    ("Oblivion.esm","INFO","00022B39","NAM1"),
    ("Oblivion.esm","INFO","00022B42","NAM1"),
    ("Oblivion.esm","INFO","00022B4F","NAM1"),
    ("Oblivion.esm","INFO","000302D5","NAM1"),
    ("Oblivion.esm","INFO","00033FCB","NAM1"),
    ("Oblivion.esm","INFO","00035C60","NAM1"),
}
def main():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED_SHA:
        raise ValueError("Canonical SHA drift: abort before classification")
    csv.field_size_limit(100_000_000)
    findings=[]
    with SOURCE.open(encoding="utf-8-sig",newline="") as stream:
        for row in csv.DictReader(stream):
            ko=row["new_korean"]
            raw=bytes.fromhex(row["new_bytes_hex"])
            if not raw.endswith(b"\0") or b"\0" in raw[:-1]:
                raise ValueError("Invalid NUL framing")
            try:
                legacy=decode_legacy(raw[:-1])
                problem=(legacy != ko)
            except (UnicodeError,ValueError):
                legacy=None
                problem=True
            if not problem: continue
            core=(row["effective_source"],row["record_type"],
                  f"{int(row['raw_formid'],16):08X}",row["field"])
            technical=(*core,row["editor_id"])
            if technical in TECHNICAL:
                mode="technical_test_bytes_unchanged"
                if raw!=encode_legacy(ko)+b"\0" or legacy is not None:
                    raise ValueError("Technical book encoder or decoder behavior changed")
            elif core in QUOTE_FORMS:
                mode="legacy_ascii_quotes_for_unencodable_unicode_marks"
                if legacy != ko.replace("『",'"').replace("』",'"'):
                    raise ValueError("Legacy quotes differ beyond approved punctuation")
                if raw != encode_legacy(legacy)+b"\0":
                    raise ValueError("Quoted legacy text has corrupted bytes")
            else:
                raise ValueError(f"Unreviewed legacy discrepancy: {core}")
            findings.append({
                "source":core[0],"type":core[1],"formid":core[2],"field":core[3],
                "editor_id":row.get("editor_id",""),
                "occurrence":str(int(row.get("occurrence") or 0)),
                "english_sha256":hashlib.sha256(row["old_english"].encode()).hexdigest(),
                "utf8_target_sha256":hashlib.sha256(ko.encode()).hexdigest(),
                "policy":mode,
            })
    if len(findings)!=8 or {x["formid"] for x in findings}!={x[2] for x in TECHNICAL}|{x[2] for x in QUOTE_FORMS}:
        raise ValueError(f"Unexpected legacy exception count or identities: {len(findings)}")
    REPORT.write_text(json.dumps({
        "canonical_sha256":EXPECTED_SHA,"total":len(findings),
        "technical_font_test_cases":2,"quotation_fallback_cases":6,
        "unexplained_legacy_mismatches":0,
        "conclusion":"All 8 discrepancies are accounted for by historical codec constraints. Do not blindly rewrite.",
        "cases":findings
    },ensure_ascii=False,indent=2)+"\n","utf-8")
    print("PASS: 6 ASCII-quote codec fallbacks, 2 technical font tests, 0 unexplained")
if __name__=="__main__":main()
