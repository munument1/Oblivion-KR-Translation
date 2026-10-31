"""Read-only cross-release audit: Oblivion v1.2.0 vs published UOP/USIP/UODP.

Compare actual ESP subrecord values via their TES4 master ownership, FormID,
record signature, field, and occurrence. Never assume a patch's text is the
main game's: UOP/USIP/UODP may deliberately change content.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from build_unofficial_release import read_records, reviewed_identity
from scripts.qa_issue8_integrated_overlay import run as integrated_run

ARCHIVES = {
    "UOP": ("UOP_KR_UTF8_obCJK_3.5.9a_KR1.12_20261031.zip",
            "ee4f6e8089d8410a3b9de5709bfed05022f4d81dcd6e5293ae1a6b91d506fd1c"),
    "USIP": ("USIP_KR_UTF8_obCJK_1.6.2_KR1.9_20261031.zip",
             "5a13d90dcd2deb96060d1fd0fe55a316be6d47dc89dc712a1ed77e945b005723"),
    "UODP": ("UODP_KR_UTF8_obCJK_v27_KR1.10_20261025.zip",
             "39ec7cd6ad8d0a83090b8fd6752d7d3fe7dd0378099969b227694d455eb65240"),
}
FIELD_KEYS=("source","record_type","formid","field","editor_id","occurrence","original_csv_line")
COLUMNS=("patch","esp","record_type","patch_formid","record_editor","base_source","base_formid",
         "field","occurrence","original_csv_line","english_excerpt","before_ko",
         "new_v120_ko","published_ko","published_utf8_status","comparison",
         "is_forward_manifest","published_field_sha256","proposed_utf8_sha256")

def read_changed(data_csv):
    with data_csv.open(encoding="utf-8-sig", newline="") as stream:
        rows=list(csv.DictReader(stream))
    candidates=defaultdict(list)
    for row in rows:
        key=(row["source"], row["record_type"].encode("ascii"),int(row["formid"],16),
             row["field"].encode("ascii"), int(row["occurrence"]))
        candidates[key].append(row)
    return rows,candidates

def decode_editor(s):
    if s.startswith("b'") or s.startswith('b"'):
        try:return ast.literal_eval(s).rstrip(b"\x00")
        except (ValueError, SyntaxError):return None
    return s.encode("cp1252",errors="replace").rstrip(b"\x00") if s else None

def run(release_dir:Path,outdir:Path):
    outdir.mkdir(parents=True, exist_ok=True)
    integrated_run(outdir/"v120_baseline")
    changed,candidates=read_changed(outdir/"v120_baseline"/"ISSUE8_INTEGRATED_DIFF.csv")
    patch_coverage=Counter()
    detailed=[]
    from unofficial_text_forwarding import load_text_forwarding
    ROOT=Path(__file__).resolve().parents[1]
    manifest=load_text_forwarding(ROOT)
    for patch,(filename,expected_sha) in ARCHIVES.items():
        zip_path=release_dir/filename
        if not zip_path.is_file():
            raise FileNotFoundError(zip_path)
        if hashlib.sha256(zip_path.read_bytes()).hexdigest()!=expected_sha:
            raise ValueError(f"{patch} release ZIP SHA-256 mismatch")
        with ZipFile(zip_path) as archive,TemporaryDirectory() as td:
            if archive.testzip():
                raise ValueError(f"Corrupt {patch} ZIP")
            esp_names=[x for x in archive.namelist() if x.lower().endswith(".esp")]
            if not esp_names:
                raise ValueError(f"{patch} has no ESP")
            for esp in esp_names:
                path=Path(td)/Path(esp).name
                path.write_bytes(archive.read(esp))
                records=read_records(path)
                hits=0
                for (kind,fid),fields in records.items():
                    if kind==b"TES4":continue
                    owner_id=reviewed_identity(records,fid)
                    if not owner_id:continue
                    owner,base_fid=owner_id
                    if owner not in ("Oblivion.esm","Knights.esp","DLCBattlehornCastle.esp","DLCMehrunesRazor.esp"):
                        continue
                    indices=defaultdict(list)
                    for j,(f,v) in enumerate(fields):
                        indices[f].append((j,v))
                    editor=next((v.rstrip(b"\0") for f,v in fields if f==b"EDID"),None)
                    for field,positions in indices.items():
                        for occ,(position,actual) in enumerate(positions):
                            target=candidates.get((owner,kind,base_fid,field,occ),[])
                            if not target:continue
                            for row in target:
                                expected_editor=decode_editor(row["editor_id"])
                                if expected_editor is not None and editor is not None and expected_editor!=editor:
                                    continue
                                before=row["before_ko"].encode("utf-8")+b"\0"
                                after=row["after_ko"].encode("utf-8")+b"\0"
                                if actual==after:state="matches_v120"
                                elif actual==before:state="EXACT_STALE_PRE_V120"
                                else:
                                    try:
                                        decoded=actual.rstrip(b"\0").decode("utf-8")
                                        if row["before_ko"] in decoded and row["before_ko"]!=row["after_ko"]:
                                            state="OLD_TEXT_PRESENT_CONTEXT"
                                        elif row["after_ko"] in decoded:state="NEW_TEXT_PRESENT_CONTEXT"
                                        else:state="DIFFERENT_PATCH_TEXT_REVIEW"
                                        utf_status="utf8"
                                    except UnicodeError:
                                        decoded=actual[:180].hex()
                                        state="NON_UTF8_REVIEW"
                                        utf_status="non_utf8"
                                if state in ("matches_v120","EXACT_STALE_PRE_V120"):
                                    decoded=actual.rstrip(b"\0").decode("utf-8",errors="replace")
                                    utf_status="utf8"
                                manifest_key=(esp,kind,fid,field,editor or b"",occ)
                                manifested=manifest_key in manifest
                                patch_coverage[(patch,state)]+=1
                                hits+=1
                                detailed.append({
                                    "patch":patch,"esp":esp,"record_type":kind.decode("ascii"),
                                    "patch_formid":f"{fid:08X}","record_editor":repr(editor),
                                    "base_source":owner,"base_formid":f"{base_fid:08X}",
                                    "field":field.decode("ascii"),"occurrence":occ,
                                    "original_csv_line":row["original_csv_line"],
                                    "english_excerpt":row["english"][:230].replace("\r","\\r").replace("\n","\\n"),
                                    "before_ko":row["before_ko"],
                                    "new_v120_ko":row["after_ko"],
                                    "published_ko":decoded,
                                    "published_utf8_status":utf_status,"comparison":state,
                                    "is_forward_manifest":manifested,
                                    "published_field_sha256":hashlib.sha256(actual).hexdigest(),
                                    "proposed_utf8_sha256":hashlib.sha256(after).hexdigest(),
                                })
                patch_coverage[(patch,"total_esp_records")]+=len(records)-1
                patch_coverage[(patch,"source_field_hits")]+=hits
    # No patch may be changed by this read-only job.
    with (outdir/"ISSUE8_V120_UNOFFICIAL_OVERLAP.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS)
        w.writeheader();w.writerows(sorted(detailed,key=lambda x:(x["patch"],x["esp"],x["patch_formid"],x["field"],x["occurrence"])))
    bypatch={p:{status:count for (pp,status),count in patch_coverage.items() if pp==p} for p in ARCHIVES}
    summary={
        "audit":"READ_ONLY source master/FormID/field/occurrence audit of real release ZIPs",
        "main_changed_canonical_records":len(changed),
        "release_zip_sha256":{p:v[1] for p,v in ARCHIVES.items()},
        "per_patch":bypatch,
        "sample_stale":[{k:d[k] for k in ("patch","esp","base_source","record_type","base_formid","field","before_ko","new_v120_ko","published_ko","is_forward_manifest")}
            for d in detailed if d["comparison"]=="EXACT_STALE_PRE_V120"][:80],
        "cautions":["A plugin's intentional content edits must not be blindly replaced",
                    "Same FormID with another field is not a same-field collision",
                    "No game executable or original English masters were executed"],
    }
    (outdir/"ISSUE8_V120_UNOFFICIAL_OVERLAP_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"total_changed":len(changed),"per_patch":bypatch},ensure_ascii=False,indent=2))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--release-dir",type=Path,required=True)
    p.add_argument("--outdir",type=Path,default=Path("issue8_unofficial_overlap"))
    args=p.parse_args()
    run(args.release_dir,args.outdir)
