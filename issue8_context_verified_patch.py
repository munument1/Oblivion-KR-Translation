"""Issue #8: context-verified Gatekeeper, Marauder, Bands of the Chosen.

This module corrects only source-anchored, audited original records. 'Cupboard'
is intentionally left untouched because its SEED glossary entry is disputed.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path
from issue8_reporter_term_patch import verify_canonical

GATEKEEPER = re.compile(r"(?<![A-Za-z])Gatekeeper(?![A-Za-z])", re.I)
MARAUDER = re.compile(r"(?<![A-Za-z])Marauders?(?![A-Za-z])", re.I)
BANDS = re.compile(r"(?<![A-Za-z])Bands of the Chosen(?![A-Za-z])", re.I)
BAND_ALIASES = (
    "선택 받은 자의 밴드",
    "선택받은 자의 밴드",
    "선택받은 자의 띠",
    "선택 받은 자의 띠",
    "선민의 팔찌",
)
EXPECTED = {
    "Gatekeeper": 231,
    "Marauder": 16,
    "Bands of the Chosen": 25,
}
MARKERS = re.compile(
    r"<[^>]*>|%(?:[-+0#]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+"
)


def correct_context_verified_names(translations, canonical_csv: Path | None = None):
    """Preflight all original names, preserve records and change only Korean UTF-8.

    The original source English must contain the named term, source plugin and
    type identity must match, and all three known corpus counts must match.
    """
    if canonical_csv is not None:
        verify_canonical(canonical_csv)
    plans = []
    counts = Counter()
    identities = set()
    for key, candidates in translations.items():
        target, record_type, fid, field = key
        for index, item in enumerate(candidates):
            if (item.source != target or item.record_type != record_type
                or item.formid != fid or item.field != field):
                continue
            if not item.korean.endswith(b"\0") or b"\0" in item.korean[:-1]:
                raise ValueError("Issue #8 invalid translated string")
            before = item.korean[:-1].decode("utf-8", "strict")
            after = before
            applied = []
            if target == "Oblivion.esm" and GATEKEEPER.search(item.english):
                # The relevant English records refer to Shivering Isles' named
                # Gatekeeper creature (verified against creature FULL and quests).
                new = re.sub("관문지기|문지기", "게이트키퍼", after)
                if new != after:
                    applied.append("Gatekeeper")
                    after = new
            if MARAUDER.search(item.english):
                new = after.replace("약탈자", "습격자")
                if new != after:
                    applied.append("Marauder")
                    after = new
            if target == "Oblivion.esm" and BANDS.search(item.english):
                new = after
                for alias in BAND_ALIASES:
                    new = new.replace(alias, "선택받은 자의 팔찌")
                if new != after:
                    applied.append("Bands of the Chosen")
                    after = new
            if after == before:
                continue
            identity = (key, item.source, item.editor_id, item.occurrence, item.line)
            if identity in identities:
                raise ValueError(f"Issue #8 duplicate source row: {identity}")
            identities.add(identity)
            if MARKERS.findall(before) != MARKERS.findall(after):
                raise ValueError(f"Issue #8 markup/placeholder drift: {identity}")
            if [c for c in before if c in "\r\n"] != [c for c in after if c in "\r\n"]:
                raise ValueError(f"Issue #8 newline drift: {identity}")
            for name in applied:
                counts[name] += 1
            plans.append((key, index, item, after.encode("utf-8") + b"\0"))
    if dict(counts) != EXPECTED:
        raise ValueError(f"Issue #8 contextual source drift: expected {EXPECTED}, got {dict(counts)}")
    for key, index, item, target in plans:
        translations[key][index] = replace(item, korean=target)
    return dict(counts)
