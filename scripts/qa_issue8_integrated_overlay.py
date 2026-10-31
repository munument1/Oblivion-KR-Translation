#!/usr/bin/env python3
"""Issue #8 integrated *translation-data* dry run using exact OBCJK build order.

No copyrighted ESM/ESP, runtime DLL, game executable, or installer is generated.
This establishes that every staged source-guarded correction composes safely
with PR #13, canonical inputs remain byte-identical, and the output names are
inspectable for follow-up gameplay verification.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_vanilla_overlay import load_translations
from book_title_overrides import apply_book_title_overrides
from claude_issue8_crate import correct_crate_names
from claude_issue8_amber import correct_amber_equipment_names
from issue8_reporter_term_patch import correct_reporter_terms, verify_canonical
from issue8_remaining_term_patch import correct_remaining_glossary_names
from issue8_context_verified_patch import correct_context_verified_names
from issue8_cupboard_patch import correct_cupboard_names
from issue8_glossary_exceptions import correct_glossary_exceptions

TOKEN_RE = re.compile(r"<[^>]*>|%(?:[-+0#]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+")
FILENAME = "ISSUE8_INTEGRATED_DIFF.csv"
SUMMARY = "ISSUE8_INTEGRATED_DATA_QA.json"
COLUMNS = ("source","record_type","formid","field","english","editor_id",
           "occurrence","original_csv_line","before_ko","after_ko",
           "before_utf8_sha256","after_utf8_sha256")

def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()

def index_records(table):
    out={}
    for key, items in table.items():
        for index, item in enumerate(items):
            uid=(key,index)
            if uid in out:
                raise ValueError("Duplicate in-memory source index")
            out[uid]=item
    return out

def source_metadata(item):
    return (item.source,item.record_type,item.formid,item.field,item.english,
            item.editor_id,item.occurrence,item.line)

def run(outdir: Path):
    original=ROOT/"canonical_translation_v2.csv"
    locations=ROOT/"canonical_locations_v2.csv"
    verify_canonical(original)
    hashes_before={path.name:sha(path.read_bytes()) for path in (original,locations)}
    table=load_translations(original,(
        ROOT/"canonical_ui_supplement_v1.csv",
        ROOT/"canonical_nexus_56688_fur_v1.csv",
    ),encoded_column="obcjk_utf8_hex")
    before=index_records(table)

    # This order MUST be identical to build_obcjk_release.build().
    steps={}
    steps["crate"]=correct_crate_names(table)
    steps["amber"]=correct_amber_equipment_names(table)
    steps["book_title"]=apply_book_title_overrides(
        table,ROOT/"canonical_book_title_overrides_v1.csv")
    steps["reporter"]=correct_reporter_terms(table,original)
    steps["remaining_names"]=correct_remaining_glossary_names(table,original)
    steps["context_names"]=correct_context_verified_names(table,original)
    steps["cupboard"]=correct_cupboard_names(table,original)
    steps["exceptions"]=correct_glossary_exceptions(table,original)

    if steps["book_title"] != 2:
        raise ValueError(f"Expected both Barenziah & Mythic Dawn title updates: {steps['book_title']}")
    if steps["reporter"].get("Mythic Dawn") != 105:
        raise ValueError("PR #13 must precede reporter patch; expected 105 remaining Mythic Dawn aliases")
    after=index_records(table)
    if before.keys()!=after.keys():
        raise ValueError("Source record indices changed during integration")
    changes=[]
    for uid,b in before.items():
        a=after[uid]
        if source_metadata(a)!=source_metadata(b):
            raise ValueError(f"Source identity changed: {uid}")
        if a.korean == b.korean:
            continue
        if not a.korean.endswith(b"\0") or not b.korean.endswith(b"\0"):
            raise ValueError(f"NUL terminator invalid: {uid}")
        ko_before=b.korean[:-1].decode("utf-8")
        ko_after=a.korean[:-1].decode("utf-8")
        if TOKEN_RE.findall(ko_before)!=TOKEN_RE.findall(ko_after):
            raise ValueError(f"Tags/placeholders changed: {uid}")
        if [c for c in ko_before if c in "\r\n"]!=[c for c in ko_after if c in "\r\n"]:
            raise ValueError(f"Newlines changed: {uid}")
        changes.append(dict(source=a.source,
            record_type=a.record_type.decode("ascii"),
            formid=f"{a.formid:08X}",field=a.field.decode("ascii"),
            english=a.english,editor_id=a.editor_id,
            occurrence=a.occurrence,original_csv_line=a.line,
            before_ko=ko_before,after_ko=ko_after,
            before_utf8_sha256=sha(b.korean),after_utf8_sha256=sha(a.korean)))
    changes.sort(key=lambda r:(r["source"],r["record_type"],r["formid"],
                               r["field"],str(r["occurrence"]),str(r["original_csv_line"])))
    book2=table.get(("Oblivion.esm",b"BOOK",0x00022B05,b"FULL"),[])
    matches=[x for x in book2 if x.english=="Mythic Dawn Commentaries 2"]
    if len(matches)!=1 or matches[0].korean != "미식 던 논평집 2".encode()+b"\0":
        raise ValueError("Mythic Dawn volume 2 integration regression")
    hashes_after={path.name:sha(path.read_bytes()) for path in (original,locations)}
    if hashes_before!=hashes_after:
        raise ValueError("Canonical source was mutated during integration")

    outdir.mkdir(parents=True,exist_ok=True)
    with (outdir/FILENAME).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(changes)
    summary={
        "kind":"read_only_translation_data_dry_run_NOT_game_plugin_binary",
        "original_canonical_sha256":hashes_after,
        "translations_loaded":len(before),
        "changed_distinct_records":len(changes),
        "changed_by_source":dict(Counter(x["source"] for x in changes)),
        "steps":steps,
        "book2_verified":"미식 던 논평집 2",
        "original_formid_record_field_and_english_preserved":True,
        "original_placeholders_markup_newlines_preserved":True,
        "canonical_input_unchanged":True,
        "needs":["actual Oblivion.esm and official DLC plugin input",
                 "native ESM/ESP patch/structural signature build",
                 "xOBSE/obCJK runtime and in-game menu/dialogue/book/map test",
                 "Nexus/release publication separately"],
    }
    (outdir/SUMMARY).write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps({
        "changed_distinct_records":len(changes),
        "book_title":steps["book_title"],
        "reporter_mythic":steps["reporter"]["Mythic Dawn"],
        "verified_original_untouched":True
    },ensure_ascii=False,indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",type=Path,default=Path("issue8_integrated_qa"))
    opts=p.parse_args()
    run(opts.outdir)
