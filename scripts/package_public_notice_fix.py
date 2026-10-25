"""Refresh one BOOK/DESC in the pinned current UOP package; preserve all else."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_unofficial_release import read_records, rewrite
from build_vanilla_overlay import structure_signature
from package_obcjk_unofficial import PATCHES

PIN = '3546cd3ef189a8e596fa9eee8d4d7c91e377d8840fe0a7f4c35e9df01037f105'
PLUGIN = 'Unofficial Oblivion Patch.esp'
OUTPUT = 'UOP_KR_UTF8_obCJK_3.5.9a_KR1.11_20261025.zip'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def package(source, output):
    if sha(source.read_bytes()) != PIN:
        raise ValueError('Unexpected current UOP ZIP')
    with (ROOT/'canonical_unofficial_translation_v2.csv').open(encoding='utf-8-sig',newline='') as f:
        rows = [r for r in csv.DictReader(f) if (r['effective_source'],r['record_type'],r['raw_formid'],r['field'])
                == (PLUGIN,'BOOK','00071D50','DESC')]
    if len(rows)!=1:
        raise ValueError('Expected exactly one canonical notice')
    target = bytes.fromhex(rows[0]['obcjk_utf8_hex'])
    if b'<br>' in target.lower() or b'\r\n\r\n' not in target:
        raise ValueError('Expected plain text notice with real line breaks')
    with ZipFile(source) as old, tempfile.TemporaryDirectory() as temp:
        if old.testzip() or {n for n in old.namelist() if n.endswith('.esp')}!=PATCHES['UOP']:
            raise ValueError('Unexpected baseline archive')
        validation = json.loads(old.read('validation.json'))
        for name,item in validation['plugins'].items():
            if sha(old.read(name))!=item['output_sha256']:
                raise ValueError('Baseline ESP checksum mismatch')
        original,updated = Path(temp)/PLUGIN,Path(temp)/'updated.esp'
        original.write_bytes(old.read(PLUGIN))
        records=read_records(original)
        key=(b'BOOK',0x71D50)
        fields=records[key]
        if next(v for t,v in fields if t==b'EDID')!=b'DarkClaudiusHouseNote\0':
            raise ValueError('Unexpected notice identity')
        indices=[i for i,(t,_) in enumerate(fields) if t==b'DESC']
        if len(indices)!=1:
            raise ValueError('Unexpected notice multiplicity')
        index=indices[0];before=fields[index][1]
        if not before.startswith('공고:<br>'.encode()):
            raise ValueError('Unexpected previous notice')
        changes={key:{index:(b'DESC',before,target)}}
        if rewrite(original,updated,changes)!=1 or structure_signature(original)!=structure_signature(updated):
            raise ValueError('Unexpected structure or script change')
        actual=read_records(updated)
        if actual.keys()!=records.keys():
            raise ValueError('Record identity changed')
        for identity,fs in records.items():
            expected=list(fs)
            if identity==key:
                expected[index]=(b'DESC',target)
            if actual[identity]!=expected:
                raise ValueError('Unselected subrecord changed')
        report={'baseline_zip_sha256':PIN,'record':'BOOK 00071D50','field':'DESC',
                'changed_fields':1,'old_field_sha256':sha(before),'new_field_sha256':sha(target),
                'all_other_subrecords_and_scripts_unchanged':True,'runtime_verified':False}
        validation['plugins'][PLUGIN]['output_sha256']=sha(updated.read_bytes())
        validation['public_notice_fix']=report
        output.mkdir(parents=True,exist_ok=True)
        destpath=output/OUTPUT
        with ZipFile(destpath,'x',ZIP_DEFLATED,compresslevel=6) as dest:
            for name in old.namelist():
                if name not in (PLUGIN,'validation.json','SHA256SUMS.txt','README_KR.md'):
                    dest.writestr(name,old.read(name))
            dest.write(updated,PLUGIN)
            dest.write(ROOT/'docs/unofficial/UOP.md','README_KR.md')
            dest.writestr('validation.json',json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
            dest.writestr('SHA256SUMS.txt',''.join(f'{r["output_sha256"]}  {n}\n' for n,r in validation['plugins'].items()))
        with ZipFile(destpath) as archive:
            if archive.testzip():
                raise ValueError('Corrupt output ZIP')
            for name in old.namelist():
                if name not in (PLUGIN,'validation.json','SHA256SUMS.txt','README_KR.md') and archive.read(name)!=old.read(name):
                    raise ValueError('Unselected archive entry changed')
            for name,item in validation['plugins'].items():
                if sha(archive.read(name))!=item['output_sha256']:
                    raise ValueError('Output ESP checksum mismatch')
        destpath.with_suffix('.zip.sha256').write_text(f'{sha(destpath.read_bytes())}  {destpath.name}\n',encoding='ascii')
        (output/'Public_notice_fix_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print(destpath,sha(destpath.read_bytes()))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    package(args.source,args.output)
