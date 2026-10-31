"""Repackage pinned public UOP/USIP/UODP KR ESPs with issue #8 term fixes.

No original English plugins are present or modified. Existing published Korean
ESPs are the source of truth; ONLY audited localizable subrecords change.
Every other field, record ID, script and unselected ESP must be preserved.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_unofficial_release import read_records,rewrite
from build_vanilla_overlay import structure_signature
from scripts.audit_issue8_unofficial_overlap import ARCHIVES

OUTPUTS={
 "UOP":"UOP_KR_UTF8_obCJK_3.5.9a_KR1.13_20261031.zip",
 "USIP":"USIP_KR_UTF8_obCJK_1.6.2_KR1.10_20261031.zip",
 "UODP":"UODP_KR_UTF8_obCJK_v27_KR1.11_20261031.zip",
}
# A reviewer checked source English and existing patch-specific deviations.
# Alter only the designated Korean name, never restore main-game sentences.
CONTEXT={
 ("UOP","QUST","0001E72D","CNAM"):("미씩 던","미식 던",1),
 ("UOP","BOOK","00024549","DESC"):("셰이딘홀","체이딘할",1),
 ("UOP","BOOK","00024561","DESC"):("셰이딘홀","체이딘할",17),
 ("UOP","INFO","0002B09F","NAM1"):("아일레이드","에일리드",1),
 ("UOP","QUST","00036337","CNAM"):("쉐이딘홀","체이딘할",1),
 ("USIP","BOOK","0007F3E7","DESC"):("약탈자","습격자",1),
 ("UOP","CELL","0001EC36","FULL"):("셰이딘홀","체이딘할",1),
}
# Patch's intentionally abbreviated journal omits Cheydinhal; leave verbatim.
KEEP={("UOP","QUST","00035717","CNAM")}
EXPECTED={
 "UOP":{"direct_text":266,"context_text":5,"direct_location":16,"context_location":1,"untouched_review":1,"already_correct":1},
 "USIP":{"direct_text":130,"context_text":1,"direct_location":0,"context_location":0,"untouched_review":0,"already_correct":0},
 "UODP":{"direct_text":75,"context_text":0,"direct_location":1,"context_location":0,"untouched_review":0,"already_correct":0},
}
def load_csv(path):
 with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def digest(data):return hashlib.sha256(data).hexdigest()

def collect(audit):
 patchplan=defaultdict(dict)
 count=defaultdict(Counter)
 report=defaultdict(list)
 for row in load_csv(audit/"ISSUE8_V120_UNOFFICIAL_OVERLAP.csv"):
  patch=row["patch"]
  identity=(patch,row["record_type"],row["base_formid"],row["field"])
  key=(row["esp"],row["record_type"],row["patch_formid"],row["field"],int(row["occurrence"]))
  old=row["published_ko"]
  target=None
  state=row["comparison"]
  if state=="EXACT_STALE_PRE_V120":
   if old!=row["before_ko"]:raise ValueError(f"Contradictory text audit {identity}")
   target=row["new_v120_ko"]; count[patch]["direct_text"]+=1
  elif state=="matches_v120":
   count[patch]["already_correct"]+=1
  elif state=="DIFFERENT_PATCH_TEXT_REVIEW":
   if identity in KEEP:
    count[patch]["untouched_review"]+=1
   elif identity in CONTEXT:
    before,after,expected=CONTEXT[identity]
    if old.count(before)!=expected:raise ValueError(f"Ambiguous contextual text {identity}: {old.count(before)}")
    target=old.replace(before,after)
    count[patch]["context_text"]+=1
   else:raise ValueError(f"Unreviewed patch-specific text: {identity}")
  else:raise ValueError(f"Unexpected text classification {identity} {state}")
  if target is not None:
   patchplan[patch][key]=(old,target,row["published_field_sha256"],"text")
   report[patch].append({"identity":key,"source":row["base_source"],"base_formid":row["base_formid"],"before_sha256":row["published_field_sha256"],
    "after_sha256":digest(target.encode()+b"\0"),"policy":state})
 for row in load_csv(audit/"ISSUE8_UNOFFICIAL_LOCATION_OVERLAPS.csv"):
  patch=row["patch"]
  identity=(patch,row["record_type"],row["base_formid"],row["field"])
  key=(row["esp"],row["record_type"],row["formid"],row["field"],int(row["occurrence"]))
  old=row["actual"]
  if row["status"]=="old":
   if old!=row["old"]:raise ValueError(f"Old location source mismatch {identity}")
   target=row["new"];count[patch]["direct_location"]+=1
  elif row["status"]=="other" and identity in CONTEXT:
   find,repl,expected=CONTEXT[identity]
   if old.count(find)!=expected:raise ValueError(f"Changed patch context {identity}")
   target=old.replace(find,repl);count[patch]["context_location"]+=1
  else:raise ValueError(f"Unreviewed location collision {identity}: {row['status']}")
  if key in patchplan[patch]:raise ValueError(f"Duplicate source field {key}")
  patchplan[patch][key]=(old,target,row["actual_sha256"],"location")
  report[patch].append({"identity":key,"source":row["owner"],"base_formid":row["base_formid"],"before_sha256":row["actual_sha256"],
     "after_sha256":digest(target.encode()+b"\0"),"policy":row["status"]})
 for patch,expected in EXPECTED.items():
  if dict(count[patch])!=expected:raise ValueError(f"{patch} count drift: expected {expected} actual {dict(count[patch])}")
  if len(patchplan[patch])!=sum(v for k,v in expected.items() if k not in ("already_correct","untouched_review")):
   raise ValueError(f"{patch} duplicate field drift")
 return patchplan,count,report

def refresh(release_dir,audit,outdir):
 plans,counts,reports=collect(audit)
 outdir.mkdir(parents=True,exist_ok=True)
 all_stats={}
 for patch,(filename,expected_sha) in ARCHIVES.items():
  prior=release_dir/filename
  if digest(prior.read_bytes())!=expected_sha:raise ValueError(f"Changed {patch} release ZIP")
  output=outdir/OUTPUTS[patch]
  if output.exists():raise FileExistsError(output)
  zip_report={"patch":patch,"from":filename,"from_zip_sha256":expected_sha,
    "new_archive_name":output.name,"counts":dict(counts[patch]),"plugins":{}}
  with ZipFile(prior) as base, TemporaryDirectory() as td:
   if base.testzip():raise ValueError("Baseline ZIP corrupt")
   originals={}
   new_esps={}
   all_names=base.namelist()
   for name in all_names:
    if not name.lower().endswith(".esp"):continue
    original=Path(td)/("old-"+Path(name).name);original.write_bytes(base.read(name))
    old_records=read_records(original)
    modifications=defaultdict(dict)
    selected=[]
    for (ep,kind,fid,field,occ),(before,after,before_sha,category) in plans[patch].items():
     if ep!=name:continue
     key=(kind.encode("ascii"),int(fid,16))
     srcfields=old_records[key]
     indexes=[i for i,(f,v) in enumerate(srcfields) if f==field.encode("ascii")]
     if occ>=len(indexes):raise ValueError("Missing text field occurrence")
     pos=indexes[occ]
     old=srcfields[pos][1]
     if digest(old)!=before_sha or old!=before.encode("utf-8")+b"\0":
      raise ValueError(f"Released ESP field changed {patch} {key} {field} {occ}")
     new=after.encode("utf-8")+b"\0"
     if old==new:raise ValueError("No-op patch record")
     modifications[key][pos]=(field.encode("ascii"),old,new)
     selected.append({"record_type":kind,"formid":fid,"field":field,
         "occurrence":occ,"old_sha256":digest(old),"new_sha256":digest(new),
         "category":category})
    newfile=Path(td)/("new-"+Path(name).name)
    if rewrite(original,newfile,modifications)!=len(selected):
     raise ValueError("Applied count drift")
    if structure_signature(original)!=structure_signature(newfile):
     raise ValueError("Record structure/script drift")
    new_records=read_records(newfile)
    if old_records.keys()!=new_records.keys():raise ValueError("Record identity drift")
    for key,srcfields in old_records.items():
     expected=list(srcfields)
     for pos,(field,old,new) in modifications.get(key,{}).items():
      if expected[pos]!=(field,old):raise ValueError("Original row moved")
      expected[pos]=(field,new)
     if expected!=new_records[key]:raise ValueError(f"Unselected subrecord changed: {key}")
    originals[name]=original
    new_esps[name]=newfile
    zip_report["plugins"][name]={"before_sha256":digest(original.read_bytes()),
        "after_sha256":digest(newfile.read_bytes()),"changed_fields":len(selected),
        "fields":selected}
   if sum(d["changed_fields"] for d in zip_report["plugins"].values())!=len(plans[patch]):
    raise ValueError("ZIP field count mismatch")
   # Preserve all original non-ESP members byte-identically, except superseded
   # checksums and validation metadata; keep the prior report for provenance.
   with ZipFile(output,"x",ZIP_DEFLATED,compresslevel=6) as dest:
    for name in all_names:
     if name in new_esps:dest.writestr(name,new_esps[name].read_bytes())
     elif name=="validation.json":dest.writestr("previous_validation.json",base.read(name))
     elif name=="SHA256SUMS.txt":continue
     elif name=="previous_validation.json":raise ValueError("Prior validation filename collision")
     else:dest.writestr(name,base.read(name))
    dest.writestr("validation.json",json.dumps(zip_report,ensure_ascii=False,indent=2)+"\n")
    dest.writestr("SHA256SUMS.txt","".join(
     f"{digest(newfile.read_bytes())}  {name}\n" for name,newfile in sorted(new_esps.items())))
    dest.writestr("ISSUE8_GLOSSARY_UPDATE.txt",
      "v1.2.0 glossary name synchronization. Exact published ESP subrecords only; "
      "original patch gameplay changes, compiled scripts, and unrelated fields preserved. "
      "See validation.json for input/output hashes and record identities.\n")
  with ZipFile(output) as z:
   if z.testzip():raise ValueError("Corrupt output")
   for name,file in new_esps.items():
    if digest(z.read(name))!=zip_report["plugins"][name]["after_sha256"]:raise ValueError("ZIP ESP hash")
  final_hash=digest(output.read_bytes())
  output.with_suffix(".zip.sha256").write_text(f"{final_hash}  {output.name}\n",encoding="ascii")
  zip_report["final_zip_sha256"]=final_hash
  all_stats[patch]=zip_report
 (outdir/"ISSUE8_UNOFFICIAL_RELEASE_QA.json").write_text(
  json.dumps(all_stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({p:{"filename":x["new_archive_name"],
  "changed":sum(v["changed_fields"] for v in x["plugins"].values()),
  "sha256":x["final_zip_sha256"],"counts":x["counts"]} for p,x in all_stats.items()},
  ensure_ascii=False,indent=2))
 return all_stats

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--release-dir",type=Path,required=True)
 p.add_argument("--audit",type=Path,required=True)
 p.add_argument("--outdir",type=Path,required=True)
 args=p.parse_args()
 refresh(args.release_dir,args.audit,args.outdir)
