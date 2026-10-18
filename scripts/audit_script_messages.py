"""Read-only inventory of Message/MessageBox literals in original and KR plugins.

Candidates include unused/debug scripts; inventory counts are not a count of
messages reachable in normal play. Run with --source Data --translated MOD
--output audit.json. No game bytecode or complete script sources are exported.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_vanilla_overlay import parse_subrecords


def scripts(path):
    data = path.read_bytes()
    def walk(start, end):
        while start < end:
            if start + 20 > end:
                raise ValueError('Truncated record header')
            kind, size, flags, fid, _ = struct.unpack_from('<4sIIII', data, start)
            stop = start + size if kind == b'GRUP' else start + 20 + size
            if not start + 20 <= stop <= end:
                raise ValueError('Invalid record bounds')
            if kind == b'GRUP':
                yield from walk(start + 20, stop)
            elif kind in (b'SCPT', b'INFO', b'QUST'):
                body = data[start + 20:stop]
                if flags & 0x40000:
                    size = struct.unpack_from('<I', body)[0]
                    body = zlib.decompress(body[4:])
                    if len(body) != size:
                        raise ValueError('Invalid decompressed size')
                yield (kind, fid), list(parse_subrecords(body))
            start = stop
    yield from walk(0, len(data))


def audit(source, translated):
    rows = []
    for path in sorted(source.iterdir()):
        if path.suffix.lower() not in ('.esm', '.esp') or not (translated / path.name).is_file():
            continue
        targets = dict(scripts(translated / path.name))
        for (kind, fid), fields in scripts(path):
            target = targets.get((kind, fid), [])
            source_compiled = [v for k, v, _ in fields if k == b'SCDA']
            target_compiled = [v for k, v, _ in target if k == b'SCDA']
            lines = [line.strip() for k, v, _ in fields if k == b'SCTX'
                     for line in v.decode('cp1252').splitlines()
                     if re.match(r'^\s*(messagebox|message)\b', line, re.I)]
            if not lines:
                continue
            literals = [text for line in lines for text in re.findall(r'"([^"\r\n]*)"', line)]
            remaining = [text for text in literals if text and
                         any(text.encode('cp1252') in v for v in target_compiled)]
            rows.append(dict(file=path.name, type=kind.decode(), formid=f'{fid:08X}',
                             edid=next((v.rstrip(b'\0').decode('cp1252') for k, v, _ in fields if k == b'EDID'), ''),
                             compiled_bytecode_unchanged=source_compiled == target_compiled,
                             literals=literals, remaining_english_literals=remaining))
    return dict(candidate_records=len(rows), record_types=dict(Counter(r['type'] for r in rows)),
                compiled_bytecode_unchanged=sum(r['compiled_bytecode_unchanged'] for r in rows),
                candidate_literal_occurrences=sum(len(r['literals']) for r in rows),
                remaining_english_occurrences=sum(len(r['remaining_english_literals']) for r in rows),
                includes_unused_and_debug_scripts=True, records=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--translated', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in args.source.iterdir()} | {p.resolve() for p in args.translated.iterdir()}:
        raise ValueError('Audit output must not overwrite an input file')
    report = audit(args.source, args.translated)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}, indent=2))
