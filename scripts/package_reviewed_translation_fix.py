"""Refresh reviewed text from pinned public packages; verify every other subrecord."""
import argparse,hashlib,json,sys,tempfile
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_unofficial_release import read_records,reviewed_identity,rewrite
from build_vanilla_overlay import structure_signature
from unofficial_text_forwarding import load_text_forwarding
from package_obcjk_unofficial import PATCHES

BASELINES={
 'UOP':('UOP_KR_UTF8_obCJK_3.5.9a_KR1.10_20261023.zip','3546cd3ef189a8e596fa9eee8d4d7c91e377d8840fe0a7f4c35e9df01037f105'),
 'USIP':('USIP_KR_UTF8_obCJK_1.6.2_KR1.7_20261023.zip','fa4ceebb193e335ed2b0180a4e0b27628a21a75a8ad52a9334f0dcc1be294cf5'),
 'UODP':('UODP_KR_UTF8_obCJK_v27_KR1.9_20261023.zip','32f32ae24771eeceb0e4a8bb2d3966c5d59249c872e4e9448956ccde75e2bf2b')}
OUTPUTS={'UOP':'UOP_KR_UTF8_obCJK_3.5.9a_KR1.11_20261025.zip',
         'USIP':'USIP_KR_UTF8_obCJK_1.6.2_KR1.8_20261025.zip',
         'UODP':'UODP_KR_UTF8_obCJK_v27_KR1.10_20261025.zip'}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def package(label,source,output):
 if source.name!=BASELINES[label][0] or sha(source.read_bytes())!=BASELINES[label][1]:
  raise ValueError('Unexpected published baseline')
 table=load_text_forwarding(ROOT)
 output.mkdir(parents=True,exist_ok=True)
 destpath=output/OUTPUTS[label]
 report={'baseline_sha256':BASELINES[label][1],'plugins':{},'runtime_verified':False}
 with ZipFile(source) as old,tempfile.TemporaryDirectory() as temp:
  names={n for n in old.namelist() if n.endswith('.esp')}
  if names!=PATCHES[label] or old.testzip():raise ValueError('Unexpected baseline layout')
  validation=json.loads(old.read('validation.json'))
  for name,item in validation['plugins'].items():
   if sha(old.read(name))!=item['output_sha256']:raise ValueError('Baseline validation mismatch')
  updated_files={}
  for name in sorted(names):
   src,dest=Path(temp)/name,Path(temp)/('new-'+name)
   src.write_bytes(old.read(name));records=read_records(src);changes={};entries=[]
   for key,item in table.items():
    plugin,kind,fid,field,editor,occ=key;owner,basefid,source_sha,target,policy=item
    if plugin!=name or policy!='forward':continue
    fs=records[kind,fid]
    if reviewed_identity(records,fid)!=(owner,basefid):raise ValueError('Wrong master ownership')
    if next((v.rstrip(b'\0') for t,v in fs if t==b'EDID'),b'')!=editor:raise ValueError('Wrong editor identity')
    indices=[i for i,(t,_) in enumerate(fs) if t==field]
    if occ>=len(indices):raise ValueError('Unexpected field multiplicity')
    index=indices[occ];before=fs[index][1]
    if before!=target:
     changes.setdefault((kind,fid),{})[index]=(field,before,target)
     entries.append({'type':kind.decode(),'formid':f'{fid:08X}','field':field.decode(),'occurrence':occ,
                     'old_sha256':sha(before),'new_sha256':sha(target)})
   if rewrite(src,dest,changes)!=len(entries):raise ValueError('Applied count mismatch')
   if structure_signature(src)!=structure_signature(dest):raise ValueError('Structure or script changed')
   actual=read_records(dest)
   if actual.keys()!=records.keys():raise ValueError('Record set changed')
   for key,fs in records.items():
    expected=list(fs)
    for i,(tag,before,target) in changes.get(key,{}).items():
     if expected[i]!=(tag,before):raise ValueError('Input changed')
     expected[i]=(tag,target)
    if actual[key]!=expected:raise ValueError('Unselected field changed')
   if not entries and src.read_bytes()!=dest.read_bytes():raise ValueError('Unchanged file differs')
   updated_files[name]=dest
   validation['plugins'][name]['output_sha256']=sha(dest.read_bytes())
   report['plugins'][name]={'changed_fields':len(entries),'changes':entries,
       'output_sha256':sha(dest.read_bytes()),'unselected_fields_and_scripts_unchanged':True}
  validation['reviewed_latest_main_refresh']=report
  with ZipFile(destpath,'x',ZIP_DEFLATED,compresslevel=6) as z:
   for n in old.namelist():
    if n not in names|{'validation.json','SHA256SUMS.txt','README_KR.md'}:z.writestr(n,old.read(n))
   for n,p in updated_files.items():z.write(p,n)
   z.write(ROOT/'docs/unofficial'/f'{label}.md','README_KR.md')
   z.writestr('validation.json',json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
   z.writestr('SHA256SUMS.txt',''.join(f'{r["output_sha256"]}  {n}\n' for n,r in validation['plugins'].items()))
  with ZipFile(destpath) as z:
   if z.testzip():raise ValueError('Corrupt package')
   for n,item in validation['plugins'].items():
    if sha(z.read(n))!=item['output_sha256']:raise ValueError('Output checksum mismatch')
  digest=sha(destpath.read_bytes())
  destpath.with_suffix('.zip.sha256').write_text(f'{digest}  {destpath.name}\n',encoding='ascii')
  (output/(label+'_latest_main_refresh.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
  print(label,sum(r['changed_fields'] for r in report['plugins'].values()),digest)
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--baseline-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 for label,(name,_) in BASELINES.items():package(label,a.baseline_dir/name,a.output)
