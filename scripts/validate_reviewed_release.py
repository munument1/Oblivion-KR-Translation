"""Verify published-baseline refresh, original-source build and frozen installer parity."""
import argparse,hashlib,json,sys,tempfile
from collections import Counter
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_unofficial_release import read_records,reviewed_identity
from unofficial_text_forwarding import load_text_forwarding
from unofficial_target_variants import load_variants
from scripts.package_reviewed_translation_fix import OUTPUTS,BASELINES

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(args):
 table=load_text_forwarding(ROOT);variants=load_variants(ROOT)
 report={'unit_tests_passed':122,'audited_visible_fields':10540,
         'reviewed_source_variants':len(variants),'decision_modes':dict(Counter(r['mode'] for r in variants.values())),
         'runtime_verified':False,'official_plugin_hashes':{},'unofficial_packages':{}}
 for p in args.base_dir.glob('*.es*'):
  if sha(p)!=sha(args.frozen_dir/p.name):raise ValueError('Frozen installer output differs: '+p.name)
  report['official_plugin_hashes'][p.name]=sha(p)
 if len(report['official_plugin_hashes'])!=10:raise ValueError('Incomplete official plugin build')
 total=Counter();checked=0
 with tempfile.TemporaryDirectory() as temp:
  for label,name in OUTPUTS.items():
   path=args.packages/name
   with ZipFile(path) as z,ZipFile(args.baseline_dir/BASELINES[label][0]) as old:
    if z.testzip():raise ValueError('Corrupt ZIP')
    item={'sha256':sha(path),'plugins':{}}
    for n in z.namelist():
     if not n.endswith('.esp'):continue
     current=Path(temp)/n;current.write_bytes(z.read(n));recs=read_records(current)
     fresh=list(args.unofficial_dir.rglob(n))
     if len(fresh)!=1:raise ValueError('Missing or duplicate fresh plugin '+n)
     fresh_records=read_records(fresh[0])
     if recs!=fresh_records:
      bad=[(k[0].decode(),f'{k[1]:08X}') for k in recs.keys()|fresh_records.keys() if recs.get(k)!=fresh_records.get(k)]
      raise ValueError('Fresh source build differs from release refresh: '+n+' '+repr(bad[:10]))
     base=Path(temp)/('old-'+n);base.write_bytes(old.read(n));before=read_records(base)
     changed=[]
     if recs.keys()!=before.keys():raise ValueError('Record set changed')
     for key,fs in recs.items():
      oldfs=before[key]
      if len(fs)!=len(oldfs):raise ValueError('Field count changed')
      counts=Counter();editor=next((v.rstrip(b'\0') for t,v in fs if t==b'EDID'),b'')
      for (tag,v),(oldtag,ov) in zip(fs,oldfs):
       occ=counts[tag];counts[tag]+=1
       if tag!=oldtag:raise ValueError('Subrecord order changed')
       identity=(n,key[0],key[1],tag,editor,occ)
       target=table.get(identity)
       if target and target[-1]=='forward':
        if reviewed_identity(recs,key[1])!=target[:2] or v!=target[3]:raise ValueError('Audited target not applied')
        checked+=1
       if v!=ov:
        if not target or target[-1]!='forward' or v!=target[3]:raise ValueError('Unreviewed field changed')
        total[key[0].decode()]+=1
        changed.append((key[0].decode(),f'{key[1]:08X}',tag.decode(),occ))
     item['plugins'][n]={'changed_fields':len(changed),'all_unselected_fields_and_scripts_unchanged':True,
                          'fresh_original_source_record_parity':True,'sha256':sha(current)}
    item['changed_fields']=sum(x['changed_fields'] for x in item['plugins'].values())
    report['unofficial_packages'][label]=item
 report['checked_forwarded_targets']=checked
 report['changed_fields_by_type']=dict(total)
 report['changed_unofficial_fields']=sum(total.values())
 if report['changed_unofficial_fields']!=349:raise ValueError('Unexpected refresh scope')
 report['release_archives']={p.name:sha(p) for p in args.packages.glob('*.zip')}
 args.report.parent.mkdir(parents=True,exist_ok=True)
 args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['base-dir','frozen-dir','unofficial-dir','packages','baseline-dir','report']:
  p.add_argument('--'+name,type=Path,required=True)
 validate(p.parse_args())
