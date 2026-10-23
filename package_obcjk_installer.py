"""Package the UTF-8 installer, licenses, runtime provenance and instructions."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from obcjk_fonts import BUNDLE, bundle_manifest
from obcjk_runtime import BUNDLE as RUNTIME_BUNDLE, bundle_manifest as runtime_manifest

ROOT = Path(__file__).resolve().parent


def package(exe, output, version='1.1.7'):
    bundle_manifest()
    runtime_manifest()
    exe, output = Path(exe), Path(output)
    if not exe.is_file() or exe.read_bytes()[:2] != b'MZ':
        raise ValueError('Built Windows installer EXE required')
    files = [(exe, 'OblivionKRBuilder.exe'),
             (ROOT / 'install.bat', 'install.bat'),
             (ROOT / 'README.md', 'README.md'),
             (ROOT / f'release_notes_v{version}.md', 'CHANGELOG.md'),
             (BUNDLE / 'manifest.json', 'font_sources.json')]
    files += [(RUNTIME_BUNDLE / 'manifest.json', 'obcjk_runtime/manifest.json'),
              (RUNTIME_BUNDLE / 'NOTICE_KO.txt', 'obcjk_runtime/NOTICE_KO.txt')]
    files += [(p, 'obcjk_runtime/source_changes/' + p.name)
              for p in sorted((RUNTIME_BUNDLE / 'source_changes').iterdir()) if p.is_file()]
    files += [(p, 'licenses/' + p.name) for p in sorted((BUNDLE / 'licenses').iterdir()) if p.is_file()]
    for p, _ in files:
        if not p.is_file():
            raise FileNotFoundError(p)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream, ZipFile(stream, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in files:
            archive.write(path, name)
        archive.writestr('SHA256SUMS.txt', ''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}\n' for p, name in files))
    with ZipFile(output) as archive:
        if archive.testzip() or any(Path(n).suffix.lower() in {'.esm', '.esp', '.dll'} for n in archive.namelist()):
            raise ValueError('Installer package validation failed')
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + '.sha256').write_text(
        f'{sha}  {output.name}\n', encoding='ascii')
    print(output.resolve(), output.stat().st_size, sha)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', default='1.1.7')
    args = parser.parse_args()
    package(args.exe, args.output, args.version)
