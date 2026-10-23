"""Refresh audited translation fields of the hash-pinned v1.1.5 ESP packages.

This maintenance build requires no private game installation. It preserves the
released patch's gameplay fixes, scripts and every unselected subrecord. Normal
fresh builds use build_unofficial_release and the same forwarding table.
"""
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
from build_unofficial_release import read_records, reviewed_identity, rewrite
from build_vanilla_overlay import structure_signature
from unofficial_text_forwarding import load_text_forwarding
from package_obcjk_unofficial import PATCHES

BASELINES = {
    'UOP': ('UOP_KR_UTF8_obCJK_3.5.9a_KR1.8_20261021.zip',
            '95f05c3a26170346cc98f83666643a457305283ee66723e539e58d91ffe779a7'),
    'UODP': ('UODP_KR_UTF8_obCJK_v27_KR1.8_20261021.zip',
             'e0d0cb2f0bd85adda1ef02dff6dff7852e25fcae0c78fa051175464b92b408a2'),
    'USIP': ('USIP_KR_UTF8_obCJK_1.6.2_KR1.6_20261021.zip',
             '67839c02746600052a2409cd6b5980994793ff0c299df77baed64fb0d0b6bec9'),
}
OUTPUTS = {
    'UOP': 'UOP_KR_UTF8_obCJK_3.5.9a_KR1.9_20261023.zip',
    'UODP': 'UODP_KR_UTF8_obCJK_v27_KR1.9_20261023.zip',
    'USIP': 'USIP_KR_UTF8_obCJK_1.6.2_KR1.7_20261023.zip',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_manual_fixes():
    targets = {}
    with (ROOT / 'canonical_unofficial_translation_v2.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            key = (row['effective_source'], row['record_type'].encode(), int(row['raw_formid'],16), row['field'].encode(), row['editor_id'].encode(), int(row['occurrence']))
            targets[key] = row
    result = {}
    with (ROOT / 'unofficial_manual_fixes_v1.csv').open(encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream):
            key = (row['plugin'], row['record_type'].encode(), int(row['formid'],16), row['field'].encode(), row['editor_id'].encode(), int(row['occurrence']))
            target = targets[key]
            if hashlib.sha256(target['old_english'].encode('cp1252')+b'\0').hexdigest() != row['source_sha256']:
                raise ValueError(f'Changed manual source: {key}')
            result[key] = bytes.fromhex(target['obcjk_utf8_hex'])
    return result


def refresh(patch, source, output):
    if sha(source.read_bytes()) != BASELINES[patch][1]:
        raise ValueError('Unexpected v1.1.5 ZIP hash')
    forwarding = load_text_forwarding(ROOT)
    manual = load_manual_fixes()
    if set(manual) - set(forwarding):
        raise ValueError('Manual fixes lack audited ownership')
    audit = {'baseline_zip': source.name, 'baseline_sha256': BASELINES[patch][1],
             'method': 'audited translation-only refresh of published v1.1.5', 'plugins': {}}
    with tempfile.TemporaryDirectory() as temp, ZipFile(source) as archive:
        esp_names = {n for n in archive.namelist() if n.lower().endswith('.esp')}
        if esp_names != PATCHES[patch] or archive.testzip():
            raise ValueError('Unexpected baseline archive layout')
        old_validation = json.loads(archive.read('validation.json'))
        output.mkdir(parents=True, exist_ok=True)
        target = output / OUTPUTS[patch]
        with ZipFile(target, 'x', ZIP_DEFLATED, compresslevel=6) as dest:
            for name in sorted(esp_names):
                original = Path(temp) / name
                original.write_bytes(archive.read(name))
                if sha(original.read_bytes()) != old_validation[name]['output_sha256']:
                    raise ValueError(f'Baseline ESP validation mismatch: {name}')
                records = read_records(original)
                changes = {}
                entries = []
                for (plugin, kind, fid, field, editor, occurrence), item in forwarding.items():
                    if plugin != name:
                        continue
                    owner, base_fid, source_sha, new, policy = item
                    key = (kind, fid)
                    fields = records[key]
                    if reviewed_identity(records, fid) != (owner, base_fid):
                        raise ValueError(f'Wrong book owner: {name} {fid:08X}')
                    if next((v.rstrip(b'\0') for f, v in fields if f == b'EDID'), b'') != editor:
                        raise ValueError(f'Wrong book editor: {name} {fid:08X}')
                    indices = [i for i, (f, _) in enumerate(fields) if f == field]
                    if occurrence >= len(indices):
                        raise ValueError('Unexpected book field multiplicity')
                    index = indices[occurrence]
                    old = fields[index][1]
                    manual_key = (plugin, kind, fid, field, editor, occurrence)
                    if manual_key in manual:
                        new = manual[manual_key]
                        policy = 'manual'
                    if policy in ('forward', 'manual') and old != new:
                        changes.setdefault(key, {})[index] = (field, old, new)
                        entries.append({'record_type': kind.decode(), 'formid': f'{fid:08X}', 'field': field.decode(),
                                        'occurrence': occurrence, 'policy': policy,
                                        'editor_id': editor.decode(), 'old_sha256': sha(old),
                                        'new_sha256': sha(new), 'patch_source_sha256': source_sha})
                updated = Path(temp) / ('new-' + name)
                if rewrite(original, updated, changes) != len(entries):
                    raise ValueError('Applied count mismatch')
                if structure_signature(original) != structure_signature(updated):
                    raise ValueError('Record identity or script changed')
                actual = read_records(updated)
                for key, fields in records.items():
                    expected = list(fields)
                    for index, (field, old, new) in changes.get(key, {}).items():
                        if expected[index] != (field, old):
                            raise ValueError('Source changed during update')
                        expected[index] = (field, new)
                    if actual[key] != expected:
                        raise ValueError('Unselected subrecord changed')
                if not changes and updated.read_bytes() != original.read_bytes():
                    raise ValueError('Unchanged plugin bytes differ')
                audit['plugins'][name] = {
                    'baseline_sha256': sha(original.read_bytes()),
                    'output_sha256': sha(updated.read_bytes()),
                    'structure': structure_signature(updated), 'changes': entries,
                }
                dest.write(updated, name)
            dest.write(ROOT / 'docs' / 'unofficial' / f'{patch}.md', 'README_KR.md')
            dest.writestr('validation.json', json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
            dest.writestr('baseline_validation_v1.1.5.json', json.dumps(old_validation, indent=2) + '\n')
            dest.writestr('SHA256SUMS.txt', ''.join(
                f'{r["output_sha256"]}  {name}\n' for name, r in audit['plugins'].items()))
        expected_count = {'UOP':508,'USIP':92,'UODP':16}[patch]
        if sum(len(r['changes']) for r in audit['plugins'].values()) != expected_count:
            raise ValueError('Unexpected v1.1.6 change count')
        with ZipFile(target) as archive:
            if archive.testzip():
                raise ValueError('Output ZIP corrupt')
        digest = sha(target.read_bytes())
        target.with_suffix('.zip.sha256').write_text(f'{digest}  {target.name}\n', encoding='ascii')
        for name, report in audit['plugins'].items():
            print(name, len(report['changes']), report['output_sha256'])
        print(target, digest)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', choices=BASELINES, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    refresh(args.patch, args.source, args.output)
