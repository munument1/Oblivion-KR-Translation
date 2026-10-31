"""Audit v1.1.9→v1.2.0 location override collisions in released unofficial ESPs."""
import argparse,csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_unofficial_release import read_records,reviewed_identity
from scripts.audit_issue8_unofficial_overlap import ARCHIVES

def read_locations(path):
    result={}
    with path.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            key=(row["effective_source"],row["record_type"].encode(),
                 int(row["raw_formid"],16),row["field"].encode(),
                 row.get("editor_id",""))
            if key in result:raise ValueError("Duplicate location "+repr(key))
            result[key]=row
    return result

def run(baseline, current, released, outdir):
    before=read_locations(baseline)
    after=read_locations(current)
    changed={}
    for key,n in after.items():
        old=before.get(key)
        if old is None:continue
        if n["obcjk_unicode_text"]!=old["obcjk_unicode_text"]:
            changed[key]=(old,n)
    by_key=defaultdict(list)
    for (source,kind,fid,field,edid),pair in changed.items():
        by_key[(source,kind,fid,field)].append((edid,pair))
    rows=[]
    for patch,(filename,digest) in ARCHIVES.items():
        path=released/filename
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError("ZIP hash")
        with ZipFile(path) as z, TemporaryDirectory() as tmp:
            for name in z.namelist():
                if not name.lower().endswith(".esp"):continue
                ep=Path(tmp)/Path(name).name;ep.write_bytes(z.read(name))
                records=read_records(ep)
                for (kind,fid),fields in records.items():
                    if kind==b"TES4":continue
                    origin=reviewed_identity(records,fid)
                    if not origin:continue
                    owner,base_fid=origin
                    editor=next((v.rstrip(b"\0").decode("ascii",errors="replace") for f,v in fields if f==b"EDID"),"")
                    for field in {f for f,v in fields}:
                        for edid,(old,new) in by_key.get((owner,kind,base_fid,field),()):
                            if edid and editor and edid!=editor:continue
                            vals=[v for f,v in fields if f==field]
                            expected_old=bytes.fromhex(old["obcjk_utf8_hex"])
                            expected_new=bytes.fromhex(new["obcjk_utf8_hex"])
                            for occur,actual in enumerate(vals):
                                status="old" if actual==expected_old else "new" if actual==expected_new else "other"
                                rows.append({"patch":patch,"esp":name,"record_type":kind.decode(),
                                  "formid":f"{fid:08X}","owner":owner,"base_formid":f"{base_fid:08X}",
                                  "field":field.decode(),"editor":editor,"occurrence":occur,"status":status,
                                  "old":old["obcjk_unicode_text"],"new":new["obcjk_unicode_text"],
                                  "actual":actual.rstrip(b"\0").decode("utf-8",errors="replace"),
                                  "actual_sha256":hashlib.sha256(actual).hexdigest()})
    outdir.mkdir(parents=True,exist_ok=True)
    with (outdir/"ISSUE8_UNOFFICIAL_LOCATION_OVERLAPS.csv").open("w",encoding="utf-8-sig",newline="") as f:
        cols=["patch","esp","record_type","formid","owner","base_formid","field","editor","occurrence","status","old","new","actual","actual_sha256"]
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
    result={"location_source_rows_changed":len(changed),
            "location_overrides":len(rows),
            "per_patch":{p:dict(Counter(r["status"] for r in rows if r["patch"]==p)) for p in ARCHIVES},
            "matches":rows}
    (outdir/"ISSUE8_UNOFFICIAL_LOCATION_SUMMARY.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"source_changed":len(changed),"overrides":len(rows),"per_patch":result["per_patch"]},ensure_ascii=False))
    return result

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,required=True)
 p.add_argument("--released",type=Path,required=True)
 p.add_argument("--outdir",type=Path,required=True)
 args=p.parse_args()
 run(args.baseline,ROOT/"canonical_locations_v2.csv",args.released,args.outdir)
