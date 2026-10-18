#!/usr/bin/env python3
"""Rebuild the Korean UOP/USIP/UODP OBCJK UTF-8 overlay from latest originals.

The existing Korean ESPs are translation memory only. This tool copies the
latest original records and changes verified text subrecords, preserving every
other field and compiled script. Audited CELL/WRLD, REFR map-marker, and REGN
location names are forwarded in the same UTF-8 build. Legacy output and the old
save-era English location-name guard are no longer part of the release policy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

from build_vanilla_overlay import (Translation, decode_english, encode_subrecord, load_quest_loading_translations,
                                   load_translations, parse_subrecords, sha256_file,
                                   structure_signature)
from uop_book_restoration import (BARZ_FIVE, UOP_PLUGIN, load_restorations,
                                  normalize_volume_five_title, restore_book_body,
                                  suspicious_book_body)

PAIRS = (
    ("UOP", "Unofficial Oblivion Patch-KR"),
    ("USIP", "Unofficial Shivering Isles Patch-KR"),
    ("UODP", "Unofficial Oblivion DLC Patches-KR"),
)
TEXT_FIELDS = {b"FULL", b"DESC", b"NAM1", b"CNAM", b"DATA", b"RDMP"}


def read_records(path: Path):
    result = {}
    with path.open("rb") as stream:
        def walk(end):
            while stream.tell() < end:
                start = stream.tell()
                header = stream.read(20)
                if len(header) != 20:
                    raise ValueError(f"{path.name}: short header at {start}")
                kind, size, flags, formid, _ = struct.unpack("<4sIIII", header)
                if kind == b"GRUP":
                    if size < 20 or start + size > end:
                        raise ValueError(f"{path.name}: invalid group")
                    walk(start + size)
                else:
                    if start + 20 + size > end:
                        raise ValueError(f"{path.name}: invalid record")
                    body = stream.read(size)
                    if flags & 0x40000:
                        expected = struct.unpack_from("<I", body)[0]
                        body = zlib.decompress(body[4:])
                        if len(body) != expected:
                            raise ValueError(f"{path.name}: bad compression")
                    key = (kind, formid)
                    if key in result:
                        raise ValueError(f"{path.name}: duplicate record {kind!r} {formid:08X}")
                    result[key] = [(field, value) for field, value, _ in parse_subrecords(body)]
            if stream.tell() != end:
                raise ValueError(f"{path.name}: group boundary mismatch")
        walk(path.stat().st_size)
    return result


def load_patch_canonical(path: Path):
    table = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            target = bytes.fromhex(row["obcjk_utf8_hex"])
            if not target.endswith(b"\0") or b"\0" in target[:-1]:
                raise ValueError(f"{path.name} line {line}: invalid UTF-8 target")
            target[:-1].decode("utf-8")
            editor = row.get("editor_id")
            occurrence = row.get("occurrence", "")
            item = Translation(
                row["effective_source"], row["record_type"].encode("ascii"),
                int(row["raw_formid"], 16), row["field"].encode("ascii"),
                row["old_english"], target, line,
                editor.encode("ascii") if editor else None,
                int(occurrence) if occurrence not in (None, "") else None,
            )
            table[(item.source, item.record_type, item.formid, item.field)].append(item)
    return table


def matching_patch_translation(table, plugin, record_type, formid, field, old, editor, occurrence):
    matches = (table or {}).get((plugin, record_type, formid, field), ())
    matches = [item for item in matches if item.english == decode_english(old)
               and (item.editor_id is None or item.editor_id == editor)
               and (item.occurrence is None or item.occurrence == occurrence)]
    targets = {item.korean for item in matches}
    return targets.pop() if len(targets) == 1 else None


def has_localizable_text(path: Path):
    """Return true only for player-visible string-like fields outside TES4 metadata."""
    for (kind, _), fields in read_records(path).items():
        if kind == b"TES4":
            continue
        for field, value in fields:
            if field not in TEXT_FIELDS or not value.endswith(b"\0") or b"\0" in value[:-1]:
                continue
            try:
                text = value[:-1].decode("cp1252")
            except UnicodeDecodeError:
                continue
            if text.strip():
                return True
    return False


def reviewed_identity(records, formid):
    """Resolve an override through its TES4 masters, never through the patch's own slot."""
    masters = [value.rstrip(b"\0").decode("ascii")
               for field, value in records[(b"TES4", 0)] if field == b"MAST"]
    slot = formid >> 24
    if slot >= len(masters):
        return None
    owner = masters[slot]
    # Translation tables use the source plugin's file-relative identity.
    canonical_slot = 0 if owner == "Oblivion.esm" else 1
    return owner, (canonical_slot << 24) | (formid & 0xFFFFFF)


