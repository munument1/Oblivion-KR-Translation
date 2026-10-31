"""Source-scoped correction for the Claude issue #8 Crate mistranslations.

The original 47k-row canonical file remains immutable. Only direct Oblivion.esm
CONT/FULL rows whose English is exactly "Crate" and old UTF-8 text is exactly
"의자" are corrected. All other translations and record keys remain unchanged.
"""
from dataclasses import replace

SOURCE = "Oblivion.esm"
OLD = "의자".encode("utf-8") + b"\0"
NEW = "상자".encode("utf-8") + b"\0"
EXPECTED = 38


def correct_crate_names(translations, expected=EXPECTED):
    """Correct only audited Crate rows, aborting on corpus drift."""
    matches = []
    for key, candidates in translations.items():
        target, kind, formid, field = key
        if (target, kind, field) != (SOURCE, b"CONT", b"FULL"):
            continue
        for index, item in enumerate(candidates):
            if (item.source == SOURCE and item.record_type == b"CONT"
                    and item.field == b"FULL" and item.english == "Crate"
                    and item.korean == OLD):
                matches.append((key, index, item))

    identities = [(key, item.editor_id, item.occurrence)
                  for key, _, item in matches]
    if len(matches) != expected or len(set(identities)) != len(identities):
        raise ValueError(
            f"Claude issue #8 Crate identity/count drift: "
            f"expected {expected} unique, found {len(matches)} "
            f"({len(set(identities))} unique)"
        )
    for key, index, item in matches:
        translations[key][index] = replace(item, korean=NEW)
    return len(matches)
