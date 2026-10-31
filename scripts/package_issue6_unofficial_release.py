"""Rebase issue #6 corrections onto the SHA-pinned public KR packages.

Do not distribute a fresh source-only build directly: that loses earlier
reviewed translations. Only changed Korean output and precisely identified
script literal fields are selected from the independently validated build.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_unofficial_release import read_records, rewrite, localizable_field
from package_obcjk_unofficial import PATCHES
from issue6_unofficial_menu_scripts import PINS

BASELINE = {
    'UOP': ('UOP_KR_UTF8_obCJK_3.5.9a_KR1.11_20261025.zip',
            'ccc8adca3ef43f29108e31ba5c4cbd3d1607317170fc9b7c8b178f4fe9251abc'),
    'USIP': ('USIP_KR_UTF8_obCJK_1.6.2_KR1.8_20261025.zip',
             '0433ab4d5287f20a666d17c2bbbb245b8504b646bd125f670a0e8b2c8526ab0e')
}
FOLDERS = {'UOP': 'Unofficial Oblivion Patch-KR', 'USIP': 'Unofficial Shivering Isles Patch-KR'}
OUTPUT = {
    'UOP': 'UOP_KR_UTF8_obCJK_3.5.9a_KR1.12_20261031.zip',
    'USIP': 'USIP_KR_UTF8_obCJK_1.6.2_KR1.9_20261031.zip',
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def is_korean(value):
    try:
        decoded = value.rstrip(b'\0').decode('utf-8')
    except UnicodeError:
        return False
    return any('\uac00' <= c <= '\ud7a3' for c in decoded)


def package(label, baseline_dir, fresh_dir, output_dir):
    old_name, old_hash = BASELINE[label]
    source = baseline_dir / old_name
    assert source.is_file() and sha(source.read_bytes()) == old_hash, 'Public baseline mismatch'
    output = output_dir / OUTPUT[label]
    assert not output.exists(), 'Never overwrite a public package'
    report = {'public_baseline': old_name, 'public_baseline_sha256': old_hash,
              'fresh_build': str(fresh_dir), 'files': {}, 'runtime_verified': False}
    with ZipFile(source) as z, tempfile.TemporaryDirectory() as t:
        assert z.testzip() is None
        names = {n for n in z.namelist() if n.endswith('.esp')}
        assert names == PATCHES[label], (label, names)
        validation = json.loads(z.read('validation.json'))
        files = {}
        for name in sorted(names):
            original = Path(t) / name
            original.write_bytes(z.read(name))
            assert sha(original.read_bytes()) == validation['plugins'][name]['output_sha256']
            fresh = fresh_dir / FOLDERS[label] / name
            previous_records, current_records = read_records(original), read_records(fresh)
            assert previous_records.keys() == current_records.keys(), 'Record set mismatch'
            changes, entries = {}, []
            for rec, fields in previous_records.items():
                other = current_records[rec]
                assert len(fields) == len(other), 'Subrecord count mismatch'
                for ordinal, ((tag, old), (new_tag, new)) in enumerate(zip(fields, other)):
                    assert tag == new_tag, 'Subrecord tag mismatch'
                    if old == new:
                        continue
                    if localizable_field(rec[0], tag):
                        # Previous Korean is never replaced by English.
                        if not is_korean(new):
                            assert is_korean(old), ('Unexpected non-Korean text change', name, rec, tag)
                            continue
                        mode = 'reviewed_korean_refinement'
                    else:
                        script = PINS.get(name)
                        assert script is not None and rec == (b'SCPT', script[0]) and tag in (b'SCDA', b'SCTX'), (
                            'Unapproved nonlocalizable change', name, rec, tag)
                        assert len(old) == len(new), 'Compiled script sizes changed'
                        mode = 'menu_literal'
                    changes.setdefault(rec, {})[ordinal] = (tag, old, new)
                    entries.append({'kind':rec[0].decode(), 'formid':f'{rec[1]:08X}',
                                    'field':tag.decode(), 'ordinal':ordinal, 'mode':mode,
                                    'old_sha256':sha(old), 'new_sha256':sha(new)})
            destination = Path(t) / ('release-' + name)
            assert rewrite(original, destination, changes) == len(entries)
            output_records = read_records(destination)
            for key, fields in previous_records.items():
                expected = list(fields)
                for i, (tag, before, after) in changes.get(key, {}).items():
                    assert expected[i] == (tag, before)
                    expected[i] = (tag, after)
                assert output_records[key] == expected, ('Unexpected edit', name, key)
            if not entries:
                assert destination.read_bytes() == original.read_bytes()
            files[name] = destination
            validation['plugins'][name]['output_sha256'] = sha(destination.read_bytes())
            report['files'][name] = {'changes':entries, 'output_sha256':sha(destination.read_bytes())}
            print(label, name, 'intentional changes', len(entries), flush=True)

        validation['issue6_verified_rebase'] = report
        output_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, 'x', ZIP_DEFLATED, compresslevel=6) as out:
            for n in z.namelist():
                if n in names | {'validation.json', 'SHA256SUMS.txt', 'README_KR.md'}:
                    continue
                out.writestr(n, z.read(n))
            for n in sorted(files):
                out.write(files[n], n)
            out.write(ROOT / 'docs' / 'unofficial' / f'{label}.md', 'README_KR.md')
            out.writestr('validation.json', json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
            out.writestr('SHA256SUMS.txt', ''.join(
                f"{validation['plugins'][n]['output_sha256']}  {n}\n" for n in sorted(files)))
        with ZipFile(output) as check:
            assert check.testzip() is None
            assert {n for n in check.namelist() if n.endswith('.esp')} == PATCHES[label]
            for n in files:
                assert sha(check.read(n)) == validation['plugins'][n]['output_sha256']
        digest = sha(output.read_bytes())
        output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')
        (output_dir / (label + '_issue6_rebase_audit.json')).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Release package:', output, output.stat().st_size, digest)
    return report

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--baseline-dir', required=True, type=Path)
    p.add_argument('--fresh-dir', required=True, type=Path)
    p.add_argument('--output-dir', required=True, type=Path)
    args = p.parse_args()
    for label in BASELINE:
        package(label, args.baseline_dir, args.fresh_dir, args.output_dir)
