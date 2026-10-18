"""Translate all nine wayshrines in vanilla and Knights, without resizing bytecode.

Pin each full SCPT body and replace only matched SCDA/SCTX literals. UTF-8
payloads are padded to their original byte lengths so all instruction sizes,
jumps, SCHR metadata, reference indices and record/container sizes stay intact.
"""
from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path

from build_vanilla_overlay import parse_subrecords, sha256_file

TRANSLATIONS = {
    'The gods are not mocked! They require an honest heart, not one hidden behind a false face.':
        '신을 기만하지 마라! 거짓 얼굴 뒤에 숨지 말고 참된 마음으로 오라!',
    'Protect the weak. Pray at my chapel altars to receive my blessings.':
        '약자를 지켜라. 성당 제단에 빌어 축복받으라.',
    "Continue your penance to earn the gods' forgiveness.":
        '신의 용서를 구하며 참회를 계속하라.',
    "Rejoice! You've completed the Pilgrimage of the Nine Wayshrines, and gained the new Power of Pilgrim's Grace.":
        '기뻐하라! 아홉 성소 순례를 마쳐 새 능력, 순례자의 은총을 얻었노라.',
    "Rejoice! You've completed the Pilgrimage of the Nine Wayshrines, and your sins have been washed clean!":
        '기뻐하라! 아홉 성소 순례를 마쳐 죄를 씻었노라!',
    'Honor your body and spirit. Pray at my chapel altars to receive my blessings.':
        '몸과 영혼을 존중하라. 성당 제단에 빌어 축복받으라.',
    'Love beauty and honor its mysteries. Pray at my chapel altars to receive my blessings.':
        '아름다움과 그 신비를 경애하라. 성당 제단에 빌어 축복받으라.',
    'Honor the Nine and do your duty. Pray at my chapel altars to receive my blessings.':
        '아홉 신을 섬겨 본분을 다하라. 성당 제단에 빌어 축복받으라.',
    'Be strong for war and fight evil. Pray at my chapel altars to receive my blessings.':
        '강해져 악과 싸워라. 성당 제단에 빌어 축복받으라.',
    'Honest labor earns its own reward. Pray at my chapel altars to receive my blessings.':
        '정직한 노동은 보상받으리라. 성당 제단에 빌어 축복받으라.',
    "Go carefully upon Nature's path. Pray at my chapel altars to receive my blessings.":
        '자연의 길을 신중히 걸어라. 성당 제단에 빌어 축복받으라.',
    'Know the truth. Observe the law. Pray at my chapel altars to receive my blessings.':
        '진리를 알고 법을 지켜라. 성당 제단에 빌어 축복받으라.',
    'Be humble and live in peace. Pray at my chapel altars to receive my blessings.':
        '겸손히 평화롭게 살라. 성당 제단에 빌어 축복받으라.',
    'Seek greater fame to be judged worthy.': '명성을 높여 자격을 갖추라.',
}