def matching_translation(table, official, record_type, formid, field, old, editor, occurrence):
    candidates = (table or {}).get((official, record_type, formid, field), ())
    matches = [item for item in candidates if item.english == decode_english(old) and
               (item.editor_id is None or item.editor_id == editor) and
               (item.occurrence is None or item.occurrence == occurrence)]
    if not matches:
        return None
    targets = {item.korean for item in matches}
    if len(targets) == 1:
        return targets.pop()
    # Match the main builder's ordered direct-source refinement policy.
    direct = [item for item in matches if item.source == official]
    return direct[-1].korean if direct else None


def collect_changes(original: Path, prior: Path | None, vanilla_audit=None, vanilla_table=None, final_table=None,
                    quest_entries=None, loading_entries=None, completions=None, nexus_completions=None,
                    patch_table=None, location_table=None, patch_location_table=None,
                    book_restorations=None):
    old_records = read_records(original)
    kr_records = read_records(prior) if prior is not None else old_records
    if old_records.keys() != kr_records.keys():
        raise ValueError(f"{original.name}: record identities differ from Korean reference")
    changes = {}
    counts = Counter()
    for key, old_fields in old_records.items():
        identity = reviewed_identity(old_records, key[1])
        official, base_formid = identity if identity else (None, None)
        kr_fields = kr_records[key]
        if [field for field, _ in old_fields] != [field for field, _ in kr_fields]:
            raise ValueError(f"{original.name}: subrecord sequence differs at {key}")
        old_editor = next((value for field, value in old_fields if field == b"EDID"), b"")
        kr_editor = next((value for field, value in kr_fields if field == b"EDID"), b"")
        if old_editor != kr_editor:
            raise ValueError(f"{original.name}: EditorID differs at {key}")
        stage = None
        stage_occurrences = Counter()
        field_occurrences = Counter()
        for index, ((field, old), (_, new)) in enumerate(zip(old_fields, kr_fields)):
            field_occurrence = field_occurrences[field]
            field_occurrences[field] += 1
            if key[0] == b"QUST" and field == b"INDX":
                stage = int.from_bytes(old, "little")
            occurrence = None
            if key[0] == b"QUST" and field == b"CNAM" and stage is not None:
                occurrence = stage_occurrences[stage]
                stage_occurrences[stage] += 1
            if field not in TEXT_FIELDS:
                if old != new:
                    raise ValueError(f"{original.name}: non-text difference at {key} field {field!r}")
                continue
            # Oblivion resolves voice folders from the visible RACE name.
            # Keep race FULL names in English so Sound\\Voice\\...\\Imperial, Argonian, etc. still resolve.
            if key[0] == b"RACE" and field == b"FULL":
                if old != new:
                    counts["voice_safe_race_names_preserved"] += 1
                continue
            if not old.endswith(b"\0"):
                if old != new:
                    raise ValueError(f"{original.name}: non-text difference at {key} field {field!r}")
                continue
            if old != new and not new.endswith(b"\0"):
                raise ValueError(f"{original.name}: non-text difference at {key} field {field!r}")
            if b"\0" in old[:-1]:
                if old != new:
                    raise ValueError(f"{original.name}: embedded NUL at {key} field {field!r}")
                continue
            if old != new and b"\0" in new[:-1]:
                raise ValueError(f"{original.name}: embedded NUL at {key} field {field!r}")

            # Existing KR is a legacy fallback. A tracked canonical patch table
            # can replace that dependency entirely for reproducible UTF-8 builds.
            replacement = new if old != new else None
            patch_selected = matching_patch_translation(
                patch_table, original.name, key[0], key[1], field, old,
                old_editor.rstrip(b"\0"), field_occurrence)
            if patch_selected is not None:
                replacement = patch_selected
                counts["canonical_patch_translation"] += 1
            is_location = ((key[0] in (b"CELL", b"WRLD", b"REFR") and field == b"FULL") or
                           (key[0] == b"REGN" and field == b"RDMP"))
            if is_location:
                patch_location = matching_patch_translation(
                    patch_location_table, original.name, key[0], key[1], field, old,
                    old_editor.rstrip(b"\0"), field_occurrence)
                direct_location = matching_patch_translation(
                    location_table, original.name, key[0], key[1], field, old,
                    old_editor.rstrip(b"\0"), field_occurrence)
                if patch_location is not None:
                    replacement = patch_location
                    counts["canonical_patch_location"] += 1
                elif direct_location is not None:
                    replacement = direct_location
                    counts["canonical_direct_location"] += 1
                elif identity is not None:
                    official_location = matching_translation(
                        location_table, official, key[0], base_formid, field, old,
                        old_editor.rstrip(b"\0"), field_occurrence)
                    if official_location is not None:
                        replacement = official_location
                        counts["canonical_base_location"] += 1
            reviewed = None
            if vanilla_audit is not None:
                audit_key = (official, key[0].decode("ascii"), f"{base_formid:08X}" if identity else "",
                             field.decode("ascii"), hashlib.sha256(old).hexdigest())
                if audit_key in vanilla_audit:
                    selected = matching_translation(vanilla_table, official, key[0], base_formid,
                                                    field, old, old_editor.rstrip(b"\0"), field_occurrence)
                    if selected is not None:
                        reviewed = selected
                        replacement = reviewed
            if official == "Oblivion.esm" and quest_entries is not None:
                special = None
                if key[0] == b"QUST" and field == b"CNAM" and occurrence is not None:
                    special = quest_entries.get((base_formid, stage, occurrence))
                elif key[0] == b"LSCR" and field == b"DESC":
                    special = (loading_entries or {}).get(base_formid)
                if special and special[0] == old_editor.rstrip(b"\0") and special[1] == old:
                    reviewed = special[2]
                    replacement = reviewed
            # Explicit final review outranks journal memories and completion fallbacks.
            selected = matching_translation(final_table, official, key[0], base_formid,
                                            field, old, old_editor.rstrip(b"\0"), field_occurrence)
            if selected is not None:
                reviewed = selected
                replacement = selected
            completion = (completions or {}).get((original.name, key[0], key[1], field))
            if completion and reviewed is None:
                if old != completion[0]:
                    raise ValueError(f"{original.name}: completion source mismatch at {key}")
                replacement = completion[1]
                counts["manual_completion"] += 1
            nx_occurrence = occurrence if (key[0] == b"QUST" and field == b"CNAM" and occurrence is not None) else field_occurrence
            nx_stage = stage if (key[0] == b"QUST" and field == b"CNAM") else None
            nx = (nexus_completions or {}).get((original.name, key[0], key[1], field, nx_occurrence, nx_stage))
            if nx and reviewed is None:
                if old != nx[0]:
                    raise ValueError(f"{original.name}: nexus completion source mismatch at {key} {field!r} occ {nx_occurrence}")
                replacement = nx[1]
                counts["nexus_completion"] += 1
            # Late, FormID- and source-hash-scoped BOOK repair outranks stale
            # canonical UOP title-only DESC translations and prior KR memories.
            if original.name == UOP_PLUGIN and key[0] == b"BOOK":
                if field == b"DESC":
                    restored = restore_book_body(key[1], old, book_restorations or {})
                    if restored is not None:
                        replacement = restored
                        counts["uop_book_desc_restored"] += 1
                elif field == b"FULL" and key[1] == BARZ_FIVE:
                    replacement = normalize_volume_five_title(
                        replacement if replacement is not None else old)
                    counts["uop_book_title_fixed"] += 1

            # Reject catastrophic future truncation: BOOK/DESC cannot silently
            # become just the title, even when it is non-empty valid UTF-8.
            if key[0] == b"BOOK" and field == b"DESC" and replacement is not None:
                new_body = replacement.rstrip(b"\0").decode("utf-8", errors="strict")
                if suspicious_book_body(decode_english(old), new_body):
                    raise ValueError(
                        f"{original.name}: BOOK/DESC reduced to title-only body "
                        f"at FormID {key[1]:08X}")

            if replacement is not None and replacement != old:
                changes.setdefault(key, {})[index] = (field, old, replacement)
                counts["translated_fields"] += 1
                if reviewed is not None:
                    counts["reviewed_base_translation"] += 1
                    if old != new and replacement != new:
                        counts["reviewed_base_overrode_prior_kr"] += 1
                elif old == new:
                    counts["forwarded_base_translation"] += 1
    return changes, counts

