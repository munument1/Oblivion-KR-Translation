"""Issue #8 second-pass glossary names: exact-source, fail-closed in-memory fixes.

No generic Gatekeeper, Marauder or Cupboard substitution. The source CSV and
record identities remain byte-identical; outputs are produced by the regular builder.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

from issue8_reporter_term_patch import verify_canonical

# Counts verified from issue #8 source-audit artifact PR #15.
# The Modryn Oreyn place CELL belongs to the separate locations CSV (one row).
EXPECTED = {
    "Ayleid": 173,
    "Crucible": 74,
    "Jauffre": 29,
    "Staff of Sheogorath": 3,
    "Arquen": 10,
    "Modryn Oreyn": 21,
    "Vicente Valtieri": 15,
    "Mankar Camoran": 19,
    "Golden Saint": 39,
    "Dark Seducer": 41,
}

RULES = (
    ("Ayleid", re.compile(r"(?<![A-Za-z])Ayleids?(?![A-Za-z])", re.I),
     ("아일레이드",), "에일리드"),
    ("Crucible", re.compile(r"(?<![A-Za-z])Crucible(?![A-Za-z])", re.I),
     ("크루서블",), "크루시블"),
    ("Jauffre", re.compile(r"(?<![A-Za-z])Jauffre(?![A-Za-z])", re.I),
     ("조프리",), "죠프리"),
    ("Staff of Sheogorath", re.compile(r"(?<![A-Za-z])Staff of Sheogorath(?![A-Za-z])", re.I),
     ("쉐오고라스의 스태프",), "쉐오고라스의 지팡이"),
    ("Arquen", re.compile(r"(?<![A-Za-z])Arquen(?![A-Za-z])", re.I),
     ("아르쿠엔", "아르퀜"), "아퀜"),
    ("Modryn Oreyn", re.compile(r"(?<![A-Za-z])Modryn Oreyn(?![A-Za-z])", re.I),
     ("모드린 오레인",), "모드윈 오레인"),
    ("Vicente Valtieri", re.compile(r"(?<![A-Za-z])Vicente Valtieri(?![A-Za-z])", re.I),
     ("비센티 발티에리",), "비센테 발티에리"),
    ("Mankar Camoran", re.compile(r"(?<![A-Za-z])Mankar Camoran(?![A-Za-z])", re.I),
     ("맨카 케모런",), "맨카 캐모런"),
    ("Golden Saint", re.compile(r"(?<![A-Za-z])Golden Saints?(?![A-Za-z])", re.I),
     ("골드 세인트",), "골든 세인트"),
    ("Dark Seducer", re.compile(r"(?<![A-Za-z])Dark Seducers?(?![A-Za-z])", re.I),
     ("다크 시듀어",), "다크 세듀서"),
)
PLACEHOLDERS = re.compile(
    r"<[^>]*>|%(?:[-+0#]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+"
)


def correct_remaining_glossary_names(translations, source_path: Path | None = None):
    """Apply only confirmed aliases after validating the entire source/record corpus."""
    if source_path is not None:
        verify_canonical(source_path)
    planned = []
    counts = Counter()
    changed_identities = set()
    for key, candidates in translations.items():
        target, kind, formid, field = key
        for index, item in enumerate(candidates):
            # Reject unofficial upstream variants and unrelated auxiliary tables.
            if item.source != target or item.formid != formid or item.record_type != kind or item.field != field:
                continue
            if not item.korean.endswith(b"\0") or b"\0" in item.korean[:-1]:
                raise ValueError("Issue #8 invalid target string framing")
            old = item.korean[:-1].decode("utf-8", "strict")
            new = old
            matched = []
            for name, eng_re, aliases, canonical in RULES:
                if not eng_re.search(item.english) or canonical in new:
                    continue
                found = [alias for alias in aliases if alias in new]
                if len(found) != 1:
                    continue
                new = new.replace(found[0], canonical)
                matched.append(name)
            if old == new:
                continue
            identity = (key, item.source, item.editor_id, item.occurrence, item.line)
            if identity in changed_identities:
                raise ValueError("Issue #8 duplicate source identity")
            changed_identities.add(identity)
            if PLACEHOLDERS.findall(old) != PLACEHOLDERS.findall(new):
                raise ValueError(f"Issue #8 markup/placeholder drift: {identity}")
            if [c for c in old if c in "\r\n"] != [c for c in new if c in "\r\n"]:
                raise ValueError(f"Issue #8 newline drift: {identity}")
            for name in matched:
                counts[name] += 1
            planned.append((key, index, item, new.encode("utf-8") + b"\0"))
    if dict(counts) != EXPECTED:
        raise ValueError(
            f"Issue #8 second-pass source drift, expected {EXPECTED}, got {dict(counts)}"
        )
    for key, index, item, after in planned:
        translations[key][index] = replace(item, korean=after)
    return dict(counts)
