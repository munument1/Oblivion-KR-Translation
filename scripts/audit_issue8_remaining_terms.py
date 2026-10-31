#!/usr/bin/env python3
"""Read-only issue #8 second-pass candidate enumeration, never edits translations."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# Exact English source identity must match and the Korean alias must be explicit.
# "Gatekeeper", "Marauder", "Cupboard" and Bands titles remain contextual.
TERMS = {
    "Ayleid": (r"(?<![A-Za-z])Ayleids?(?![A-Za-z])",
               ("아일레이드",), "에일리드", "proper"),
    "Crucible": (r"(?<![A-Za-z])Crucible(?![A-Za-z])",
                 ("크루서블",), "크루시블", "place"),
    "Jauffre": (r"(?<![A-Za-z])Jauffre(?![A-Za-z])",
               ("조프리",), "죠프리", "proper"),
    "Staff of Sheogorath": (r"(?<![A-Za-z])Staff of Sheogorath(?![A-Za-z])",
               ("쉐오고라스의 스태프",), "쉐오고라스의 지팡이", "item"),
    "Gatekeeper": (r"(?<![A-Za-z])Gatekeeper(?![A-Za-z])",
               ("관문지기", "문지기"), "게이트키퍼", "contextual"),
    "Arquen": (r"(?<![A-Za-z])Arquen(?![A-Za-z])",
               ("아르쿠엔", "아르퀜"), "아퀜", "proper"),
    "Modryn Oreyn": (r"(?<![A-Za-z])Modryn Oreyn(?![A-Za-z])",
               ("모드린 오레인",), "모드윈 오레인", "proper"),
    "Vicente Valtieri": (r"(?<![A-Za-z])Vicente Valtieri(?![A-Za-z])",
               ("비센티 발티에리",), "비센테 발티에리", "proper"),
    "Mankar Camoran": (r"(?<![A-Za-z])Mankar Camoran(?![A-Za-z])",
               ("맨카 케모런",), "맨카 캐모런", "proper"),
    "Golden Saint": (r"(?<![A-Za-z])Golden Saints?(?![A-Za-z])",
               ("골드 세인트",), "골든 세인트", "proper"),
    "Dark Seducer": (r"(?<![A-Za-z])Dark Seducers?(?![A-Za-z])",
               ("다크 시듀어",), "다크 세듀서", "proper"),
    "Marauder": (r"(?<![A-Za-z])Marauders?(?![A-Za-z])",
               ("약탈자",), "습격자", "contextual"),
    "Cupboard": (r"(?<![A-Za-z])Cupboards?(?![A-Za-z])",
               ("찬장",), "선반", "contextual_seed"),
    "Bands of the Chosen": (r"(?<![A-Za-z])Bands of the Chosen(?![A-Za-z])",
               ("선택받은 자의 밴드", "선민의 팔찌"), "선택받은 자의 팔찌", "contextual"),
}
COMPILED = {name: re.compile(pattern, re.I)
            for name, (pattern, _, _, _) in TERMS.items()}
COLUMNS = ["term","kind","classification","source","record_type","raw_formid",
           "editor_id","field","occurrence","english_excerpt","korean_excerpt",
           "old_english_sha256","old_korean_sha256","matched_alias",
           "canonical","raw_csv_line_number"]

def surface(record, field):
    if record in {"INFO", "DIAL"}:
        return "dialogue"
    if record == "BOOK":
        return "book_title" if field == "FULL" else "book_body"
    if record == "QUST":
        return "quest_journal" if field == "CNAM" else "quest_other"
    if record in {"CELL", "WRLD", "REFR", "REGN"}:
        return "location"
    if field == "FULL":
        return "full_name"
    return "other"

def examine(row, line):
    source_text = row.get("old_english", "")
    korean = row.get("obcjk_unicode_text", "")
    if not korean and row.get("obcjk_utf8_hex"):
        try:
            korean = bytes.fromhex(row["obcjk_utf8_hex"]).rstrip(b"\0").decode("utf-8")
        except (ValueError, UnicodeError):
            pass
    found=[]
    for name,(_,aliases,canonical,kind) in TERMS.items():
        if not COMPILED[name].search(source_text):
            continue
        present = [a for a in aliases if a in korean]
        if len(present)>1:
            classification="mixed_aliases_review"
        elif len(present)==1 and canonical not in korean:
            classification="alias_candidate" if kind not in {"contextual","contextual_seed"} else "context_required"
        elif len(present)==1:
            classification="mixed_canonical_review"
        elif canonical in korean:
            classification="canonical_match"
        else:
            classification="unrecognized_context"
        found.append(dict(
            term=name, kind=surface(row.get("record_type",""), row.get("field","")),
            classification=classification, source=row.get("effective_source",""),
            record_type=row.get("record_type",""),raw_formid=row.get("raw_formid",""),
            editor_id=row.get("editor_id",""),field=row.get("field",""),
            occurrence=row.get("occurrence",""),
            english_excerpt=source_text[:320].replace("\r","\\r").replace("\n","\\n"),
            korean_excerpt=korean[:520].replace("\r","\\r").replace("\n","\\n"),
            old_english_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            old_korean_sha256=hashlib.sha256(korean.encode("utf-8")).hexdigest(),
            matched_alias="|".join(present),
            canonical=canonical,raw_csv_line_number=line
        ))
    return found

def run(canonical, locations, outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    results=[]
    hashes={}
    count_sources=Counter()
    for path in [canonical,locations]:
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open("r",encoding="utf-8-sig",newline="") as handle:
            reader=csv.DictReader(handle)
            for idx,row in enumerate(reader,2):
                count_sources[path.name]+=1
                results.extend(examine(row,idx))
    results.sort(key=lambda x:(x["term"],x["source"],x["raw_formid"],
                              x["field"],x["occurrence"],x["raw_csv_line_number"]))
    with (outdir/"ISSUE8_REMAINING_TERM_CANDIDATES.csv").open(
            "w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    count=Counter((row["term"],row["classification"]) for row in results)
    by_term={name:{
        "total":sum(v for (t,k),v in count.items() if t==name),
        "status":dict(sorted((k,v) for (t,k),v in count.items() if t==name)),
        "surfaces":dict(Counter(x["kind"] for x in results if x["term"]==name)),
        "examples":[{k:x[k] for k in ("source","record_type","raw_formid","field",
             "english_excerpt","korean_excerpt","matched_alias")}
             for x in results if x["term"]==name and x["classification"]
             in ("alias_candidate","context_required","mixed_aliases_review")][:18]
    } for name in TERMS}
    obj={"input_sha256":hashes,"input_rows":dict(count_sources),
         "total_term_hits":len(results),"terms":by_term,
         "warning":"Names only; no edits, and context_required is never automatically fixable."}
    (outdir/"ISSUE8_REMAINING_TERM_SUMMARY.json").write_text(
        json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"total_term_hits":len(results),
        "terms":{n:{"total":v["total"],"status":v["status"]}
                 for n,v in by_term.items()}},ensure_ascii=False,indent=2))
    return obj

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--translations",type=Path,default=Path("canonical_translation_v2.csv"))
    p.add_argument("--locations",type=Path,default=Path("canonical_locations_v2.csv"))
    p.add_argument("--outdir",type=Path,default=Path("issue8_remaining_term_review"))
    args=p.parse_args()
    run(args.translations,args.locations,args.outdir)