def rewrite(original: Path, destination: Path, changes):
    destination.parent.mkdir(parents=True, exist_ok=True)
    applied = 0
    with original.open("rb") as src, destination.open("w+b") as dst:
        def walk(end):
            nonlocal applied
            while src.tell() < end:
                start = src.tell()
                header = src.read(20)
                if len(header) != 20:
                    raise ValueError(f"{original.name}: truncated record")
                kind, size, flags, formid, _ = struct.unpack("<4sIIII", header)
                if kind == b"GRUP":
                    out_start = dst.tell()
                    dst.write(header)
                    walk(start + size)
                    out_end = dst.tell()
                    dst.seek(out_start + 4)
                    dst.write(struct.pack("<I", out_end - out_start))
                    dst.seek(out_end)
                    continue
                body = src.read(size)
                if len(body) != size:
                    raise ValueError(f"{original.name}: truncated body")
                replacements = changes.get((kind, formid))
                if replacements:
                    compressed = bool(flags & 0x40000)
                    plain = zlib.decompress(body[4:]) if compressed else body
                    parts = list(parse_subrecords(plain))
                    updated = []
                    for index, (field, value, raw) in enumerate(parts):
                        expected = replacements.get(index)
                        if expected:
                            if (field, value) != expected[:2]:
                                raise ValueError(f"{original.name}: source mismatch at {kind!r} {formid:08X}")
                            updated.append(encode_subrecord(field, expected[2]))
                            applied += 1
                        else:
                            updated.append(raw)
                    plain = b"".join(updated)
                    body = struct.pack("<I", len(plain)) + zlib.compress(plain) if compressed else plain
                    header = header[:4] + struct.pack("<I", len(body)) + header[8:]
                dst.write(header)
                dst.write(body)
            if src.tell() != end:
                raise ValueError(f"{original.name}: container mismatch")
        walk(original.stat().st_size)
    return applied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Folder with UOP/USIP/UODP original subfolders")
    parser.add_argument("--prior-kr", type=Path, help="Optional older KR overlays used only as translation-memory input")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vanilla-audit", type=Path, help="Final vanilla build translation_audit.json")
    parser.add_argument("--text-backend", choices=("obcjk",), default="obcjk",
                        help="OBCJK UTF-8 output. Legacy output is no longer supported.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    patch_table = load_patch_canonical(root / "canonical_unofficial_translation_v2.csv")
    book_restorations = load_restorations(
        root / "uop_book_body_restore_v1.csv",
        root / "canonical_translation_v2.csv")
    location_table = load_patch_canonical(root / "canonical_locations_v2.csv")
    patch_location_table = load_patch_canonical(root / "canonical_unofficial_locations_v2.csv")
    if args.vanilla_audit:
        data = json.loads(args.vanilla_audit.read_text(encoding="utf-8"))
        vanilla_audit = {(a["file"], a["type"], a["formid"], a["field"], a["source_sha256"])
                         for a in data["applied"]}
        # Official-record forwarding uses the same canonical v2 table as the
        # vanilla release. Legacy/remaster memories are archival only.
        vanilla_table = load_translations(
            root / "canonical_translation_v2.csv",
            encoded_column="obcjk_utf8_hex" if args.text_backend == "obcjk" else "new_bytes_hex")
        final_table = None
        quest_entries = loading_entries = None
    else:
        vanilla_audit = vanilla_table = final_table = quest_entries = loading_entries = None
    completions = {}
    if args.text_backend == "legacy":
        with (Path(__file__).resolve().parent / "patch_completion.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                key = (row["file"], row["record_type"].encode("ascii"),
                       int(row["formid"], 16), row["field"].encode("ascii"))
                if key in completions:
                    raise ValueError(f"duplicate patch completion {key}")
                completions[key] = (bytes.fromhex(row["source_hex"]), bytes.fromhex(row["target_hex"]))
    nexus_completions = {}
    nexus_path = Path(__file__).resolve().parent / "_build" / "nexus_patch_completion.csv"
    if args.text_backend == "legacy" and nexus_path.is_file():
        with nexus_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                key = (row["file"], row["record_type"].encode("ascii"), int(row["formid"], 16),
                       row["field"].encode("ascii"), int(row["occurrence"]),
                       int(row["quest_stage"]) if row["quest_stage"] else None)
                if key in nexus_completions:
                    raise ValueError(f"duplicate nexus completion {key}")
                nexus_completions[key] = (bytes.fromhex(row["source_hex"]), bytes.fromhex(row["target_hex"]))
    report = {}
    for source_folder, kr_folder in PAIRS:
        originals = sorted((args.source / source_folder).glob("*.esp"))
        if not originals:
            raise ValueError(f"No original ESPs in {args.source / source_folder}")
        for original in originals:
            prior = (args.prior_kr / kr_folder / original.name) if args.prior_kr else None
            destination = args.output / kr_folder / original.name
            if prior is not None and not prior.is_file():
                prior = None
            if args.text_backend == "legacy" and prior is None:
                if has_localizable_text(original):
                    raise FileNotFoundError(args.prior_kr / kr_folder / original.name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
                before = structure_signature(original)
                if before != structure_signature(destination):
                    raise ValueError(f"{original.name}: passthrough structure differs")
                report[original.name] = {
                    "source_sha256": sha256_file(original),
                    "output_sha256": sha256_file(destination),
                    "translated_fields": 0,
                    "passthrough_without_kr_reference": True,
                    "location_fields_preserved_english": 0,
                    "structure": before,
                }
                print(f"{original.name}: unchanged passthrough; no player-visible text and no KR reference")
                continue
            changes, counts = collect_changes(original, prior, vanilla_audit, vanilla_table, final_table,
                                              quest_entries, loading_entries, completions, nexus_completions,
                                              patch_table, location_table, patch_location_table,
                                              book_restorations=book_restorations)
            if original.name == UOP_PLUGIN and counts["uop_book_desc_restored"] != len(book_restorations):
                raise ValueError(
                    f"UOP BOOK/DESC restoration incomplete: "
                    f"{counts['uop_book_desc_restored']}/{len(book_restorations)}")
            destination = args.output / kr_folder / original.name
            applied = rewrite(original, destination, changes)
            if applied != counts["translated_fields"]:
                raise ValueError(f"{original.name}: applied count mismatch")
            before = structure_signature(original)
            after = structure_signature(destination)
            if before != after:
                raise ValueError(f"{original.name}: structure or script differs")
            report[original.name] = {
                "source_sha256": sha256_file(original),
                "output_sha256": sha256_file(destination),
                "translated_fields": applied,
                "forwarded_base_translation": counts["forwarded_base_translation"],
                "reviewed_base_translation": counts["reviewed_base_translation"],
                "reviewed_base_overrode_prior_kr": counts["reviewed_base_overrode_prior_kr"],
                "manual_completion": counts["manual_completion"],
                "nexus_completion": counts["nexus_completion"],
                "canonical_base_location": counts["canonical_base_location"],
                "canonical_direct_location": counts["canonical_direct_location"],
                "canonical_patch_location": counts["canonical_patch_location"],
                "canonical_patch_translation": counts["canonical_patch_translation"],
                "uop_book_desc_restored": counts["uop_book_desc_restored"],
                "uop_book_title_fixed": counts["uop_book_title_fixed"],
                "text_backend": args.text_backend,
                "structure": before,
            }
            if original.name == 'Knights - Unofficial Patch.esp':
                from build_shrine_messages import build as build_shrine_messages
                temporary = destination.with_suffix('.esp.shrine-building')
                shrine_report = build_shrine_messages(destination, temporary, original.name)
                temporary.replace(destination)
                report[original.name]['shrine_messages'] = shrine_report
                report[original.name]['output_sha256'] = shrine_report['output_sha256']
            print(f"{original.name}: {applied} Korean fields; reviewed-base {counts['reviewed_base_translation']} (overrode prior KR {counts['reviewed_base_overrode_prior_kr']}), forwarded-base {counts['forwarded_base_translation']}; locations base {counts['canonical_base_location']} + direct {counts['canonical_direct_location']} + patch {counts['canonical_patch_location']}")
    (args.output / "release_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
