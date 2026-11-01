"""One FULL-only correction on the published UOP KR1.13, with full field parity."""
from pathlib import Path
import sys,json,hashlib,tempfile,zipfile,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_unofficial_release import read_records,rewrite
from build_vanilla_overlay import structure_signature
BASE='5fb22fb624ec19cd2b1f4cee585298abc5b514c078cd284a7a59d63da95e2e3a'
def sha(b):return hashlib.sha256(b).hexdigest()
def package(source,output):
 assert sha(source.read_bytes())==BASE
 with zipfile.ZipFile(source) as z,tempfile.TemporaryDirectory() as td:
  assert z.testzip() is None
  name='Unofficial Oblivion Patch.esp';old=Path(td)/'old.esp';old.write_bytes(z.read(name));rs=read_records(old)
  key=(b'SPEL',0x84B17);fs=rs[key];positions=[i for i,(k,v) in enumerate(fs) if k==b'FULL'];assert len(positions)==1
  i=positions[0];assert fs[i]==(b'FULL','은밀'.encode()+b'\0')
  changes={key:{i:(b'FULL',fs[i][1],'침묵'.encode()+b'\0')}}
  new=Path(td)/'new.esp';assert rewrite(old,new,changes)==1
  assert structure_signature(old)==structure_signature(new)
  nr=read_records(new);assert rs.keys()==nr.keys()
  for k,values in rs.items():
   expected=list(values)
   if k==key:expected[i]=(b'FULL','침묵'.encode()+b'\0')
   assert nr[k]==expected
  qa={'baseline_zip_sha256':BASE,'esp_before':sha(old.read_bytes()),'esp_after':sha(new.read_bytes()),'changed_fields':1,'record':'SPEL 00084B17 FULL','all_unselected_fields_unchanged':True,'gameplay_tested':False}
  with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
   for n in z.namelist():
    if n==name:out.writestr(n,new.read_bytes())
    elif n=='SHA256SUMS.txt':
     out.writestr(n,z.read(n).replace(qa['esp_before'].encode(),qa['esp_after'].encode()))
    else:out.writestr(n,z.read(n))
   out.writestr('KR1.14-verification.json',json.dumps(qa,indent=2))
   out.writestr('KR1.14-CHANGES.txt','UOP KR1.14: Silence spell 00084B17 renamed to 침묵. Only one FULL field changed from KR1.13; previous validation.json describes the preserved KR1.13 baseline.\n')
  with zipfile.ZipFile(output) as out:
   assert out.testzip() is None
   for n in z.namelist():
    if n not in (name,'SHA256SUMS.txt'):assert z.read(n)==out.read(n)
 qa['output_zip_sha256']=sha(output.read_bytes())
 output.with_suffix('.zip.sha256').write_text(qa['output_zip_sha256']+'  '+output.name+'\n',encoding='ascii')
 output.with_suffix('.verification.json').write_text(json.dumps(qa,indent=2),encoding='utf8')
 print(json.dumps(qa,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();package(a.source,a.output)