# (plugin, FormID): (EditorID, SHA-256 of the original complete SCPT body).
PINS = {
    ('Knights.esp', 0x0017721A): ('ShrineStendarr', '51531d8491329851afeb141810946d21873413f1085681e63a6a6c7b4e2c0659'),
    ('Knights.esp', 0x00177219): ('ShrineArkay', '7d094c149c2ec5b475ebca047013f7c830f241e5b524cd8a4bc208347feb3cfe'),
    ('Knights.esp', 0x00177218): ('ShrineDibella', '23a7e5be21f30d0c295813d047f603afe39330bccad05bf573b3d87570e2924a'),
    ('Knights.esp', 0x00177217): ('ShrineAkatosh', '2990661fb80e6409690ccfbff8769e81646dc5ddf4c2f0d6d5b1bd798c473dcd'),
    ('Knights.esp', 0x00177216): ('ShrineTiberSeptim', '72a84171e7f0d800f37140c72892de17e5735bbceaacf68501ea8be92a39f5e0'),
    ('Knights.esp', 0x00177215): ('ShrineZenithar', '08785ef263d4aa9ed0c3d88eeb6e0de1b0143b94d8dee873b6c83bfce18789c4'),
    ('Knights.esp', 0x00177214): ('ShrineKynareth', '3c3f74a55aa6de51bda00fe4b2711a7348b86781d79710cebe0d8e0b903e1421'),
    ('Knights.esp', 0x00177213): ('ShrineJulianos', '0d1165e909454209dc78d0fb5e9d7d9639ea59dea4589271d2b2333725e57789'),
    ('Knights.esp', 0x00177201): ('ShrineMara', '4f72c1a7e9d1e7784acdc7b041811aac783888104f2eab3fcbe7e148934fc967'),
    ('Oblivion.esm', 0x0017721A): ('ShrineStendarr', '40be438893f24b079268991643e642902dcb4989f2d6401230bcad90250a7ad9'),
    ('Oblivion.esm', 0x00177219): ('ShrineArkay', '9750634027b192070aa9bc96f13dfadef486b308d7f0ea572a918b2e12535713'),
    ('Oblivion.esm', 0x00177218): ('ShrineDibella', '7f94316ba09fb508a15684075bad04c3004a368b97ad27ecc967d3c20570122f'),
    ('Oblivion.esm', 0x00177217): ('ShrineAkatosh', '7eb531ed28e7b3a9d0297c62bb79fb95f4538f3109f5dae94a4a1cb21ce08ef2'),
    ('Oblivion.esm', 0x00177216): ('ShrineTiberSeptim', '90ef08351ed9701402dc3555d07f7c47a4a0b74d0cb5498ea5a6f12c8bb493a0'),
    ('Oblivion.esm', 0x00177215): ('ShrineZenithar', '0bdffe0a42b657595e8ab37819703fd44eb01ada9a818e191d63cc8258490469'),
    ('Oblivion.esm', 0x00177214): ('ShrineKynareth', 'd4a7ea85f1375b92d6cdab57e50f3a78651920d45fa2ea81d8ffe26b2e15faa0'),
    ('Oblivion.esm', 0x00177213): ('ShrineJulianos', 'e6832c871339c84aeeff2df0ac28d6f66910de52b89210c6ae36b2feb65bc7fd'),
    ('Oblivion.esm', 0x00177201): ('ShrineMara', 'de0bfa25e07b86359078135660582488092ced6e42216b30b8b7a0b72798ea4d'),
    ('Knights - Unofficial Patch.esp', 0x00177201): ('ShrineMara', 'bfba6ec77113e1dc31c0da8c8d715afbd256349b8b7f3770181f9298840c452f'),
    ('Knights - Unofficial Patch.esp', 0x00177213): ('ShrineJulianos', '81a5037c6f22057cf9e755ec83207b8bd5b58ed2c24794fa7e3f798fd3ac180b'),
    ('Knights - Unofficial Patch.esp', 0x00177214): ('ShrineKynareth', '90b11e082a86b3b8882386ac1c9eb3de3cd250a005842c4b92241c9f1008c10f'),
    ('Knights - Unofficial Patch.esp', 0x00177215): ('ShrineZenithar', 'a7c2963523d6560d2646e95c8afe701129437d993dedaea67d9d699f9662db09'),
    ('Knights - Unofficial Patch.esp', 0x00177216): ('ShrineTiberSeptim', '630c8c6761e2528dbcc425354b1317b46a8a2291601e4871aee8ae4f578506e8'),
    ('Knights - Unofficial Patch.esp', 0x00177217): ('ShrineAkatosh', '084f4e507bd8a67968c973375680758686899cd8f4e79dc416c8f24d7cedc4ea'),
    ('Knights - Unofficial Patch.esp', 0x00177218): ('ShrineDibella', '2b32f23c53ca44eb7e1fb84062b625360921d51d5768648b9b31b7f73f6236df'),
    ('Knights - Unofficial Patch.esp', 0x00177219): ('ShrineArkay', '32115273ff7079c27fbfcd5a7a20f1edfe1236f0d290cef5a5eac3c7c23989f7'),
    ('Knights - Unofficial Patch.esp', 0x0017721A): ('ShrineStendarr', 'f46a008556bb277a41f4f0599a1ff2cfecc2c7dad0898983feaa3649ac56c6b7'),
}


def translate_body(body, edid, pin):
    if hashlib.sha256(body).hexdigest() != pin:
        raise ValueError('Wayshrine script differs from the verified original')
    parts = list(parse_subrecords(body))
    if next((v.rstrip(b'\0').decode('ascii') for k, v, _ in parts if k == b'EDID'), None) != edid:
        raise ValueError('Wayshrine script identity mismatch')
    fields = {k: v for k, v, _ in parts}
    if sum(k == b'SCDA' for k, _, _ in parts) != 1 or sum(k == b'SCTX' for k, _, _ in parts) != 1:
        raise ValueError('Expected one compiled script and one source script')
    lines = re.findall(rb'^\s*messagebox\s+"([^"\r\n]+)"', fields[b'SCTX'], re.I | re.M)
    if (len(lines), len(set(lines))) not in ((3, 3), (5, 5), (8, 6)):
        raise ValueError('Unexpected wayshrine message count')
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
    if len(pins) != 9:
        raise ValueError('Expected nine wayshrine identities for supported plugin')
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError('Wayshrine output must be new and separate from input')
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
                    raise ValueError('Duplicate or compressed wayshrine script')
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
        raise ValueError('Missing wayshrine scripts')
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
        raise ValueError('Wayshrine output checksum mismatch')
    return dict(source_sha256=source_sha, output_sha256=output_sha, scripts=reports,
                script_count=len(reports), display_strings=sum(len(r['changes']) // 2 for r in reports),
                file_size_unchanged=True, only_allowlisted_literal_bytes_changed=True,
                bytecode_lengths_and_control_flow_unchanged=True, runtime_verified=False)
