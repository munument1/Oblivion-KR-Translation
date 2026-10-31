"""Issue #6: source-pinned BOOK/DESC line-break correction.

Only the explicit frozen manifest is eligible. The writer never changes the
English BOOK source or its HTML; it adjusts the known UTF-8 Korean payload at
the last translation-selection stage, after UOP's base-game forwarding.

Use --make-manifest once to prepare the reviewed snapshot; do not regenerate
it during the release build. The normal --check operation verifies every pin.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "issue6_book_markup_manifest_v1.json"
BASE = "Oblivion.esm"
UOP = "Unofficial Oblivion Patch.esp"
BR = re.compile(r"<br>", re.IGNORECASE)
HTML = re.compile(r"<\s*/?\s*(?:br|div|font|img|p)\b", re.IGNORECASE)
SHOP = re.compile(r"Clutter(?:[A-Za-z]+Shop\d+|ShoppingList\d+)$")
JOURNAL_ID = "00038B2F"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fix_breaks(body: bytes, mode: str) -> bytes:
    if not body.endswith(b"\0") or b"\0" in body[:-1]:
        raise ValueError("BOOK/DESC must be a single NUL-terminated string")
    text = body[:-1].decode("utf-8", errors="strict")
    if not BR.search(text):
        raise ValueError("expected literal <br> markup is absent")
    if mode == "plain_newlines":
        # There is already a physical newline in many legacy translations
        # immediately AFTER the literal tag. Keep that newline, avoiding a
        # duplicate blank paragraph. A stand-alone tag becomes a real CRLF.
        updated = BR.sub(lambda m: "" if re.match(r"[\r\n]", text[m.end():])
                         else "\r\n", text)
    elif mode == "uop_journal_original_br":
        # The original UOP journal contains uppercase <BR> markup; preserve
        # its outer font pair and the original Windows newline convention.
        # The vanilla canonical book body lacks this UOP-only HTML wrapper.
        if re.search(r"<\s*/?\s*font\b", text, re.IGNORECASE):
            raise ValueError("forwarded UOP journal unexpectedly contains a font tag")
        updated = BR.sub("<BR>", text)
        updated = updated.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        updated = "<font face=5>\r\n<BR>\r\n" + updated + "\r\n</font>"
    else:
        raise ValueError("unexpected correction mode")
    if BR.search(updated) and mode == "plain_newlines":
        raise AssertionError("plain text still has literal <br>")
    return updated.encode("utf-8") + b"\0"


def csv_books(name: str) -> dict[tuple[str, str], dict]:
    result = {}
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["record_type"] != "BOOK" or row["field"] != "DESC":
                continue
            key = (row["effective_source"], row["raw_formid"])
            if key in result:
                raise ValueError(f"duplicate BOOK/DESC row {key}")
            result[key] = row
    return result


def _raw_source(row: dict) -> bytes:
    raw = row["old_english"].encode("cp1252", errors="strict") + b"\0"
    # Vanilla canonical does not carry source_sha256; its exact source is
    # frozen in our manifest. UOP canonical does carry the original digest.
    if row.get("source_sha256") and digest(raw) != row["source_sha256"]:
        raise ValueError(f"source hash disagrees with CSV {row['raw_formid']}")
    return raw


def _translated(row: dict) -> bytes:
    value = bytes.fromhex(row["obcjk_utf8_hex"])
    if not value.endswith(b"\0") or b"\0" in value[:-1]:
        raise ValueError(f"invalid translation {row['raw_formid']}")
    value[:-1].decode("utf-8", errors="strict")
    return value


def candidate_manifest() -> list[dict]:
    """Snapshot the narrow, human-selected journal + shop-paper set.

    UOP forwards eight of the shop notes and the journal from the main-game
    canonical table. Pin its different source and the actually forwarded
    vanilla target separately, since its own canonical row isn't final.
    """
    base = csv_books("canonical_translation_v2.csv")
    uop = csv_books("canonical_unofficial_translation_v2.csv")
    uop_forwards = {}
    with (ROOT / "unofficial_text_forwarding_v1.csv").open(
            encoding="utf-8-sig", newline="") as stream:
        for forwarded in csv.DictReader(stream):
            if (forwarded["plugin"], forwarded["record_type"], forwarded["field"]) != (
                    UOP, "BOOK", "DESC"):
                continue
            fid = forwarded["formid"]
            if fid in uop_forwards:
                raise ValueError(f"duplicate UOP BOOK/DESC forwarding {fid}")
            uop_forwards[fid] = forwarded
    results = []
    for (plugin, formid), row in base.items():
        if plugin != BASE or not (formid == JOURNAL_ID or SHOP.fullmatch(row["editor_id"])):
            continue
        original = _raw_source(row)
        target = _translated(row)
        if HTML.search(row["old_english"]) or not BR.search(target[:-1].decode("utf-8")):
            if formid == JOURNAL_ID:
                raise ValueError(f"journal source unexpectedly changed: {formid}")
            continue  # Shopping lists with original HTML need separate game testing.
        mode = "plain_newlines"
        updated = fix_breaks(target, mode)
        entry = {
            "plugin": plugin, "record_type": "BOOK", "formid": formid,
            "field": "DESC", "editor_id": row["editor_id"], "occurrence": int(row["occurrence"]),
            "source_sha256": digest(original), "prior_ko_sha256": digest(target),
            "corrected_ko_sha256": digest(updated), "mode": mode,
            "original_br_count": 0, "prior_ko_br_count": len(BR.findall(target[:-1].decode("utf-8"))),
        }
        results.append(entry)
        uop_row = uop.get((UOP, formid))
        if uop_row is not None:
            if uop_row["editor_id"] != row["editor_id"]:
                raise ValueError(f"UOP editor mismatch {formid}")
            uop_source = _raw_source(uop_row)
            forwarding = uop_forwards.get(formid)
            if (forwarding is None or forwarding["policy"] != "forward"
                    or forwarding["owner"] != BASE
                    or forwarding["base_formid"] != formid
                    or forwarding["editor_id"] != row["editor_id"]
                    or forwarding["occurrence"] != row["occurrence"]
                    or forwarding["patch_source_sha256"] != digest(uop_source)
                    or forwarding["base_source_sha256"] != digest(original)):
                raise ValueError(f"UOP BOOK forwarding is not exact: {formid}")
            # The MS52 UOP source itself uses <BR>; its translated source
            # text must retain book markup in the selected final output.
            uop_mode = "uop_journal_original_br" if formid == JOURNAL_ID else mode
            if formid != JOURNAL_ID and HTML.search(uop_row["old_english"]):
                raise ValueError(f"UOP shop paper unexpectedly has HTML {formid}")
            results.append({
                **entry, "plugin": UOP, "source_sha256": digest(uop_source),
                "mode": uop_mode, "corrected_ko_sha256": digest(fix_breaks(target, uop_mode)),
                "original_br_count": len(BR.findall(uop_row["old_english"])),
                # The UOP translator's canonical target differs; final
                # forwarding must be checked by the release-side integrator.
                "selection": "forwarded_from_Oblivion.esm",
            })
    return sorted(results, key=lambda e: (e["plugin"], e["formid"]))


@lru_cache(maxsize=1)
def load_manifest(path: Path = MANIFEST) -> dict[tuple[str, str], dict]:
    values = json.loads(path.read_text(encoding="utf-8"))
    keyed = {}
    for entry in values:
        key = (entry["plugin"], entry["formid"])
        if key in keyed:
            raise ValueError(f"duplicate manifest entry: {key}")
        if any(not re.fullmatch("[a-f0-9]{64}", entry[name])
               for name in ("source_sha256", "prior_ko_sha256", "corrected_ko_sha256")):
            raise ValueError(f"invalid SHA pin: {key}")
        keyed[key] = entry
    return keyed


def correct_selected_book(plugin: str, formid: int, editor_id: bytes,
                          original: bytes, chosen: bytes | None,
                          manifest: dict[tuple[str, str], dict] | None = None) -> bytes | None:
    """Call on the final BOOK/DESC replacement after forwarding.

    A None or non-target leaves normal builder behavior intact; an eligible
    source or selected target mismatch fails closed instead of guessing.
    """
    pins = load_manifest() if manifest is None else manifest
    entry = pins.get((plugin, f"{formid:08X}"))
    if entry is None:
        return chosen
    if editor_id.rstrip(b"\0").decode("ascii", errors="strict") != entry["editor_id"]:
        raise ValueError(f"issue #6 editor mismatch: {plugin} {formid:08X}")
    if digest(original) != entry["source_sha256"]:
        raise ValueError(f"issue #6 source mismatch: {plugin} {formid:08X}")
    if chosen is None:
        raise ValueError(f"issue #6 candidate missing: {plugin} {formid:08X}")
    if digest(chosen) == entry["corrected_ko_sha256"]:
        return chosen
    if digest(chosen) != entry["prior_ko_sha256"]:
        raise ValueError(f"issue #6 translation mismatch: {plugin} {formid:08X}")
    updated = fix_breaks(chosen, entry["mode"])
    if digest(updated) != entry["corrected_ko_sha256"]:
        raise AssertionError(f"issue #6 corrected SHA mismatch: {plugin} {formid:08X}")
    return updated


def validate_snapshot() -> dict:
    actual = candidate_manifest()
    expected = list(load_manifest().values())
    if actual != expected:
        raise ValueError("issue #6 manifest stale: source or selected translation changed")
    return {
        "manifest_sha256": digest(MANIFEST.read_bytes()), "cases": len(actual),
        "vanilla": sum(x["plugin"] == BASE for x in actual),
        "uop_forwarded": sum(x["plugin"] == UOP for x in actual),
        "game_runtime_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make-manifest", action="store_true", help="prepare new frozen manifest")
    args = parser.parse_args()
    if args.make_manifest:
        if MANIFEST.exists():
            raise FileExistsError("Refusing to replace pinned manifest")
        MANIFEST.write_text(json.dumps(candidate_manifest(), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps(validate_snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
