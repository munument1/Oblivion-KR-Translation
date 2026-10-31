"""Issue #8: human-reviewed source-anchored exceptions missed by lexical glossary QA.

A few valid names use an obsolete phonetic spelling or a book header
already contains the canonical term while its body contains old variants.
Each correction is identified by original plugin, record type, FormID, field,
English concept and exact old Korean text, with fail-closed counts.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
import re

from issue8_reporter_term_patch import verify_canonical

# (report-id, source, record, FormID, field, required English, old KO, new KO, exact matches)
RULES = (
    ("cheydinhal_quest_title", "Oblivion.esm", b"QUST", 0x00085483, b"FULL",
     "Buying a house in Cheydinhal", "쉐이던홀에서 집 구입", "체이딘할에서 집 구입", 1),
    ("mythic_dawn_dialogue", "Oblivion.esm", b"INFO", 0x0008306B, b"NAM1",
     "Mythic Dawn", "미스틱 던", "미식 던", 1),
    ("mysterium_fourth_book_header", "Oblivion.esm", b"BOOK", 0x00022B07, b"DESC",
     "COMMENTARIES ON THE MYSTERIUM XARXES", "신비의 작시스 주해", "작시스의 신비 주해", 1),
    ("mysterium_quest_1", "Oblivion.esm", b"QUST", 0x0001E727, b"CNAM",
     "Mysterium Xarxes", "자서스 신비", "작시스의 신비", 1),
    ("mysterium_quest_2", "Oblivion.esm", b"QUST", 0x0001E728, b"CNAM",
     "Mysterium Xarxes", "미스테리움 자르크시스", "작시스의 신비", 1),
    ("mysterium_quest_3", "Oblivion.esm", b"QUST", 0x0001E72A, b"CNAM",
     "Mysterium Xarxes", "자서스 신비", "작시스의 신비", 1),
    ("mysterium_quest_4", "Oblivion.esm", b"QUST", 0x0001E72B, b"CNAM",
     "Mysterium Xarxes", "자서스 신비", "작시스의 신비", 1),
    ("mysterium_quest_5", "Oblivion.esm", b"QUST", 0x0001E72E, b"CNAM",
     "Mysterium Xarxes", "자서스 신비", "작시스의 신비", 2),
    ("mysterium_quest_6", "Oblivion.esm", b"QUST", 0x0001E72F, b"CNAM",
     "Mysterium Xarxes", "자서스 신비", "작시스의 신비", 1),
    ("knights_of_nine_book_body", "Knights.esp", b"BOOK", 0x01000ED2, b"DESC",
     "The Knights of the Nine", "나인 디바인 기사단", "나인의 기사단", 13),
    ("crusader_relics_book_body", "Knights.esp", b"BOOK", 0x01000ED2, b"DESC",
     "Crusader", "성전사의", "성기사의", 3),
    ("knights_of_nine_quest_reference", "Knights.esp", b"QUST", 0x01002D3F, b"CNAM",
     "former Knights of the Nine", "전 성기사 기사들의 유령", "나인의 기사단 선대 기사들의 유령", 1),
    ("mankar_quest_reference", "Oblivion.esm", b"QUST", 0x0001E728, b"CNAM",
     "Mankar Camoran", "만카 카모란", "맨카 캐모런", 1),
)
EXPECTED = {r[0]: r[-1] for r in RULES}
MARKERS = re.compile(r"<[^>]*>|%(?:[-+0#]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+")


def correct_glossary_exceptions(translations, canonical_csv: Path | None = None):
    if canonical_csv is not None:
        verify_canonical(canonical_csv)
    changed = Counter()
    planned = []
    seen = set()
    for key, items in translations.items():
        source, kind, fid, field = key
        for index, item in enumerate(items):
            if (item.source != source or item.record_type != kind
                    or item.formid != fid or item.field != field):
                continue
            if not item.korean.endswith(b"\0") or b"\0" in item.korean[:-1]:
                raise ValueError("Issue #8 exception: invalid NUL layout")
            before = item.korean[:-1].decode("utf-8", "strict")
            after = before
            for name, expected_source, record_type, formid, required_field, original, old_ko, new_ko, expected_count in RULES:
                if key != (expected_source, record_type, formid, required_field):
                    continue
                if original not in item.english:
                    continue
                occurrences = after.count(old_ko)
                if occurrences:
                    changed[name] += occurrences
                    after = after.replace(old_ko, new_ko)
            if before == after:
                continue
            identity = (key, item.english, item.editor_id, item.occurrence, item.line)
            if identity in seen:
                raise ValueError(f"Issue #8 exception duplicate: {identity}")
            seen.add(identity)
            if MARKERS.findall(before) != MARKERS.findall(after):
                raise ValueError(f"Issue #8 exception markup drift: {identity}")
            if [c for c in before if c in "\r\n"] != [c for c in after if c in "\r\n"]:
                raise ValueError(f"Issue #8 exception newline drift: {identity}")
            planned.append((key, index, item, after.encode("utf-8") + b"\0"))
    if dict(changed) != EXPECTED:
        raise ValueError(f"Issue #8 exception source drift: expected {EXPECTED}, found {dict(changed)}")
    for key, index, item, after in planned:
        translations[key][index] = replace(item, korean=after)
    return {"terms": dict(changed), "changed_rows": len(planned)}
