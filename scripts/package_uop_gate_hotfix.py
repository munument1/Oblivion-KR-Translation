"""Build the gate-only hotfix from the exact published v1.1.6 UOP package."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_gate_messages import build
from package_obcjk_unofficial import PATCHES

BASELINE_SHA256='4c7c63f73cb547738a1c62b41159c37a82a7c3077a2daa4052391a975440bc74'
OUTPUT='UOP_KR_UTF8_obCJK_3.5.9a_KR1.10_20261023.zip'
PLUGIN='Unofficial Oblivion Patch.esp'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def package(source,folder):
    source,folder=Path(source),Path(folder)
    raw=source.read_bytes()
    if sha(raw)!=BASELINE_SHA256:
        raise ValueError('Unrecognized baseline ZIP')
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/OUTPUT
    with ZipFile(source) as old, tempfile.TemporaryDirectory() as temp:
        if old.testzip() or {n for n in old.namelist() if n.endswith('.esp')}!=PATCHES['UOP']:
            raise ValueError('Unexpected baseline layout')
        validation=json.loads(old.read('validation.json'))
        for name,item in validation['plugins'].items():
            if sha(old.read(name))!=item['output_sha256']:
                raise ValueError('Baseline ESP checksum mismatch')
        original=Path(temp)/PLUGIN
        original.write_bytes(old.read(PLUGIN))
        updated=Path(temp)/'updated.esp'
        report=build(original,updated,PLUGIN)
        if report['script_count']!=3 or report['display_strings']!=7:
            raise ValueError('Incomplete gate translation')
        validation['plugins'][PLUGIN]['output_sha256']=report['output_sha256']
        validation['plugins'][PLUGIN]['gate_messages']=report
        # The old structure hash includes bytecode; retain it only as baseline
        # provenance, never label it as the new script signature.
        validation['plugins'][PLUGIN]['baseline_structure_v1.1.6']=validation['plugins'][PLUGIN].pop('structure')
        validation['gate_hotfix']={'baseline_zip_sha256':BASELINE_SHA256,
                                  'only_allowlisted_literal_bytes_changed':True}
        with output.open('xb') as stream, ZipFile(stream,'w',ZIP_DEFLATED,compresslevel=6) as dest:
            for name in old.namelist():
                if name not in {PLUGIN,'validation.json','SHA256SUMS.txt','README_KR.md'}:
                    dest.writestr(name,old.read(name))
            dest.write(updated,PLUGIN)
            dest.write(ROOT/'docs/unofficial/UOP.md','README_KR.md')
            dest.writestr('validation.json',json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
            dest.writestr('gate_messages_validation.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            dest.writestr('SHA256SUMS.txt',''.join(f'{r["output_sha256"]}  {n}\n' for n,r in validation['plugins'].items()))
        with ZipFile(output) as dest:
            if dest.testzip():
                raise ValueError('Corrupt hotfix ZIP')
            for name in old.namelist():
                if name not in {PLUGIN,'validation.json','SHA256SUMS.txt','README_KR.md'} and dest.read(name)!=old.read(name):
                    raise ValueError('Unselected archive entry changed')
            for name,r in validation['plugins'].items():
                if sha(dest.read(name))!=r['output_sha256']:
                    raise ValueError('Packaged ESP checksum mismatch')
        digest=sha(output.read_bytes())
        output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n',encoding='ascii')
        (folder/'UOP_gate_messages_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(output.name,digest)
        return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    package(a.source,a.output)
