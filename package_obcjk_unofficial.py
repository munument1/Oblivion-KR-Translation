"""Create one verified OBCJK UTF-8 ZIP per unofficial patch for Nexus uploads."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

OMIT = 'UOP Vampire Aging & Face Fix.esp'
PATCHES = {
    'UOP': {'Unofficial Oblivion Patch.esp', 'Oblivion Citadel Door Fix.esp'},
    'USIP': {'Unofficial Shivering Isles Patch.esp'},
    'UODP': {f'{name} - Unofficial Patch.esp' for name in (
        'DLCBattlehornCastle', 'DLCFrostcrag', 'DLCHorseArmor', 'DLCMehrunesRazor',
        'DLCOrrery', 'DLCSpellTomes', 'DLCThievesDen', 'DLCVileLair', 'Knights'
    )} | {'DLCThievesDen - Unofficial Patch - SSSB.esp'},
}


def load_validation(folder: Path):
    release = folder.parent / 'release_audit.json'
    if not release.is_file():
        raise FileNotFoundError(release)
    raw = json.loads(release.read_text(encoding='utf-8'))
    data = {}
    for path in folder.glob('*.esp'):
        if path.name not in raw:
            raise ValueError(f'Missing release audit entry: {path.name}')
        source = raw[path.name]
        data[path.name] = {
            'original_sha256': source['source_sha256'],
            'output_sha256': source['output_sha256'],
            'changes': source.get('translated_fields', 0),
            'checks': {
                'translated_fields': source.get('translated_fields', 0),
                'structure': source.get('structure'),
                'text_backend': source.get('text_backend'),
                **({'shrine_messages': source['shrine_messages']} if 'shrine_messages' in source else {}),
                **({'gate_messages': source['gate_messages']} if 'gate_messages' in source else {}),
            },
            'locations': {
                'base': source.get('canonical_base_location', 0),
                'direct': source.get('canonical_direct_location', 0),
                'patch': source.get('canonical_patch_location', 0),
            },
        }
    return data


def package(inputs, output, patch):
    expected = PATCHES[patch]
    sources, reports = {}, {}
    for folder in inputs:
        data = load_validation(folder)
        for name, report in data.items():
            path = folder / name
            if path.suffix.lower() != '.esp' or name in sources:
                raise ValueError('Expected unique unofficial ESP files')
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != report['output_sha256']:
                raise ValueError(f'OBCJK UTF-8 source checksum mismatch: {name}')
            sources[name] = path
            reports[name] = report

    if OMIT in sources and reports[OMIT]['changes']:
        raise ValueError('The optional Vampire fix should not contain translation changes')
    if not expected <= sources.keys():
        raise ValueError(f'Missing {patch} ESPs: {sorted(expected - sources.keys())}')
    unknown = sources.keys() - set().union(*PATCHES.values()) - {OMIT}
    if unknown:
        raise ValueError(f'Unexpected unofficial ESPs: {sorted(unknown)}')

    entries, audit = [], {}
    for name in sorted(expected):
        path = sources[name]
        report = reports[name]
        target = name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append((path, target))
        audit[name] = {
            'archive_path': target,
            'original_sha256': report['original_sha256'],
            'output_sha256': digest,
            'validation': report['checks'],
            'location_forwarding': report['locations'],
        }

    if {path.name for path, _ in entries} != expected:
        raise ValueError(f'Expected only {patch} translated ESPs')

    output.parent.mkdir(parents=True, exist_ok=True)
    readme = Path(__file__).resolve().parent / 'docs/unofficial' / f'{patch}.md'
    with output.open('xb') as stream, ZipFile(stream, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in entries:
            archive.write(path, name)
        archive.write(readme, 'README_KR.md')
        archive.writestr('validation.json', json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
        archive.writestr('SHA256SUMS.txt', ''.join(
            f'{audit[path.name]["output_sha256"]}  {name}\n' for path, name in entries))

    with ZipFile(output) as archive:
        if any('/' in n for n in archive.namelist() if n.lower().endswith('.esp')):
            raise ValueError('Every ESP must be at the archive root')
        if archive.testzip():
            raise ValueError('ZIP integrity check failed')
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + '.sha256').write_text(
        f'{sha}  {output.name}\n', encoding='ascii')
    print(output.resolve(), output.stat().st_size, sha)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--patch', choices=PATCHES, required=True)
    args = parser.parse_args()
    package(args.input_dir, args.output, args.patch)
