"""Fail-closed repair for the 12 incomplete OCRP canonical column updates.

The actual Korean text and UTF-8/legacy byte fields were already reconciled.
Only obcjk_unicode_text is stale. All 12 old values must exactly match the
originally reviewed pre-edit texts, source identities and SHA-256 values.

Run --check first and pin candidate_sha256 before --apply.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "8d06e39e11064c2d880d16d93fad9b20894e08f5395861515aeea1a9c8fcd3a0"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def corrections(report_path, legacy_review_path):
    from scripts.reconcile_canonical_ocrp import reviewed_rules
    docs=json.loads(Path(report_path).read_text(encoding="utf-8"))
    rows=docs["changed_record_identities"]
    rules=reviewed_rules(legacy_review_path)
    required={}
    for item in rows:
        key=(item["kind"],f"{int(item['formid'],16):08X}",
             item["field"],item["english_sha256"])
        required.setdefault(key,set()).add(item["old_korean_sha256"])
    if len(rows)!=12 or sum(map(len,required.values()))!=12:
        raise ValueError("Expected 12 distinct audited source-English and old-Korean rows")
    return required,rules


def repair(path, report_path, legacy_review_path, *, expected_source_sha=BASELINE_SHA,
           expected_output_sha=None, apply=False):
    path=Path(path)
    if sha(path)!=expected_source_sha:
        raise ValueError("Source canonical SHA mismatch; no changes made")
    required, rules=corrections(report_path,legacy_review_path)
    matches=set()
    changed=[]
    count=0
    fd,temp_name=tempfile.mkstemp(prefix="canonical_unicode_fix_",suffix=".csv",dir=path.parent)
    os.close(fd)
    tmp=Path(temp_name)
    try:
        csv.field_size_limit(100_000_000)
        with path.open(encoding="utf-8-sig",newline="") as f, \
             tmp.open("w",encoding="utf-8",newline="") as out:
            reader=csv.DictReader(f)
            required_fields={"record_type","raw_formid","field","old_english","new_korean",
                             "obcjk_unicode_text","obcjk_utf8_hex","new_bytes_hex"}
            if not required_fields.issubset(reader.fieldnames or []):
                raise ValueError("Canonical schema changed")
            writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator="\n")
            writer.writeheader()
            for row in reader:
                count+=1
                before=row["obcjk_unicode_text"]
                target=row["new_korean"]
                identity=(row["record_type"],f"{int(row['raw_formid'],16):08X}",
                          row["field"],hashlib.sha256(row["old_english"].encode()).hexdigest())
                if before != target:
                    old_sha=hashlib.sha256(before.encode()).hexdigest()
                    if old_sha not in required.get(identity,set()):
                        raise ValueError(f"Unexpected Unicode-vs-text discrepancy: {identity}")
                    if rules.get((row["old_english"],before)) != target:
                        raise ValueError("Reviewed original/target text does not match")
                    raw=bytes.fromhex(row["obcjk_utf8_hex"])
                    if raw!=target.encode("utf-8")+b"\0":
                        raise ValueError("UTF8 target is not the reviewed Korean")
                    from oblivion_korean_codec import decode_legacy
                    legacy=bytes.fromhex(row["new_bytes_hex"])
                    if not legacy.endswith(b"\0") or decode_legacy(legacy[:-1])!=target:
                        raise ValueError("Legacy target is not the reviewed Korean")
                    identity2=(*identity,old_sha)
                    if identity2 in matches:
                        raise ValueError("Duplicate corrected identity")
                    matches.add(identity2)
                    row["obcjk_unicode_text"]=target
                    changed.append({"kind":identity[0],"formid":identity[1],
                                    "field":identity[2],"english_sha256":identity[3]})
                writer.writerow(row)
        expected={(a,b,c,d,e) for (a,b,c,d),old_set in required.items() for e in old_set}
        if matches!=expected:
            raise ValueError(f"Missing expected source-anchored corrections: {len(expected-matches)}")
        candidate=sha(tmp)
        if expected_output_sha and candidate!=expected_output_sha:
            raise ValueError("Candidate output SHA mismatch; no changes made")
        if apply:
            if not expected_output_sha:
                raise ValueError("--apply requires reviewed expected output SHA")
            if sha(path)!=expected_source_sha:
                raise ValueError("Input changed while checking")
            os.replace(tmp,path)
        return {"rows":count,"columns_reconciled":len(changed),"old_sha256":expected_source_sha,
                "candidate_sha256":candidate,"applied":bool(apply),
                "edits":changed}
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--canonical",type=Path,default=ROOT/"canonical_translation_v2.csv")
    p.add_argument("--report",type=Path,default=ROOT/"docs/translation_memory/ocrp_canonical_applied.json")
    p.add_argument("--review",type=Path,default=ROOT/"mods/ocrp/legacy_retranslation_20261103.json")
    p.add_argument("--output-report",type=Path,default=ROOT/"docs/translation_memory/ocrp_unicode_fix_report.json")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--expected-output-sha")
    a=p.parse_args()
    result=repair(a.canonical,a.report,a.review,apply=a.apply,
                  expected_output_sha=a.expected_output_sha)
    a.output_report.parent.mkdir(parents=True,exist_ok=True)
    a.output_report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="edits"},ensure_ascii=False))

if __name__=="__main__":
    main()
