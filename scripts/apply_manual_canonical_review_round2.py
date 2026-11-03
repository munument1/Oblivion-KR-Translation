"""Exact-English, fixed-identity, human reviewed canonical semantic patches.

Never apply a historical override wholesale. Requires exact previously approved
Korean text, full FormID, source text, occurrence, editor ID and SHA-pinned corpus.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,re,tempfile
from pathlib import Path
from oblivion_korean_codec import encode_legacy,decode_legacy

ROOT=Path(__file__).resolve().parents[1]
BASE_SHA="db73d95fe31e58f569da8f364546ae6beba562259ccac5deade2838dd4da1862"
RULES=ROOT/"docs/translation_memory/manual_source_review_round2.json"

def file_sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def identity(row):
    return (row["effective_source"],row["record_type"],f"{int(row['raw_formid'],16):08X}",
            row["field"],row.get("editor_id",""),str(int(row.get("occurrence") or 0)),
            row["old_english"])

def patch(path,rules_path=RULES,*,apply=False,expected_output_sha=None):
    path=Path(path)
    if path.name!="canonical_translation_v2.csv":
        raise ValueError("Unsupported canonical file")
    current_sha=file_sha(path)
    if expected_output_sha and current_sha==expected_output_sha:
        return {"already_applied":True,"new_sha256":current_sha,"changed":0}
    if current_sha!=BASE_SHA:
        raise ValueError("Canonical source hash mismatch: refusing to edit")
    rules_list=json.loads(Path(rules_path).read_text("utf-8"))["source_anchored_reviews"]
    rules={identity(r):r for r in rules_list}
    if len(rules)!=len(rules_list) or len(rules)!=2:
        raise ValueError("Review entries duplicated or unexpected number")
    with path.open("rb") as f: head=f.read(131072)
    newline="\r\n" if b"\r\n" in head else "\n"
    fd,tempname=tempfile.mkstemp(prefix="canonical_manual_review_",suffix=".csv",dir=path.parent)
    os.close(fd)
    temp=Path(tempname)
    matched=set()
    try:
        csv.field_size_limit(100_000_000)
        with path.open(encoding="utf-8-sig",newline="") as source, \
             temp.open("w",encoding="utf-8",newline="") as output:
            reader=csv.DictReader(source)
            required={"effective_source","record_type","raw_formid","field","editor_id",
                      "occurrence","old_english","new_korean","obcjk_unicode_text",
                      "obcjk_utf8_hex","new_bytes_hex"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("Canonical format changed")
            writer=csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator=newline)
            writer.writeheader()
            count=0
            for row in reader:
                count+=1
                key=identity(row)
                item=rules.get(key)
                if item:
                    if key in matched:
                        raise ValueError("Duplicate canonical identity")
                    matched.add(key)
                    before,after=item["old_korean"],item["new_korean"]
                    if before==after or row["new_korean"]!=before or row["obcjk_unicode_text"]!=before:
                        raise ValueError("Korean source mismatch")
                    if bytes.fromhex(row["obcjk_utf8_hex"])!=before.encode("utf-8")+b"\0":
                        raise ValueError("UTF-8 byte source mismatch")
                    legacy=bytes.fromhex(row["new_bytes_hex"])
                    if not legacy.endswith(b"\0") or decode_legacy(legacy[:-1])!=before:
                        raise ValueError("Legacy byte source mismatch")
                    marker=re.compile(r"<[^>]*>|%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+")
                    if marker.findall(before)!=marker.findall(after):
                        raise ValueError("Placeholder/markup drift")
                    if re.findall(r"\d+",before)!=re.findall(r"\d+",after):
                        raise ValueError("Digit drift")
                    if [x for x in before if x in "\r\n"]!=[x for x in after if x in "\r\n"]:
                        raise ValueError("Newline drift")
                    row["new_korean"]=after
                    row["obcjk_unicode_text"]=after
                    row["obcjk_utf8_hex"]=(after.encode("utf8")+b"\0").hex()
                    row["new_bytes_hex"]=(encode_legacy(after)+b"\0").hex()
                writer.writerow(row)
        if matched!=set(rules):
            raise ValueError("Some audited source rows are missing")
        candidate=file_sha(temp)
        bytes_after=temp.stat().st_size
        if expected_output_sha and candidate!=expected_output_sha:
            raise ValueError("Candidate SHA does not match approved review")
        if apply:
            if not expected_output_sha:
                raise ValueError("Apply requires pre-reviewed output SHA")
            if file_sha(path)!=BASE_SHA:
                raise ValueError("Input modified while auditing")
            os.replace(temp,path)
        return {"source_sha256":current_sha,"candidate_sha256":candidate,
                "rows":count,"changed":len(matched),"new_bytes":bytes_after,
                "applied":bool(apply)}
    finally:
        if temp.exists():
            temp.unlink()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply",action="store_true")
    p.add_argument("--expected-output-sha")
    p.add_argument("--canonical",type=Path,default=ROOT/"canonical_translation_v2.csv")
    p.add_argument("--rules",type=Path,default=RULES)
    p.add_argument("--report",type=Path,default=ROOT/"docs/translation_memory/manual_review_round2_report.json")
    args=p.parse_args()
    result=patch(args.canonical,args.rules,apply=args.apply,
                 expected_output_sha=args.expected_output_sha)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__": main()
