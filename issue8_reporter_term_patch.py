"""Issue #8: reporter/glossary terminology in real original source records.

NO broad global substitution. These rules run on the immutable published canonical
source and replace only known Korean aliases on verified English-source records.
A fail-closed preflight prevents any changes if the audited corpus drifts.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

CANONICAL_SHA256 = "57306d322a0cca7d18b452ecb5d0f38bc594d23ed2e6b6040a3eee828c96ca23"
EXPECTED = {
    "Cheydinhal": 219,
    "Mythic Dawn": 106,
    "Mysterium Xarxes": 47,
    "Knights of the Nine": 31,
    "Crusader equipment": 171,
}
RULES = (
    ("Cheydinhal", "Oblivion.esm;Knights.esp",
     re.compile(r"(?<![A-Za-z])Cheydinhal(?![A-Za-z])", re.I),
     ("셰이딘홀", "쉐이딘홀", "체이딘홀"), "체이딘할"),
    ("Mythic Dawn", "Oblivion.esm",
     re.compile(r"(?<![A-Za-z])Mythic Dawn(?![A-Za-z])", re.I),
     ("미씩 던",), "미식 던"),
    ("Mysterium Xarxes", "Oblivion.esm",
     re.compile(r"(?<![A-Za-z])Mysterium Xarxes(?![A-Za-z])", re.I),
     ("자서스의 신비",), "작시스의 신비"),
    ("Knights of the Nine", "Knights.esp",
     re.compile(r"(?<![A-Za-z])Knights of the Nine(?![A-Za-z])", re.I),
     ("나인 디바인의 기사단", "나인 디바인 기사단", "나인 기사단"),
     "나인의 기사단"),
    ("Crusader equipment", "Knights.esp",
     re.compile(r"(?<![A-Za-z])(?:of the Crusader|Crusader\s+(?:Sword|Shield|Helm|Helmet|Gauntlets|Boots|Cuirass|Mace))(?![A-Za-z])", re.I),
     ("성전사",), "성기사"),
)
BOOK2 = ("Oblivion.esm", b"BOOK", 0x00022B05, b"FULL")
BOOK2_EN = "Mythic Dawn Commentaries 2"


def verify_canonical(path: Path) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    if digest.hexdigest() != CANONICAL_SHA256:
        raise ValueError("Issue #8 original canonical CSV SHA-256 drift")


def correct_reporter_terms(translations, canonical_csv: Path | None = None):
    """Preflight every named record and count before changing any in-memory bytes.

    Returns counts per glossary entity. The existing separate BOOK #2 correction
    may have already applied, so its one normalized form is an explicit exception.
    """
    if canonical_csv is not None:
        verify_canonical(canonical_csv)
    planned = []
    counts = Counter()
    seen = set()
    book2_already_fixed = False
    for key, items in translations.items():
        target, kind, formid, field = key
        for index, item in enumerate(items):
            identity = (key, item.source, item.editor_id, item.occurrence, item.line)
            if item.source != target or not item.korean.endswith(b"\0"):
                continue
            if item.korean[:-1].count(b"\0"):
                raise ValueError(f"Issue #8 invalid NUL in {identity}")
            try:
                before = item.korean[:-1].decode("utf-8")
            except UnicodeDecodeError as e:
                raise ValueError(f"Issue #8 invalid UTF-8 in {identity}") from e
            after = before
            if key == BOOK2 and item.english == BOOK2_EN:
                book2_already_fixed = ("미식 던 논평집 2" in before)
            applied = []
            for name, sources, english, aliases, canonical in RULES:
                if item.source not in sources.split(";") or not english.search(item.english):
                    continue
                if canonical in after:
                    # A mixed form needs line-by-line human review; do not
                    # silently rewrite part of its translation.
                    continue
                found = [alias for alias in aliases if alias in after]
                if len(found) != 1:
                    continue
                new = after.replace(found[0], canonical)
                if new == after:
                    continue
                after = new
                applied.append(name)
            if key == BOOK2 and item.english == BOOK2_EN and after == "미식 던 주석서 2":
                after = "미식 던 논평집 2"
            if after == before:
                continue
            if identity in seen:
                raise ValueError("Issue #8 duplicate translation identity")
            seen.add(identity)
            # A name-only edit must never change markup or placeholder syntax.
            marker = re.compile(r"<[^>]*>|%(?:[-+0#]*\d*(?:\.\d+)?[a-zA-Z%])|@[A-Za-z0-9_#]+")
            if marker.findall(before) != marker.findall(after):
                raise ValueError(f"Issue #8 format marker drift: {identity}")
            if [c for c in before if c in "\r\n"] != [c for c in after if c in "\r\n"]:
                raise ValueError(f"Issue #8 newline drift: {identity}")
            for name in applied:
                counts[name] += 1
            planned.append((key, index, item, after.encode("utf-8") + b"\0"))
    expected = EXPECTED.copy()
    if book2_already_fixed:
        expected["Mythic Dawn"] -= 1
    if dict(counts) != expected:
        raise ValueError(f"Issue #8 candidate drift: expected {expected}, actual {dict(counts)}")
    for key, index, item, corrected in planned:
        translations[key][index] = replace(item, korean=corrected)
    return dict(counts)
