#!/usr/bin/env python3
"""Build a Korean Oblivion mod overlay from the user's original game files.

The patcher edits existing string subrecords after exact source checks and adds
verified executable string settings. It never creates gameplay records.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import struct
import sys
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from issue6_book_markup_fix import correct_selected_book, load_manifest as load_issue6_book_manifest

from build_video_subtitles import build_videos

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MASTER = "Oblivion.esm"
# The executable supplies these menu strings, but the original ESM has no
# records for them. Some are "bare" EXE setting keys, so the generic EXE
# scanner cannot pair them with their visible English value. Inject explicit
# GMST overrides so character creation and confirmation menus can localize them.
BASE_MENU_GMSTS = (
    (0x00F00001, b"sExitGameAffirm\0", b"Exit Game\0",
     bytes.fromhex("b08bd7a90520c8a408c38500")),
    (0x00F00002, b"sExitGameQuestion\0", b"Exit the game?\0",
     bytes.fromhex("b08bd7a905c7a80420c8a408c385bd80b689d0ab14c6a806b189be803f00")),
    (0x00F00003, b"sCancel\0", b"Cancel\0",
     bytes.fromhex("d997c68400")),
    (0x00F00004, b"sMain\0", b"Main Menu\0",
     bytes.fromhex("b48bd7a90220b48bc18700")),
    (0x00F00005, b"sFace\0", b"Face\0",
     bytes.fromhex("d7a204c0a60400")),
    (0x00F00006, b"sHair\0", b"Hair\0",
     bytes.fromhex("b482b38900")),
    (0x00F00007, b"sEyes\0", b"Eyes\0",
     bytes.fromhex("c1a60200")),
    (0x00F00008, b"sYesText\0", b"Yes\0",
     bytes.fromhex("b78d00")),
    (0x00F00009, b"sYes\0", b"Yes\0",
     bytes.fromhex("b78d00")),
    (0x00F0000A, b"sNo\0", b"No\0",
     bytes.fromhex("b780b189c78500")),
    (0x00F0000B, b"sOnButtonText\0", b"On\0",
     bytes.fromhex("ba83b08900")),
    (0x00F0000C, b"sOffButtonText\0", b"Off\0",
     bytes.fromhex("ce88b08900")),
    (0x00F0000D, b"sOff\0", b"Off\0",
     bytes.fromhex("ce88b08900")),
    (0x00F0000E, b"sSkillNameArmorer\0", b"Armorer\0",
     bytes.fromhex("b88bd3a302c6a60400")),
    (0x00F0000F, b"sSkillNameAthletics\0", b"Athletics\0",
     bytes.fromhex("c7a602c2a408c1a808d3a30100")),
    (0x00F00010, b"sSkillNameBlade\0", b"Blade\0",
     bytes.fromhex("d0a205c6a60400")),
    (0x00F00011, b"sSkillNameBlock\0", b"Block\0",
     bytes.fromhex("d5a008b78200")),
    (0x00F00012, b"sSkillNameBlunt\0", b"Blunt\0",
     bytes.fromhex("c2a602b08900")),
    (0x00F00013, b"sSkillNameHandToHand\0", b"Hand To Hand\0",
     bytes.fromhex("d0a301cb8600")),
    (0x00F00014, b"sSkillNameAlchemy\0", b"Alchemy\0",
     bytes.fromhex("d7a302c0a805c6a60400")),
    (0x00F00015, b"sSkillNameAlteration\0", b"Alteration\0",
     bytes.fromhex("d5a302b789b480d5a20600")),
    (0x00F00016, b"sSkillNameConjuration\0", b"Conjuration\0",
     bytes.fromhex("c684ed9902b480d5a20600")),
    (0x00F00017, b"sSkillNameDestruction\0", b"Destruction\0",
     bytes.fromhex("bc80d095b480d5a20600")),
    (0x00F00018, b"sSkillNameIllusion\0", b"Illusion\0",
     bytes.fromhex("ed9902d7a308b480d5a20600")),
    (0x00F00019, b"sSkillNameMysticism\0", b"Mysticism\0",
     bytes.fromhex("d6a902b589b480d5a20600")),
    (0x00F0001A, b"sSkillNameRestoration\0", b"Restoration\0",
     bytes.fromhex("dd95c5a401b480d5a20600")),
    (0x00F0001B, b"sSkillNameAcrobatics\0", b"Acrobatics\0",
     bytes.fromhex("c0a401b78d00")),
    (0x00F0001C, b"sSkillNameMarksman\0", b"Marksman\0",
     bytes.fromhex("c0a608c6a60400")),
    (0x00F0001D, b"sSkillNameMercantile\0", b"Mercantile\0",
     bytes.fromhex("d6a008c6a60400")),
    (0x00F0001E, b"sSkillNameSecurity\0", b"Security\0",
     bytes.fromhex("d8a005c0a805bd8ab88b00")),
    (0x00F0001F, b"sSkillNameSneak\0", b"Sneak\0",
     bytes.fromhex("d8a005d7a906c6a60400")),
    (0x00F00020, b"sSkillNameSpeechcraft\0", b"Speechcraft\0",
     bytes.fromhex("dd90c6a60400")),
    (0x00F00021, b"sAttributeNameStrength\0", b"Strength\0",
     bytes.fromhex("dda90500")),
    (0x00F00022, b"sAttributeNameIntelligence\0", b"Intelligence\0",
     bytes.fromhex("b889c1a80800")),
    (0x00F00023, b"sAttributeNameWillpower\0", b"Willpower\0",
     bytes.fromhex("d798b889d3a30100")),
    (0x00F00024, b"sAttributeNameAgility\0", b"Agility\0",
     bytes.fromhex("d4a902d9a206d6a20800")),
    (0x00F00025, b"sAttributeNameSpeed\0", b"Speed\0",
     bytes.fromhex("c6a401c28400")),
    (0x00F00026, b"sAttributeNameEndurance\0", b"Endurance\0",
     bytes.fromhex("b889c086d3a30100")),
    (0x00F00027, b"sAttributeNamePersonality\0", b"Personality\0",
     bytes.fromhex("b48ad3a30100")),
    (0x00F00028, b"sAttributeNameLuck\0", b"Luck\0",
     bytes.fromhex("ddaa08c7a60200")),
    (0x00F00029, b"sSpecNameMagic\0", b"Magic\0",
     bytes.fromhex("b480d5a20600")),
    (0x00F0002A, b"sSpecNameStealth\0", b"Stealth\0",
     bytes.fromhex("c7a802d6a90200")),
    (0x00F0002B, b"sLevelPopUpText\0",
     b"To increase your level, make progress learning your class's major skills.\0",
     bytes.fromhex("b38bd5ab04c7a80420c7a404b389b383d4a30220d8a901d7a206d79820c886c78520b089c6a604c7a80420d7a901bd8320d8a902ddaa08c284c3a80420c1a411b789b68bc7852e00")),
)
EXE_GMST_PATTERN = re.compile(rb"(?<![A-Za-z0-9_])(s[A-Z][A-Za-z0-9_]{2,60})\x00{1,4}([\x20-\x7e]{1,180})\x00")
PRINTF_PATTERN = re.compile(r"%(?:[-+0#]*\d*(?:\.\d+)?[a-zA-Z%])")
OFFICIAL = (
    MASTER, "Knights.esp", "DLCBattlehornCastle.esp", "DLCFrostcrag.esp",
    "DLCThievesDen.esp", "DLCSpellTomes.esp", "DLCMehrunesRazor.esp",
    "DLCVileLair.esp", "DLCOrrery.esp", "DLCHorseArmor.esp",
    "DLCShiveringIsles.esp",
)
PATCH_TO_OFFICIAL = {
    "Unofficial Oblivion Patch.esp": MASTER,
    "Unofficial Shivering Isles Patch.esp": MASTER,
    **{f"{name[:-4]} - Unofficial Patch.esp": name for name in OFFICIAL[1:]},
}
SOURCE_RANK = {name: 0 for name in OFFICIAL}
SOURCE_RANK.update({"Unofficial Shivering Isles Patch.esp": 1,
                    "Unofficial Oblivion Patch.esp": 2})


@dataclass(frozen=True)
class Translation:
    source: str
    record_type: bytes
    formid: int
    field: bytes
    english: str
    korean: bytes
    line: int
    editor_id: bytes | None = None
    occurrence: int | None = None


def load_translations(path: Path, extra_paths=(), encoded_column="new_bytes_hex"):
    table = defaultdict(list)
    for source_path in (path, *extra_paths):
        with source_path.open(encoding="utf-8-sig", newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), 2):
                # Remaster LOC_FN_* keys are name-only resources. They may
                # supply FULL names, but must never be reused as journal,
                # description, book-body, or other non-name text.
                if (row.get('locres_key', '').startswith('LOC_FN_')
                        and row.get('field') != 'FULL'):
                    continue
                source = row["effective_source"]
                target = source if source in OFFICIAL else PATCH_TO_OFFICIAL.get(source)
                if target is None:
                    continue
                # The game's menu save filename includes the current location.
                if row["record_type"] in ("CELL", "WRLD") and row["field"] == "FULL":
                    continue
                formid = int(row["raw_formid"], 16)
                # Official DLC records may also override base-game FormIDs.
                if (formid >> 24) not in ((0,) if target == MASTER else (0, 1)):
                    continue
                encoded = row.get(encoded_column, "")
                if not encoded:
                    raise ValueError(f"{source_path.name} line {line}: missing {encoded_column}")
                korean = bytes.fromhex(encoded)
                if not korean.endswith(b"\0") or b"\0" in korean[:-1]:
                    raise ValueError(f"{source_path.name} line {line}: invalid encoded string")
                editor_id = row.get("editor_id")
                occurrence_text = row.get("occurrence", "")
                occurrence = int(occurrence_text) if occurrence_text not in (None, "") else None
                item = Translation(source, row["record_type"].encode("ascii"),
                                   formid, row["field"].encode("ascii"),
                                   row["old_english"], korean, line,
                                   editor_id.encode("ascii") if editor_id else None,
                                   occurrence)
                table[(target, item.record_type, formid, item.field)].append(item)
    return table


def decode_english(data: bytes) -> str:
    raw = data.rstrip(b"\0")
    try:
        return raw.decode("cp1252")
    except UnicodeDecodeError:
        return raw.decode("latin1")


def normalize_source_text(text: str) -> str:
    # csv text mode normalizes CRLF in multiline fields to LF, while TES4
    # subrecords retain CRLF. Compare logical text, not newline byte style.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def parse_subrecords(data: bytes):
    pos = 0
    while pos < len(data):
        start = pos
        if pos + 6 > len(data):
            raise ValueError("truncated subrecord header")
        kind = data[pos:pos + 4]
        size = struct.unpack_from("<H", data, pos + 4)[0]
        pos += 6
        if kind == b"XXXX":
            if size != 4 or pos + 10 > len(data):
                raise ValueError("invalid XXXX subrecord")
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            kind = data[pos:pos + 4]
            pos += 6
        if pos + size > len(data):
            raise ValueError("subrecord extends past record")
        yield kind, data[pos:pos + size], data[start:pos + size]
        pos += size


def existing_gmst_keys(path: Path) -> set[bytes]:
    keys = set()
    with path.open("rb") as stream:
        def walk(end):
            while stream.tell() < end:
                start = stream.tell()
                header = stream.read(20)
                if len(header) != 20:
                    raise ValueError(f"{path.name}: truncated record at {start}")
                kind, size = struct.unpack_from("<4sI", header)
                if kind == b"GRUP":
                    if size < 20 or start + size > end:
                        raise ValueError(f"{path.name}: invalid group at {start}")
                    walk(start + size)
                elif kind == b"GMST":
                    body = stream.read(size)
                    for field, value, _ in parse_subrecords(body):
                        if field == b"EDID":
                            keys.add(value.rstrip(b"\0"))
                            break
                else:
                    stream.seek(size, 1)
            if stream.tell() != end:
                raise ValueError(f"{path.name}: group boundary mismatch")
        walk(path.stat().st_size)
    return keys


def load_menu_gmsts(existing_csv: Path, new_csv: Path, translations, text_backend="legacy"):
    with existing_csv.open(encoding="utf-8-sig", newline="") as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            fid = int(row["raw_formid"], 16); key = row["editor_id"].encode("ascii")
            korean = ((row["new_korean"].encode("utf-8") + b"\0")
                      if text_backend == "obcjk" else bytes.fromhex(row["new_bytes_hex"]))
            item = Translation("menu_gmst_master", b"GMST", fid, b"DATA", row["old_english"], korean, line, key, 0)
            translations[(MASTER, b"GMST", fid, b"DATA")] = [item]
    result=[]; seen=set()
    with new_csv.open(encoding="utf-8-sig", newline="") as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            fid=int(row["formid"],16); key=row["edid"].encode("ascii"); english=row["english"].encode("cp1252")
            korean = ((row["korean"].encode("utf-8") + b"\0")
                      if text_backend == "obcjk" else bytes.fromhex(row["encoded_hex"]))
            # Oblivion.esm has no masters: only file slot 00 is legal. xEdit
            # normalizes out-of-range slots to 00, hiding collisions if we
            # compare raw IDs alone.
            if not 0 < fid <= 0x00FFFFFF:
                raise ValueError(f"invalid Oblivion.esm menu GMST file slot at line {line}: {fid:08X}")
            if fid in seen or not re.fullmatch(rb"s[A-Z][A-Za-z0-9_]*", key): raise ValueError(f"duplicate or invalid menu GMST at line {line}")
            if not korean.endswith(b"\0") or b"\0" in korean[:-1]: raise ValueError(f"invalid menu GMST bytes at line {line}")
            if PRINTF_PATTERN.findall(row["english"]) != PRINTF_PATTERN.findall(row["korean"]): raise ValueError(f"menu GMST placeholder mismatch at line {line}")
            result.append((fid,key+b"\0",english+b"\0",korean)); seen.add(fid)
    return tuple(result)

def load_quest_loading_translations(path: Path):
    quest = {}
    loading = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            kind = row["record_type"]
            formid = int(row["formid"], 16)
            editor_id = row["editor_id"].encode("ascii")
            source = bytes.fromhex(row["source_hex"])
            target = bytes.fromhex(row["encoded_hex"])
            if not source.endswith(b"\0") or not target.endswith(b"\0") or b"\0" in target[:-1]:
                raise ValueError(f"invalid journal/loading text at CSV line {line}")
            if kind == "QUST":
                key = (formid, int(row["stage"]), int(row["occurrence"]))
                dest = quest
            elif kind == "LSCR":
                key = formid
                dest = loading
            else:
                raise ValueError(f"invalid journal/loading record type at CSV line {line}")
            if key in dest:
                raise ValueError(f"duplicate journal/loading key at CSV line {line}")
            dest[key] = (editor_id, source, target, line)
    return quest, loading


def encode_subrecord(kind: bytes, value: bytes) -> bytes:
    if len(value) <= 0xFFFF:
        return kind + struct.pack("<H", len(value)) + value
    return b"XXXX\x04\x00" + struct.pack("<I", len(value)) + kind + b"\0\0" + value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def structure_signature(path: Path, skip_formids=frozenset()):
    """Check container bounds and preserve record identity and compiled scripts."""
    digest = hashlib.sha256()
    scripts = hashlib.sha256()
    records = groups = 0
    with path.open("rb") as stream:
        def walk(end):
            nonlocal records, groups
            while stream.tell() < end:
                start = stream.tell()
                header = stream.read(20)
                if len(header) != 20:
                    raise ValueError(f"{path.name}: short header at {start}")
                kind, size = struct.unpack_from("<4sI", header)
                if kind == b"GRUP":
                    if size < 20 or start + size > end:
                        raise ValueError(f"{path.name}: bad GRUP at {start}")
                    groups += 1
                    digest.update(header[:4] + header[8:])
                    walk(start + size)
                else:
                    if start + 20 + size > end:
                        raise ValueError(f"{path.name}: bad record at {start}")
                    formid = struct.unpack_from("<I", header, 12)[0]
                    if formid in skip_formids:
                        stream.seek(size, 1)
                        continue
                    records += 1
                    digest.update(header[:4] + header[8:])
                    if kind == b"SCPT":
                        scripts.update(header[:4] + header[8:])
                        remaining = size
                        while remaining:
                            block = stream.read(min(remaining, 1 << 20))
                            scripts.update(block)
                            remaining -= len(block)
                    elif kind in (b"QUST", b"INFO"):
                        body = stream.read(size)
                        if struct.unpack_from("<I", header, 8)[0] & 0x00040000:
                            body = zlib.decompress(body[4:])
                        scripts.update(header[:4] + header[8:])
                        for field, _, original in parse_subrecords(body):
                            if field in (b"SCHR", b"SCDA", b"SCTX", b"SCRO"):
                                scripts.update(original)
                    else:
                        stream.seek(size, 1)
            if stream.tell() != end:
                raise ValueError(f"{path.name}: container mismatch")

        walk(path.stat().st_size)
    return {"records": records, "groups": groups,
            "identity_sha256": digest.hexdigest(), "scripts_sha256": scripts.hexdigest()}


def patch_record(data: bytes, filename: str, record_type: bytes, formid: int,
                 translations, counts: Counter, audit: list[dict],
                 quest_texts=None, loading_texts=None, utf8_untranslated=False) -> bytes:
    parts = list(parse_subrecords(data))
    editor_id = next((value.rstrip(b"\0") for field, value, _ in parts if field == b"EDID"), b"")
    changed = False
    output = []
    stage = None
    stage_occurrences = Counter()
    field_occurrences = Counter()
    for field, value, original in parts:
        field_occurrence = field_occurrences[field]
        field_occurrences[field] += 1
        if record_type == b"QUST" and field == b"INDX":
            stage = int.from_bytes(value, "little")
        special = None
        if record_type == b"QUST" and field == b"CNAM" and stage is not None and quest_texts:
            occurrence = stage_occurrences[stage]
            stage_occurrences[stage] += 1
            special = quest_texts.get((formid, stage, occurrence))
        elif record_type == b"LSCR" and field == b"DESC" and loading_texts:
            special = loading_texts.get(formid)
        if special is not None:
            expected_editor, expected_source, replacement, line = special
            if editor_id != expected_editor or value != expected_source:
                raise ValueError(f"journal/loading source mismatch: {filename} {formid:08X} CSV line {line}")
            output.append(encode_subrecord(field, replacement))
            changed = True
            counts["journal_loading"] += 1
            counts["applied"] += 1
            audit.append({"file": filename, "type": record_type.decode("ascii"),
                          "formid": f"{formid:08X}", "field": field.decode("ascii"),
                          "source_sha256": hashlib.sha256(value).hexdigest(),
                          "source": decode_english(value),
                          "translation_sources": ["legacy original Korean patch journal/loading"]})
            continue
        candidates = translations.get((filename, record_type, formid, field), ())
        if not candidates:
            is_display_text = (field == b"FULL" or field == b"DESC" or
                               (field == b"NAM1" and record_type == b"INFO") or
                               (field == b"CNAM" and record_type == b"QUST") or
                               (field == b"DATA" and record_type == b"GMST" and editor_id.startswith(b"s")))
            protected_name = record_type in {b"CELL", b"WRLD", b"RACE"} and field == b"FULL"
            if utf8_untranslated and is_display_text and not protected_name and value.endswith(b"\0") and b"\0" not in value[:-1]:
                try:
                    target = value[:-1].decode("cp1252").encode("utf-8") + b"\0"
                except UnicodeDecodeError:
                    target = value
                if target != value:
                    output.append(encode_subrecord(field, target))
                    changed = True
                    counts["utf8_untranslated"] += 1
                    continue
            output.append(original)
            continue
        english = decode_english(value)
        matches = [x for x in candidates if normalize_source_text(x.english) == normalize_source_text(english) and
                   (x.editor_id is None or x.editor_id == editor_id) and
                   (x.occurrence is None or x.occurrence == field_occurrence)]
        if not matches:
            output.append(original)
            continue
        # The same English string may occur in duplicate CSV rows. Apply only
        # if all matching rows agree on the encoded replacement.
        replacements = {x.korean for x in matches}
        if len(replacements) != 1:
            # Translation tables are ordered from legacy/broad memories to
            # newer, more exact Remaster recoveries. When the same exact
            # source field is intentionally refined, the latest direct row
            # wins. This avoids treating a verified refinement as ambiguity.
            direct = [x for x in matches if x.source == filename]
            if direct:
                latest = direct[-1]
                matches = [latest]
                replacements = {latest.korean}
            else:
                counts["ambiguous"] += 1
                output.append(original)
                continue
        replacement = replacements.pop()
        if (utf8_untranslated and filename == MASTER and record_type == b"BOOK"
                and field == b"DESC"):
            replacement = correct_selected_book(
                filename, formid, editor_id, value, replacement,
                load_issue6_book_manifest())
        if replacement == value:
            output.append(original)
            continue
        output.append(encode_subrecord(field, replacement))
        changed = True
        counts["applied"] += 1
        audit.append({"file": filename, "type": record_type.decode("ascii"),
                      "formid": f"{formid:08X}", "field": field.decode("ascii"),
                      "source_sha256": hashlib.sha256(value).hexdigest(),
                      "source": english, "translation_sources": sorted({x.source for x in matches})})
    return b"".join(output) if changed else data


def patch_plugin(source: Path, destination: Path, filename: str, translations,
                 counts: Counter, audit: list[dict], menu_gmsts=(),
                 quest_texts=None, loading_texts=None, utf8_untranslated=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    menu_formids = frozenset(item[0] for item in menu_gmsts)
    if filename == MASTER and any(not 0 < fid <= 0x00FFFFFF for fid in menu_formids):
        raise ValueError("invalid Oblivion.esm menu GMST file slot")
    with source.open("rb") as src, destination.open("w+b") as dst:
        limit = source.stat().st_size

        def walk(end: int):
            while src.tell() < end:
                start = src.tell()
                header = src.read(20)
                if len(header) != 20:
                    raise ValueError(f"{filename}: truncated record at {start}")
                kind, size = struct.unpack_from("<4sI", header)
                if kind == b"GRUP":
                    if size < 20 or start + size > end:
                        raise ValueError(f"{filename}: invalid group at {start}")
                    out_start = dst.tell()
                    dst.write(header)
                    walk(start + size)
                    if filename == MASTER and header[8:12] == b"GMST" and header[12:16] == b"\0\0\0\0":
                        for menu_formid, editor_id, english, korean in menu_gmsts:
                            menu_body = (encode_subrecord(b"EDID", editor_id) +
                                         encode_subrecord(b"DATA", korean))
                            dst.write(struct.pack("<4sIIII", b"GMST", len(menu_body), 0,
                                                  menu_formid, 0))
                            dst.write(menu_body)
                            counts["new_menu_gmst"] += 1
                            audit.append({"file": filename, "type": "GMST",
                                          "formid": f"{menu_formid:08X}", "field": "DATA",
                                          "source_sha256": hashlib.sha256(english).hexdigest(),
                                          "source": english[:-1].decode("ascii"),
                                          "translation_sources": ["menu GMST"]})
                    out_end = dst.tell()
                    dst.seek(out_start + 4)
                    dst.write(struct.pack("<I", out_end - out_start))
                    dst.seek(out_end)
                    continue
                if start + 20 + size > end:
                    raise ValueError(f"{filename}: invalid record at {start}")
                flags, formid = struct.unpack_from("<II", header, 8)
                if filename == MASTER and (formid & 0x00FFFFFF) in menu_formids:
                    raise ValueError("menu GMST FormID collides with source record")
                if filename == MASTER and kind == b"TES4":
                    body = bytearray(src.read(size))
                    if body[:6] != b"HEDR\x0c\x00":
                        raise ValueError("unexpected TES4 HEDR layout")
                    old_count = struct.unpack_from("<I", body, 10)[0]
                    struct.pack_into("<I", body, 10, old_count + len(menu_gmsts))
                    dst.write(header)
                    dst.write(body)
                    continue
                has_special = (filename == MASTER and
                               ((kind == b"QUST" and quest_texts and formid in quest_texts["formids"]) or
                                (kind == b"LSCR" and loading_texts and formid in loading_texts)))
                if not utf8_untranslated and not has_special and not translations.get((filename, kind, formid, b"FULL")) and not any(
                        translations.get((filename, kind, formid, field))
                        for field in (b"DESC", b"NAM1", b"CNAM", b"DATA")):
                    dst.write(header)
                    remaining = size
                    while remaining:
                        block = src.read(min(remaining, 1 << 20))
                        if not block:
                            raise ValueError(f"{filename}: truncated record data")
                        dst.write(block)
                        remaining -= len(block)
                    continue
                body = src.read(size)
                compressed = bool(flags & 0x00040000)
                if compressed:
                    if len(body) < 4:
                        raise ValueError(f"{filename}: short compressed record")
                    expected = struct.unpack_from("<I", body)[0]
                    plain = zlib.decompress(body[4:])
                    if len(plain) != expected:
                        raise ValueError(f"{filename}: bad compressed record")
                else:
                    plain = body
                updated = patch_record(plain, filename, kind, formid, translations, counts, audit,
                                       quest_texts["entries"] if has_special and kind == b"QUST" else None,
                                       loading_texts if has_special and kind == b"LSCR" else None,
                                       utf8_untranslated=utf8_untranslated)
                if updated != plain:
                    body = struct.pack("<I", len(updated)) + zlib.compress(updated) if compressed else updated
                    header = header[:4] + struct.pack("<I", len(body)) + header[8:]
                    counts["changed_records"] += 1
                dst.write(header)
                dst.write(body)
            if src.tell() != end:
                raise ValueError(f"{filename}: container size mismatch")

        walk(limit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="Original game Data directory (read only)")
    parser.add_argument("--output", type=Path, required=True, help="Destination MO2 mod or staging folder")
    parser.add_argument("--csv", type=Path, default=HERE / "canonical_translation_v2.csv")
    parser.add_argument("--extra-csv", type=Path, action="append", default=[],
                        help="Additional verified translation-memory CSV (repeatable)")
    parser.add_argument("--ini", type=Path, help="Optional active Oblivion.ini to update with a backup")
    parser.add_argument("--text-backend", choices=("obcjk",), default="obcjk",
                        help="Build the OBCJK UTF-8 overlay. Legacy release output is no longer supported.")
    parser.add_argument("--obcjk-ini", type=Path,
                        help="Optional UTF-8 obCJK INI for the obcjk backend")
    parser.add_argument("--video-subtitles", choices=("off", "auto", "required"), default="off",
                        help="Burn Korean subtitles into original intro/outro videos using FFmpeg and RAD Video Tools")
    args = parser.parse_args()
    from build_obcjk_release import build
    return build(args)
    source_dir = args.data_dir.resolve()
    output_dir = args.output.resolve()
    if source_dir == output_dir or source_dir in output_dir.parents or output_dir in source_dir.parents:
        parser.error("output must be separate from the source Data directory")
    # v2 canonical source-of-truth: the exact effective translation set
    # reconstructed from the reviewed Original build. Legacy/remaster memories
    # remain archival inputs only and are never consulted by release builds.
    table = load_translations(args.csv, tuple(args.extra_csv))
    if not (source_dir / MASTER).is_file():
        parser.error(f"{MASTER} is missing from {source_dir}")
    menu_gmsts = load_menu_gmsts(HERE / "menu_gmst_existing_105.csv", HERE / "menu_gmst_new_821.csv", table)
    menu_formids = frozenset(item[0] for item in menu_gmsts)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = []
    report = {}
    for name in OFFICIAL:
        src = source_dir / name
        if not src.is_file():
            print(f"SKIP missing {name}")
            continue
        counts = Counter()
        target = output_dir / name
        temporary = output_dir / (name + ".building")
        try:
            patch_plugin(src, temporary, name, table, counts, audit,
                         menu_gmsts if name == MASTER else ())
            if name == MASTER and counts["applied"] < 9000:
                raise ValueError("Oblivion.esm does not match the expected original English source")
            original_structure = structure_signature(src)
            output_structure = structure_signature(
                temporary, menu_formids if name == MASTER else frozenset())
            if original_structure != output_structure:
                raise ValueError(f"{name}: record structure or compiled script changed")
            if name == MASTER and counts["new_menu_gmst"] != len(menu_gmsts):
                raise ValueError("unexpected menu GMST count")
            if counts["applied"]:
                temporary.replace(target)
            else:
                temporary.unlink()
                target.unlink(missing_ok=True)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        report[name] = {"source_sha256": sha256_file(src),
                        "applied_strings": counts["applied"],
                        "changed_records": counts["changed_records"],
                        "ambiguous": counts["ambiguous"],
                        "new_menu_gmst": counts["new_menu_gmst"],
                        "journal_loading": counts["journal_loading"],
                        "structure": original_structure,
                        "output_sha256": sha256_file(target) if target.exists() else None}
        print(f"{name}: {counts['applied']} strings in {counts['changed_records']} records")
    for asset in (HERE / "assets").rglob("*"):
        if asset.is_file():
            if asset.name == 'oblivion_native_layout.json.gz':
                continue  # Builder metadata; never a game Data asset.
            target = output_dir / asset.relative_to(HERE / "assets")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset, target)
    font_lines = {
        "SFontFile_1": r"Data\Fonts\TheGreatestKorean.fnt",
        "SFontFile_2": r"Data\Fonts\TheGreatestKorean_shadowed.fnt",
        "SFontFile_3": r"Data\Fonts\TheGreatestKorean_Small_FIXED.fnt",
    }
    snippet = "[Fonts]\n" + "".join(f"{key}={value}\n" for key, value in font_lines.items())
    (output_dir / "FONT_SETTINGS.txt").write_text(snippet, encoding="utf-8")
    if args.ini:
        ini = args.ini.resolve()
        if not ini.is_file():
            raise FileNotFoundError(f"INI not found: {ini}")
        raw = ini.read_bytes()
        content = raw.decode("cp1252")
        newline = "\r\n" if b"\r\n" in raw else "\n"
        lines = content.splitlines()
        section = None
        found = set()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.fullmatch(r"\[[^\]]+\]", stripped):
                section = stripped[1:-1].lower()
            if section == "fonts":
                match = re.match(r"\s*(SFontFile_[123])\s*=", line, re.IGNORECASE)
                if match:
                    key = "SFontFile_" + match.group(1)[-1]
                    lines[i] = f"{key}={font_lines[key]}"
                    found.add(key)
        if len(found) != len(font_lines):
            try:
                pos = next(i for i, line in enumerate(lines) if line.strip().lower() == "[fonts]")
            except StopIteration:
                lines.extend(["", "[Fonts]"])
                pos = len(lines) - 1
            lines[pos + 1:pos + 1] = [f"{key}={value}" for key, value in font_lines.items() if key not in found]
        updated = (newline.join(lines) + newline).encode("cp1252")
        if updated != raw:
            backup = ini.with_name(ini.name + ".before_oblivion_kr.bak")
            if not backup.exists():
                shutil.copy2(ini, backup)
            ini.write_bytes(updated)
            print(f"Font INI updated (backup: {backup})")
    videos = {}
    if args.video_subtitles != "off":
        videos = build_videos(source_dir, output_dir, HERE / "video_subtitles",
                              required=args.video_subtitles == "required")
    (output_dir / "translation_audit.json").write_text(
        json.dumps({"files": report, "applied": audit, "videos": videos}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
