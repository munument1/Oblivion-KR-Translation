"""Translate three hash-pinned UOP gate scripts using fixed-size UTF-8 literals.

Only SCDA/SCTX payload bytes change; all metadata, instructions and offsets
are preserved. These are confirmed UOP omissions, not proof of the reporter's
unspecified Ayleid location or a fix for encoding failures in other mods.
"""
from __future__ import annotations
import hashlib
import re
import struct
from pathlib import Path
from build_vanilla_overlay import parse_subrecords, sha256_file

TRANSLATIONS = {
    ' This gate is opened remotely.': '장치로 여는 문입니다.',
    'You have opened a gate.': '문을 열었습니다.',
    'You may not use this switch at this time.': '지금은 조작할 수 없습니다.',
    'The gate has already been opened.': '이미 열린 문입니다.',
}
PINS = {
    ('Unofficial Oblivion Patch.esp', 0x0000CCD0): ('OblivionGateSwitch01MQ03Gates', '778779c98acbb8fcdb0a30619fa597e5af5d4add339c5255dedc27844f01d502'),
    ('Unofficial Oblivion Patch.esp', 0x000947B3): ('SewerVerticalGate01SCRIPT', '36ea9717db084e6208243fa5b45b1fbd5df41b0940049bd906f485f11bdc7032'),
    ('Unofficial Oblivion Patch.esp', 0x000C49FC): ('OblivionGateSwitch01', '97230965dd47766fe5afef4ac9227dc3038a943871020da6b77d94b25c3f44cb'),
}


def translate_body(body, edid, pin):
    if hashlib.sha256(body).hexdigest() != pin:
        raise ValueError('Gate script differs from the verified original')
    parts = list(parse_subrecords(body))
    if next((v.rstrip(b'\0').decode('ascii') for k, v, _ in parts if k == b'EDID'), None) != edid:
        raise ValueError('Gate script identity mismatch')
    fields = {k: v for k, v, _ in parts}
    if sum(k == b'SCDA' for k, _, _ in parts) != 1 or sum(k == b'SCTX' for k, _, _ in parts) != 1:
        raise ValueError('Expected one compiled script and one source script')
    lines = re.findall(rb'^\s*message(?:box)?\s+"([^"\r\n]+)"', fields[b'SCTX'], re.I | re.M)
    if (len(lines), len(set(lines))) not in ((1, 1), (3, 3)):
        raise ValueError('Unexpected gate message count')
    replacements = []
    for english in dict.fromkeys(lines):
        korean = TRANSLATIONS[english.decode('ascii')].encode('utf-8')
        if len(korean) > len(english):
            raise ValueError('Translation exceeds reserved literal length')
        replacements.append((english, korean.ljust(len(english), b' ')))
    output = bytearray(body)
    changes = []
    offset = 0
    for field, value, raw in parts:
        if field in (b'SCDA', b'SCTX'):
            for english, korean in replacements:
                if value.count(english) != lines.count(english):
                    raise ValueError('Literal count differs between script source and bytecode')
                for match in re.finditer(re.escape(english), value):
                    literal = match.start()
                    if field == b'SCDA' and (literal < 2 or struct.unpack_from('<H', value, literal - 2)[0] != len(english)):
                        raise ValueError('Compiled string length mismatch')
                    at = offset + len(raw) - len(value) + literal
                    output[at:at + len(english)] = korean
                    changes.append(dict(field=field.decode(), body_offset=at, bytes=len(english),
                                        english=english.decode(), korean=korean.rstrip().decode('utf-8')))
        offset += len(raw)
    restored = bytearray(output)
    for change in changes:
        at = change['body_offset']
        restored[at:at + change['bytes']] = change['english'].encode('ascii')
    if restored != body or len(output) != len(body):
        raise ValueError('Non-literal script bytes changed')
    return bytes(output), changes


def build(source, output, plugin=None):
    source, output = Path(source), Path(output)
    plugin = plugin or source.name
    pins = {fid: item for (name, fid), item in PINS.items() if name == plugin}
    if len(pins) != 3:
        raise ValueError('Expected three gate identities for supported plugin')
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError('Gate output must be new and separate from input')
    original = source.read_bytes()
    result = bytearray(original)
    reports = []
    seen = set()
    def walk(start, end):
        while start < end:
            if start + 20 > end:
                raise ValueError('Truncated record header')
            kind, size, flags, fid, _ = struct.unpack_from('<4sIIII', original, start)
            stop = start + size if kind == b'GRUP' else start + 20 + size
            if not start + 20 <= stop <= end:
                raise ValueError('Invalid record bounds')
            if kind == b'GRUP':
                walk(start + 20, stop)
            elif kind == b'SCPT' and fid in pins:
                if fid in seen or flags & 0x40000:
                    raise ValueError('Duplicate or compressed gate script')
                seen.add(fid)
                edid, pin = pins[fid]
                body, changes = translate_body(original[start + 20:stop], edid, pin)
                result[start + 20:stop] = body
                reports.append(dict(formid=f'{fid:08X}', edid=edid, body_offset=start + 20,
                                    original_body_sha256=pin, changes=changes))
            start = stop
        if start != end:
            raise ValueError('Record boundary mismatch')
    walk(0, len(original))
    if seen != pins.keys():
        raise ValueError('Missing gate scripts')
    # Independent reverse check covers the entire plugin, including all headers.
    reverse = bytearray(result)
    for report in reports:
        for change in report['changes']:
            at = report['body_offset'] + change['body_offset']
            reverse[at:at + change['bytes']] = change['english'].encode('ascii')
    if reverse != original or len(result) != len(original):
        raise ValueError('Plugin differs outside allowlisted literals')
    source_sha = hashlib.sha256(original).hexdigest()
    if sha256_file(source) != source_sha:
        raise ValueError('Source changed during build')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(result)
    output_sha = hashlib.sha256(result).hexdigest()
    if sha256_file(output) != output_sha:
        raise ValueError('Gate output checksum mismatch')
    return dict(source_sha256=source_sha, output_sha256=output_sha, scripts=reports,
                script_count=len(reports), display_strings=sum(len(r['changes']) // 2 for r in reports),
                file_size_unchanged=True, only_allowlisted_literal_bytes_changed=True,
                bytecode_lengths_and_control_flow_unchanged=True, runtime_verified=False)
