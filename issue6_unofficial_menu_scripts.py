"""SHA-pinned, fixed-length translation of UOP/USIP scripted message boxes.

For issue #6. This optional post-build stage is intentionally standalone.
The original SCPT bytecode, headers, branches, group sizes and all non-literal
bytes remain identical; translated UTF-8 is space-padded inside original
compiled 16-bit string lengths. No source ESP is modified in place.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
from pathlib import Path

from build_vanilla_overlay import parse_subrecords, sha256_file


# The PIN sha256 values below cover each complete original SCPT record body.
# They are obtained from the local, game-format source plugins, not invented.
PINS = {
    "Unofficial Oblivion Patch.esp": (
        0x01016EA6,
        "UOPMenuScript",
        "1fa2982b3c96a4b1b440334462b66fd903b723eb3271430cda8b99324375aff6",
    ),
    "Unofficial Shivering Isles Patch.esp": (
        0x030037FD,
        "USIPMenuScript",
        "8460f0cd7b586c5104f49ce79453dc49f5aed90d9959414df65c7dd95aa19eb0",
    ),
}

TRANSLATIONS = {
    "Unofficial Oblivion Patch.esp": {
        "Wait until combat mode ends before opening the UOP menu.": "전투가 끝나면 UOP 메뉴를 여세요.",
        "Unofficial Oblivion Patch v3.5.8": "비공식 패치 v3.5.8",
        "Exit and return to Oblivion": "돌아가기",
        "Turn OFF Poisoned Apple warning": "독사과 경고 끄기",
        "Turn ON vampire feeding fix": "흡혈 오류 수정 켜기",
        "Turn OFF Trespasses stat fix": "침입 횟수 수정 끄기",
        "Restore broken stats/attributes": "손상된 능력치 복구",
        "Change the Area of Effect spell": "광역 효과 주문 바꾸기",
        "Remove stuck Bound weapons/armor": "고정된 소환 장비 제거",
        "Toggle 'Follower Double-Face Fix' spell": "동료 얼굴 중복 수정 전환",
        "Turn ON Poisoned Apple warning": "독사과 경고 켜기",
        "Turn OFF vampire feeding fix": "흡혈 오류 수정 끄기",
        "Turn ON Trespasses stat fix": "침입 횟수 수정 켜기",
        "Currently using Effect # %.0f. If you're hearing strange noises or seeing spell effects every few seconds, another mod has changed the normally silent and invisible magic effect that the UOP uses for utility spells. Choose a different effect until the problem goes away.":
            "현재 효과 # %.0f 사용 중입니다. 이상한 소리나 주문 효과가 반복되면 다른 모드가 UOP 보조 주문의 비가시 효과를 바꾼 것입니다. 문제가 사라질 때까지 다른 효과를 선택하세요.",
        "Use effect # 0 (Z020)": "효과 # 0 (Z020)",
        "Use effect # 1 (RSWD)": "효과 # 1 (RSWD)",
        "Use effect # 2 (BA10)": "효과 # 2 (BA10)",
        "Use effect # 3 (BW10)": "효과 # 3 (BW10)",
        "Use effect # 4 (DARK)": "효과 # 4 (DARK)",
        "Use effect # 5 (NONE)": "효과 # 5 (NONE)",
        "Exit to main menu": "메뉴로 이동",
        # Original "OK" occupies only two bytes, shorter than a UTF-8 Korean
        # glyph; preserve it byte-for-byte to avoid corrupting compiled script.
    },
    "Unofficial Shivering Isles Patch.esp": {
        "Unofficial Shivering Isles Patch v1.6.1": "시버링 아일즈 패치 v1.6.1",
        "Exit and return to Oblivion": "돌아가기",
        "Turn ON excessive ambient sound fix": "주변 소음 오류 수정 켜기",
        "Turn ON Escort fast-travel fix": "호위 빠른이동 켜기",
        "Turn OFF excessive ambient sound fix": "주변 소음 오류 수정 끄기",
        "Turn OFF Escort fast-travel fix": "호위 빠른이동 끄기",
    },
}


def find_script(source: bytes, formid: int) -> tuple[int, bytes]:
    """Return offset of an uncompressed SCPT body, checking complete TES4 layout."""
    matches = []

    def walk(start: int, limit: int):
        while start < limit:
            if start + 20 > limit:
                raise ValueError("Truncated TES4 record header")
            kind, size, flags, fid, _ = struct.unpack_from("<4sIIII", source, start)
            stop = start + size if kind == b"GRUP" else start + 20 + size
            if not start + 20 <= stop <= limit:
                raise ValueError("Invalid TES4 record or group bounds")
            if kind == b"GRUP":
                walk(start + 20, stop)
            elif kind == b"SCPT" and fid == formid:
                if flags & 0x40000:
                    raise ValueError("Compressed target script unsupported")
                matches.append((start + 20, source[start + 20:stop]))
            start = stop
        if start != limit:
            raise ValueError("TES4 record boundary mismatch")

    walk(0, len(source))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one SCPT {formid:08X}, got {len(matches)}")
    return matches[0]


def translate_body(body: bytes, plugin: str):
    if plugin not in PINS:
        raise ValueError(f"Unknown unofficial plugin: {plugin}")
    fid, edid, expected_sha = PINS[plugin]
    if hashlib.sha256(body).hexdigest() != expected_sha:
        raise ValueError(f"{edid}: full original script SHA-256 mismatch")
    parts = list(parse_subrecords(body))
    identities = [v for field, v, _ in parts if field == b"EDID"]
    if identities != [edid.encode("ascii") + b"\0"]:
        raise ValueError("Original script EditorID mismatch")
    scda = [v for field, v, _ in parts if field == b"SCDA"]
    sctx = [v for field, v, _ in parts if field == b"SCTX"]
    if len(scda) != 1 or len(sctx) != 1:
        raise ValueError("Missing or duplicated source/compiled script field")

    all_lits = []
    for line in sctx[0].splitlines():
        if not re.search(rb"\bmessagebox\b", line, re.I):
            continue
        all_lits.extend(re.findall(rb'"([^"\r\n]*)"', line))
    source_counts = {literal: all_lits.count(literal) for literal in set(all_lits)}
    ascii_names = {value.decode("ascii") for value in source_counts}
    known_names = set(TRANSLATIONS[plugin]) | ({"OK"} if plugin == "Unofficial Oblivion Patch.esp" else set())
    if ascii_names != known_names:
        raise ValueError(f"Menu literals changed: missing={known_names - ascii_names}, new={ascii_names - known_names}")

    replacements = []
    for english, korean in TRANSLATIONS[plugin].items():
        original = english.encode("ascii")
        translated = korean.encode("utf-8")
        if (not translated or b"\0" in translated or b"\n" in translated or
                b"\r" in translated or b'"' in translated or len(translated) > len(original)
                or original.count(b"|") != translated.count(b"|")):
            raise ValueError(f"String does not fit original compiled bytes: {english!r} {len(translated)}/{len(original)}")
        if english.startswith("Use effect #"):
            # Numeric option IDs and effect magic codes are part of behavior.
            if re.findall(rb"# \d \([A-Z0-9]+\)", original) != re.findall(rb"# \d \([A-Z0-9]+\)", translated):
                raise ValueError("Effect identity changed")
        if original.count(b"%.0f") != translated.count(b"%.0f"):
            raise ValueError("Runtime format placeholder changed")
        replacements.append((original, translated.ljust(len(original), b" ")))

    output = bytearray(body)
    changed = []
    base = 0
    for field, value, raw in parts:
        if field in (b"SCDA", b"SCTX"):
            for old, new in replacements:
                positions = [match.start() for match in re.finditer(re.escape(old), value)]
                if len(positions) != source_counts[old]:
                    raise ValueError(f"{field.decode()} compiled/source occurrence mismatch for {old!r}")
                for position in positions:
                    if field == b"SCDA":
                        if position < 2 or struct.unpack_from("<H", value, position - 2)[0] != len(old):
                            raise ValueError("Compiled SCDA string prefix length mismatch")
                    absolute = base + len(raw) - len(value) + position
                    output[absolute:absolute + len(old)] = new
                    changed.append({"field": field.decode("ascii"), "body_offset": absolute,
                                    "length": len(old), "source_sha256": hashlib.sha256(old).hexdigest(),
                                    "english": old.decode("ascii"), "korean": new.rstrip(b" ").decode("utf-8")})
        base += len(raw)

    reverse = bytearray(output)
    for entry in changed:
        at = entry["body_offset"]
        reverse[at:at + entry["length"]] = entry["english"].encode("ascii")
    if reverse != body or len(output) != len(body):
        raise ValueError("Script changed outside approved byte-length-preserved literals")
    verify_fields = list(parse_subrecords(output))
    if [(field, len(value)) for field, value, _ in verify_fields] != [
        (field, len(value)) for field, value, _ in parts
    ]:
        raise ValueError("Subrecord layout changed")
    for (old_type, old_value, old_raw), (new_type, new_value, new_raw) in zip(parts, verify_fields):
        if old_type != new_type or (old_type not in (b"SCDA", b"SCTX") and old_raw != new_raw):
            raise ValueError("Original script metadata or control field modified")
    return bytes(output), changed


def build(source_path: Path, output_path: Path, plugin: str | None = None):
    source_path, output_path = Path(source_path), Path(output_path)
    plugin = plugin or source_path.name
    if plugin not in PINS:
        raise ValueError(f"Unsupported plugin: {plugin}")
    if source_path.resolve() == output_path.resolve() or output_path.exists():
        raise ValueError("Output must be new and separate from source")
    initial = source_path.read_bytes()
    source_hash = hashlib.sha256(initial).hexdigest()
    formid, editor_id, pin = PINS[plugin]
    body_offset, body = find_script(initial, formid)
    translated, changes = translate_body(body, plugin)
    after = bytearray(initial)
    after[body_offset:body_offset + len(body)] = translated
    recovered = bytearray(after)
    for change in changes:
        at = body_offset + change["body_offset"]
        recovered[at:at + change["length"]] = change["english"].encode("ascii")
    if recovered != initial or len(initial) != len(after):
        raise ValueError("Plugin differs outside source-pinned menu strings")
    if sha256_file(source_path) != source_hash:
        raise ValueError("Source plugin changed during translation")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as stream:
        stream.write(after)
    result_hash = hashlib.sha256(after).hexdigest()
    if sha256_file(output_path) != result_hash:
        raise ValueError("Output integrity check failed")
    return {"plugin": plugin, "formid": f"{formid:08X}", "editor_id": editor_id,
            "script_original_sha256": pin, "script_translated_sha256": hashlib.sha256(translated).hexdigest(),
            "source_sha256": source_hash, "output_sha256": result_hash,
            "source_size": len(initial), "output_size": len(after),
            "translated_unique_strings": len(TRANSLATIONS[plugin]),
            "translated_occurrences": len(changes) // 2,
            "compiled_and_source_occurrences": len(changes),
            "untouched_short_button": "OK" if plugin == "Unofficial Oblivion Patch.esp" else None,
            "all_other_bytes_unchanged": True, "compiled_lengths_unchanged": True,
            "script_flow_unchanged": True, "runtime_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    print(build(arguments.source, arguments.output))
