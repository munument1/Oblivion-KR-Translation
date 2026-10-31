"""Issue #8 semantic Cupboard repair, source-scoped to three verified contexts.

The original provisional glossary SEED mistakenly equates Cupboard with Shelf.
Real game cupboards are 찬장, while shelf/shelves remain 선반.
The English source records and canonical translation CSV are immutable.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

from issue8_reporter_term_patch import verify_canonical

EXPECTED = {"CONT_FULL": 48, "THIEVES_GUILD_JOURNAL": 2, "BRAVIL_FURNISHINGS_BOOK": 1}


def correct_cupboard_names(translations, canonical_csv: Path | None = None):
    if canonical_csv is not None:
        verify_canonical(canonical_csv)
    counts = Counter()
    planned = []
    identities = set()
    for key, items in translations.items():
        target, kind, formid, field = key
        if target != "Oblivion.esm":
            continue
        for idx, item in enumerate(items):
            if item.source != target or (item.record_type, item.formid, item.field) != (kind, formid, field):
                continue
            if not item.korean.endswith(b"\0") or b"\0" in item.korean[:-1]:
                raise ValueError("Cupboard source string has invalid NUL layout")
            before = item.korean[:-1].decode("utf-8", "strict")
            after = before
            group = None
            if kind == b"CONT" and field == b"FULL" and item.english == "Cupboard" and before == "선반":
                after = "찬장"
                group = "CONT_FULL"
            elif (kind == b"QUST" and formid == 0x00034EA2 and field == b"CNAM"
                  and "cupboard" in item.english.lower()
                  and "Myvryna" in item.english
                  and "미브리나의 선반" in before):
                after = before.replace("미브리나의 선반", "미브리나의 찬장")
                group = "THIEVES_GUILD_JOURNAL"
            elif (kind == b"BOOK" and formid == 0x00090EB2 and field == b"DESC"
                  and "Food Cupboard" in item.english
                  and "음식 컵보드" in before):
                after = before.replace("음식 컵보드", "음식 찬장")
                group = "BRAVIL_FURNISHINGS_BOOK"
            if group is None:
                continue
            if before.count("\r") != after.count("\r") or before.count("\n") != after.count("\n"):
                raise ValueError("Cupboard correction changed newlines")
            # Strict limited Korean nouns, no tags or variable strings are replaced.
            identity = (key, item.source, item.english, item.editor_id, item.occurrence, item.line)
            if identity in identities:
                raise ValueError(f"Duplicate Cupboard source row: {identity}")
            identities.add(identity)
            counts[group] += 1
            planned.append((key, idx, item, after.encode("utf-8") + b"\0"))
    if dict(counts) != EXPECTED:
        raise ValueError(f"Cupboard source drift: expected {EXPECTED}, got {dict(counts)}")
    for key, idx, item, data in planned:
        translations[key][idx] = replace(item, korean=data)
    return dict(counts)
