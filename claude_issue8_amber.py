"""Verified Shivering Isles Amber equipment terminology, issue #8.

The canonical source stays byte-identical. This fix only changes translation
values in memory after loading the published canonical data, and refuses
unexpected source drift. All FormIDs, EditorIDs, English source strings,
occurrence slots and unrelated TES4 fields stay untouched.
"""
from dataclasses import replace
import re

EXPECTED = {"황색": 107, "앰버": 44}
ENGLISH_AMBER = re.compile(r"(?<![A-Za-z])Amber(?![A-Za-z])")
EQUIPMENT = frozenset((b"AMMO", b"ARMO", b"WEAP"))
SOURCE = "Oblivion.esm"


def correct_amber_equipment_names(translations):
    """Use confirmed 호박석 for only 151 verified Shivering Isles item names."""
    changes = []
    counts = {word: 0 for word in EXPECTED}
    unique = set()
    for key, candidates in translations.items():
        source, kind, formid, field = key
        if source != SOURCE or kind not in EQUIPMENT or field != b"FULL":
            continue
        for index, item in enumerate(candidates):
            if not (item.source == SOURCE and item.record_type == kind
                    and item.formid == formid and item.field == field
                    and ENGLISH_AMBER.search(item.english)
                    and item.editor_id and item.editor_id.startswith(b"SE")
                    and item.korean.endswith(b"\0")):
                continue
            korean = item.korean[:-1].decode("utf-8")
            matched = [word for word in EXPECTED if word in korean]
            if len(matched) != 1:
                continue
            word = matched[0]
            updated = korean.replace(word, "호박석")
            identity = (key, item.editor_id, item.occurrence)
            if identity in unique:
                raise ValueError("duplicate Amber equipment identity")
            unique.add(identity)
            changes.append((key, index, item, updated.encode("utf-8") + b"\0"))
            counts[word] += 1

    if counts != EXPECTED or len(changes) != 151:
        raise ValueError(
            f"Claude #8 Amber source drift: expected {EXPECTED}, got {counts}"
        )
    for key, index, item, payload in changes:
        translations[key][index] = replace(item, korean=payload)
    return counts
