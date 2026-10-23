"""Verify fresh English-field replay agrees with the release refresh output.

This replays audited English text fields on a published binary fixture; it does
not pretend that the fixture is a full original English game installation.
"""
import argparse,csv,json,zipfile,tempfile,sys
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_unofficial_release import collect_changes,read_records,rewrite,load_patch_canonical
from unofficial_text_forwarding import load_text_forwarding
from uop_book_restoration import load_restorations
root=ROOT;t=load_text_forwarding(root);patch=load_patch_canonical(root/'canonical_unofficial_translation_v2.csv');locations=load_patch_canonical(root/'canonical_unofficial_locations_v2.csv');direct=load_patch_canonical(root/'canonical_locations_v2.csv')
books=load_restorations(root/'uop_book_body_restore_v1.csv',root/'canonical_translation_v2.csv');books.update(load_restorations(root/'uop_book_source_forward_v1.csv',root/'canonical_translation_v2.csv',expected_count=1))
sources={}
for f in ['canonical_unofficial_translation_v2.csv','canonical_unofficial_locations_v2.csv','canonical_locations_v2.csv','unofficial_extra_sources_v1.csv']:
 for row in csv.DictReader(open(root/f,encoding='utf-8-sig',newline='')):
  k=(row['effective_source'],row['record_type'].encode(),int(row['raw_formid'],16),row['field'].encode(),int(row.get('occurrence') or 0))
  sources.setdefault(k,row['old_english'].encode('cp1252')+b'\0')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=Path,required=True)
parser.add_argument('--release',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
temporary=tempfile.TemporaryDirectory()
folder=Path(temporary.name);total=Counter()
for label in ['UOP','USIP','UODP']:
 from scripts.release_unofficial_sync import OUTPUTS
 z=zipfile.ZipFile(args.release/OUTPUTS[label])
 for name in z.namelist():
  if not name.endswith('.esp'):continue
  baseline=args.baseline/name;records=read_records(baseline); reverse={}
  for (plugin,kind,fid,field,occ),raw in sources.items():
   if plugin!=name:continue
   values=records[kind,fid];indices=[i for i,(f,_) in enumerate(values) if f==field];index=indices[occ];old=values[index][1]
   if old!=raw:reverse.setdefault((kind,fid),{})[index]=(field,old,raw)
  eng=folder/name;rewrite(baseline,eng,reverse)
  changes,_=collect_changes(eng,baseline,patch_table=patch,location_table=direct,patch_location_table=locations,book_restorations=books,text_forwarding=t)
  out=folder/('out-'+name);rewrite(eng,out,changes);actual=read_records(out)
  expected_file=folder/('expected-'+name);expected_file.write_bytes(z.read(name));expected=read_records(expected_file)
  for key,item in t.items():
   plugin,kind,fid,field,edid,occ=key
   if plugin!=name:continue
   a=[v for f,v in actual[kind,fid] if f==field][occ];b=[v for f,v in expected[kind,fid] if f==field][occ]
   if a!=b:raise ValueError((key,a[:100],b[:100]))
   total[name]+=1
print('Fresh source-field replay and release-refresh paths agree:',dict(total), 'TOTAL',sum(total.values()))

args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps({'passed':True,'compared_fields':sum(total.values()),'per_plugin':dict(total),'method':'fresh audited English-field replay vs published-baseline refresh'},indent=2)+'\n')
temporary.cleanup()
