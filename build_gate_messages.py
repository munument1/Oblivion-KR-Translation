"""Translate hash-pinned base/UOP gate scripts using fixed-size UTF-8 literals.

Only SCDA/SCTX payload bytes change; all metadata, instructions and offsets
are preserved. ARGate01SCRIPT is linked by the base game's Ayleid Iron Gate.
This does not repair encoding failures in other mods.
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
    'No matter how hard you try, the gate will not move.': '아무리 애써도 문은 움직이지 않는다.',
}
PINS = {
    ('Oblivion.esm', 0x0006F3FF): ('ArcaneUGateScript', '078e68d59d97f0ab3d8dd266cdb1a59130b0a1f67a70b39ca1735eadc516b143'),
    ('Oblivion.esm', 0x0004CAEE): ('ARGate01SCRIPT', '80c0e51c9bf881f0257a6ab1c8811d14c14388fd6f5a539ad93b8f012e289c1d'),
    ('Oblivion.esm', 0x000947B3): ('SewerVerticalGate01SCRIPT', '92baf9e3cae2458b08508a3bf448040912f399e56aacd402e6c70d2948925062'),
    ('Unofficial Oblivion Patch.esp', 0x0000CCD0): ('OblivionGateSwitch01MQ03Gates', '778779c98acbb8fcdb0a30619fa597e5af5d4add339c5255dedc27844f01d502'),
    ('Unofficial Oblivion Patch.esp', 0x000947B3): ('SewerVerticalGate01SCRIPT', '36ea9717db084e6208243fa5b45b1fbd5df41b0940049bd906f485f11bdc7032'),
    ('Unofficial Oblivion Patch.esp', 0x000C49FC): ('OblivionGateSwitch01', '97230965dd47766fe5afef4ac9227dc3038a943871020da6b77d94b25c3f44cb'),
}


ISSUE25_PINS = {
    ('Oblivion.esm', 0x000C8A9C): ('SidewaysCave01Script', '321568d20badab4988580f017b8d6c2f18e8803b85f8394cf4ebe8e60e740f7e'),
    ('Oblivion.esm', 0x000C8A9B): ('SidewaysCave03Script', 'd4a728f0da0df11e5010a630597681072a152c696e6019e9188138374390a9b2'),
    ('Oblivion.esm', 0x000C8A9A): ('SidewaysCave02Script', 'f2ef40e0c78179f742d1a8e4ced77a9e494181541b76052711b720e1c7197f65'),
    ('Oblivion.esm', 0x000C8107): ('SidewaysCaveTablet03', '9a8bd10b25f12fbe4246cffd14f58d14c43b0797e52681c66082982ab405cfde'),
    ('Oblivion.esm', 0x000C8106): ('SidewaysCaveTablet01', '51b2f2dfe36fd697e1e8e9bce19eb67353d5eb77bcbb4faab39335871652850a'),
    ('Oblivion.esm', 0x0009764C): ('SE09RootGateMania02SCRIPT', '0b73160bda0792176a3133b4007b3ccdc6de908c4e021c167865e9d485f69cf6'),
    ('Oblivion.esm', 0x000410C8): ('RootGateMania02SCRIPT', 'c40fdcdaf2beff7f83661c342ec3961c68f1c2494d78bd7962764840371be604'),
    ('Oblivion.esm', 0x0007D435): ('SEDawnfangSpellEffectScript', 'b06d3fa7b6e5cdd8c9dd7a3481f585292f23533c0aa1f82e75578cb394d9e18e'),
    ('Oblivion.esm', 0x0007D444): ('SEDuskfangSpellEffectScript', '6c3524d0f52e13fe9d0ae7903d46c447ea12e982cf9ac97b236b68fb47615516'),
    ('Oblivion.esm', 0x000823C5): ('SEHillofSuicidesSCRIPT', '0ed8cfef539daeed7a54f4c686c1674e41aad61750500ac56179df34573eb455'),
    ('Oblivion.esm', 0x0006A8E1): ('AyleidWell', 'b9507db2d72572029beaa452439d56877543ac551be7463db7534334c78af47b'),
    ('Oblivion.esm', 0x0002D078): ('DarkBrotherhoodScript', 'b02f44bc720c9ed5a8c3156a3d47540ed0fce02fd1341b7d909a4b40bcb7e2f6'),
    ('Unofficial Oblivion Patch.esp', 0x0006A8E1): ('AyleidWell', 'fcbc2316d0bd60368246acd64dd781c6c8b39a62f9b2b0bd16ef17036aecaa77'),
    ('Unofficial Oblivion Patch.esp', 0x0002D078): ('DarkBrotherhoodScript', 'c48a871533e52e529c92b3917460f87d505df8f2580fd532fd9647d9bcc0a659'),
}

ISSUE25_MESSAGES = {
    ' The roots will not budge.': '뿌리가 꿈쩍없다.',
    'Dawnfang has extinguished %.0f life.': '다운팽 처치 수: %.0f',
    'Dawnfang has extinguished %.0f lives.': '다운팽 처치 수: %.0f',
    "Dawnfang's bloodthirst has been quenched.": '다운팽의 갈증이 가셨다.',
    'Duskfang has extinguished %.0f life.': '더스크팽 처치 수: %.0f',
    'Duskfang has extinguished %.0f lives.': '더스크팽 처치 수: %.0f',
    "Duskfang's bloodthirst has been quenched.": '더스크팽의 갈증이 가셨다.',
    'You cannot speak with this restless soul.': '이 영혼과는 대화할 수 없다.',
    'This well has been completely drained.': '우물의 힘이 모두 고갈됐다.',
    'A drained well recharges slowly. ': '우물은 천천히 회복된다.',
    'You draw power from the well.': '우물의 힘을 얻었다.',
    'Your killing has been observed by forces unknown....': '정체 모를 자들이 살인을 지켜보았다...',
    '[A hasty translation is scrawled here...] Meridia-child, Earth root power, sea wave like (earth like a flood?).  People-out (escape? present tense? imperative?).':
        '[급히 옮긴 글] 메리디아의 아이, 땅뿌리의 힘, 파도처럼(땅이 물결처럼?). 사람들-밖으로(도망? 현재형? 명령형?).',
    '[A hasty translation is scrawled here...] Stone-Settlers (builders?) not rest (wake?) Meridia.  Terror of the Most Terror. Haste to safehome.':
        '[급히 옮긴 글] 돌에 정착한 자들(석공?)이 메리디아를 깨운다(?). 지극한 공포. 안전한 집으로 서둘러라.',
    '[A hasty translation is scrawled here...] Fourth Star Hour (time?) Terror-of-the-Most-Terror of Meridia come (came?).':
        '[급히 옮긴 글] 네 번째 별의 시각(시간?). 메리디아의 지극한 공포가 온다(왔나?).',
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
    if (len(lines), len(set(lines))) not in ((1, 1), (2, 2), (3, 3)):
        raise ValueError('Unexpected gate message count')
    replacements = []
    for english in dict.fromkeys(lines):
        source_text = english.decode('ascii')
        korean = (TRANSLATIONS | ISSUE25_MESSAGES)[source_text].encode('utf-8')
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


def build(source, output, plugin=None, *, include_issue25=False):
    source, output = Path(source), Path(output)
    plugin = plugin or source.name
    pins = {fid: item for (name, fid), item in PINS.items() if name == plugin}
    expected = 3
    if len(pins) != expected:
        raise ValueError('Unexpected gate identities for supported plugin')
    if include_issue25:
        pins.update({fid: item for (name, fid), item in ISSUE25_PINS.items() if name == plugin})
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
