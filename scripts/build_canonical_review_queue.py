"""Create source-anchored review priorities without changing translations.

The old final_review_override.csv is an *alternative* source, NOT an automatic
authority over newer canonical translations. The 9,049 V2 reviewed rows
are a separate frozen subset; any disagreement must retain source evidence.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from scripts.audit_canonical_review_alignment import ROOT,fingerprint,abbreviation

LATIN=re.compile(r"[A-Za-z]")
HTML=re.compile(r"<[^>]*>")
NUM=re.compile(r"(?<![A-Za-z0-9])\d+(?![A-Za-z0-9])")
PLACE=re.compile(r"%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+")
PRIORITY={"INFO":8,"QUST":8,"DIAL":7,"NPC_":6,"BOOK":4,"GMST":6,
          "WEAP":5,"ARMO":5,"SPEL":5,"CONT":4,"FACT":5}

def load_rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return {fingerprint(row): row for row in csv.DictReader(f)}

def rating(key,ko,alternative):
    typ,field=key[1],key[3]
    score=PRIORITY.get(typ,3)
    tags=HTML.findall(ko)
    oldtags=HTML.findall(alternative)
    reasons=[]
    if ko.strip()=="":
        score+=20;reasons.append("empty")
    if LATIN.search(HTML.sub("",ko)) and not LATIN.search(HTML.sub("",alternative)):
        score+=5;reasons.append("latin_in_canonical_only")
    eng_nums=NUM.findall(HTML.sub("",key[6]))
    ko_nums=NUM.findall(HTML.sub("",ko))
    alt_nums=NUM.findall(HTML.sub("",alternative))
    if eng_nums and ko_nums!=eng_nums and alt_nums==eng_nums:
        score+=6;reasons.append("numeric_candidate")
    if PLACE.findall(ko)!=PLACE.findall(alternative):
        score+=6;reasons.append("placeholder_difference")
    if typ=="BOOK" and field=="DESC" and tags!=oldtags:
        score-=3;reasons.append("different_book_markup")
    if len(key[6])>=100 and len(ko)<=10 and len(alternative)>=30:
        score+=5;reasons.append("length_anomaly_candidate")
    return score,reasons

def main():
    csv.field_size_limit(100_000_000)
    canonical=load_rows(ROOT/"canonical_translation_v2.csv")
    final=load_rows(ROOT/"final_review_override.csv")
    v2=load_rows(ROOT/"docs/v2_review/source_snapshot/V2_SOL_FINAL_OVERRIDE.csv")
    by_type=Counter();by_field=Counter();by_reason=Counter();queue=[];v2_diffs=[]
    for key,row in final.items():
        if key not in canonical or row["new_korean"]==canonical[key]["new_korean"]:
            continue
        current=canonical[key]["new_korean"]
        alt=row["new_korean"]
        score,reasons=rating(key,current,alt)
        by_type[key[1]]+=1
        by_field[(key[1],key[3])]+=1
        for reason in reasons:
            by_reason[reason]+=1
        entry={
            **abbreviation(key),"reviewed_source":"final_review_override.csv",
            "v2_reviewed_subgroup":key in v2,
            "canonical_korean":current[:800],
            "historical_review_korean":alt[:800],
            "score":score,"review_flags":reasons,
            "action":"SOURCE_CONTEXT_REVIEW_ONLY",
        }
        if key in v2:
            v2_diffs.append(entry)
        else:
            queue.append(entry)
    queue.sort(key=lambda x:(-x["score"],x["source"],x["record_type"],
                              x["formid"],x["field"],x["english_sha256"]))
    report={
        "status":"REVIEW_REQUIRED; no automatic canonical changes",
        "source_identity":"plugin+type+full_formid+field+editor_id+occurrence+English",
        "total_conflicts":len(queue)+len(v2_diffs),
        "historical_non_v2_conflicts":len(queue),
        "v2_conflicts":len(v2_diffs),
        "by_record_type":dict(by_type.most_common()),
        "by_type_field":{f"{a}.{b}":count for (a,b),count in by_field.most_common()},
        "flags":dict(by_reason),
        "all_v2_conflicts":v2_diffs,
        "high_priority_queue":queue[:250],
        "remaining_entries":len(queue)-min(len(queue),250),
        "caveat":"The historical final_review file is not necessarily newer or more accurate than canonical."
    }
    output=ROOT/"docs/translation_memory/canonical_review_priority_queue.json"
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")
    print(json.dumps({k:report[k] for k in ("total_conflicts","historical_non_v2_conflicts",
                                           "v2_conflicts","by_record_type","flags")},
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
