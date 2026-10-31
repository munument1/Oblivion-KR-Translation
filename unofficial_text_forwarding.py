"""Main-game translation authority for audited patch text fields.

Manifest entries pin both English sources, master ownership, record signature,
EditorID and occurrence. Reordered responses/journals name the original main
occurrence explicitly. Intentional content changes keep patch-specific text.
"""
import csv
import hashlib
from pathlib import Path

from build_vanilla_overlay import load_translations, Translation
from book_title_overrides import apply_book_title_overrides
from unofficial_target_variants import load_variants, apply_variant


def main_translations(root, *, include_issue8=False):
    table = load_translations(root / 'canonical_translation_v2.csv',
        extra_paths=(root / 'canonical_ui_supplement_v1.csv',
                     root / 'canonical_nexus_56688_fur_v1.csv'),
        encoded_column='obcjk_utf8_hex')
    if include_issue8:
        from claude_issue8_crate import correct_crate_names
        from claude_issue8_amber import correct_amber_equipment_names
        correct_crate_names(table)
        correct_amber_equipment_names(table)
    apply_book_title_overrides(table, root / 'canonical_book_title_overrides_v1.csv')
    if include_issue8:
        from issue8_reporter_term_patch import correct_reporter_terms
        from issue8_remaining_term_patch import correct_remaining_glossary_names
        from issue8_context_verified_patch import correct_context_verified_names
        from issue8_cupboard_patch import correct_cupboard_names
        from issue8_glossary_exceptions import correct_glossary_exceptions
        correct_reporter_terms(table, root / 'canonical_translation_v2.csv')
        correct_remaining_glossary_names(table, root / 'canonical_translation_v2.csv')
        correct_context_verified_names(table, root / 'canonical_translation_v2.csv')
        correct_cupboard_names(table, root / 'canonical_translation_v2.csv')
        correct_glossary_exceptions(table, root / 'canonical_translation_v2.csv')
    with (root / 'canonical_locations_v2.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            item = Translation(row['effective_source'], row['record_type'].encode(),
                int(row['raw_formid'], 16), row['field'].encode(), row['old_english'],
                bytes.fromhex(row['obcjk_utf8_hex']), 0,
                row['editor_id'].encode() if row['editor_id'] else None,
                int(row.get('occurrence') or 0))
            table[(item.source, item.record_type, item.formid, item.field)].append(item)
    return table


def source_sha(text):
    return hashlib.sha256(text.encode('cp1252') + b'\0').hexdigest()


def load_text_forwarding(root: Path):
    table = main_translations(root)
    current = main_translations(root, include_issue8=True)
    # Correct reviewed variant outputs AFTER old-language replacements are
    # applied. Applying glossary fixes before apply_variant invalidates its
    # pinned patch-specific old-wording checks and can delete patch repairs.
    context = {
        ("Unofficial Oblivion Patch.esp", b"QUST", 0x0001E72D, b"CNAM"): ("미씩 던", "미식 던"),
        ("Unofficial Oblivion Patch.esp", b"BOOK", 0x00024549, b"DESC"): ("셰이딘홀", "체이딘할"),
        ("Unofficial Oblivion Patch.esp", b"BOOK", 0x00024561, b"DESC"): ("셰이딘홀", "체이딘할"),
        ("Unofficial Oblivion Patch.esp", b"INFO", 0x0002B09F, b"NAM1"): ("아일레이드", "에일리드"),
        ("Unofficial Oblivion Patch.esp", b"QUST", 0x00036337, b"CNAM"): ("쉐이딘홀", "체이딘할"),
        ("Unofficial Shivering Isles Patch.esp", b"BOOK", 0x0007F3E7, b"DESC"): ("약탈자", "습격자"),
    }
    variants = load_variants(root)
    patch_rows = {}
    for name in ('canonical_unofficial_translation_v2.csv', 'canonical_unofficial_locations_v2.csv', 'canonical_locations_v2.csv', 'unofficial_extra_sources_v1.csv'):
        with (root / name).open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                key = (row['effective_source'], row['record_type'].encode(),
                       int(row['raw_formid'], 16), row['field'].encode(),
                       row['editor_id'].encode(), int(row.get('occurrence') or 0))
                patch_rows.setdefault(key, source_sha(row['old_english']))
    result = {}
    with (root / 'unofficial_text_forwarding_v1.csv').open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            key = (row['plugin'], row['record_type'].encode(), int(row['formid'], 16),
                   row['field'].encode(), row['editor_id'].encode(), int(row['occurrence']))
            if key in result:
                raise ValueError(f'Duplicate text forwarding: {key}')
            if patch_rows[key] != row['patch_source_sha256']:
                raise ValueError(f'Changed tracked patch source: {key}')
            owner, base_fid = row['owner'], int(row['base_formid'], 16)
            items = [x for x in table.get((owner, key[1], base_fid, key[3]), ())
                     if x.source == owner and (x.editor_id or b'') == key[4]
                     and x.occurrence == int(row['base_occurrence'])
                     and source_sha(x.english) == row['base_source_sha256']]
            if not items:
                raise ValueError(f'Changed tracked main source: {key}')
            target = items[-1].korean
            if row['policy'] not in ('forward', 'patch'):
                raise ValueError(f'Unknown alignment policy: {key}')
            if not target.endswith(b'\0') or b'\0' in target[:-1]:
                raise ValueError(f'Invalid main-game target: {key}')
            target[:-1].decode('utf-8', errors='strict')
            policy = row['policy']
            if key in variants:
                variant_target = apply_variant(variants.pop(key), row, target, table)
                if variant_target is not None:
                    target = variant_target
                    policy = 'forward'
            if policy == 'forward':
                reviewed = [x for x in current.get((owner, key[1], base_fid, key[3]), ())
                            if x.source == owner and (x.editor_id or b'') == key[4]
                            and x.occurrence == int(row['base_occurrence'])
                            and source_sha(x.english) == row['base_source_sha256']]
                if not reviewed:
                    raise ValueError(f'Missing corrected source for patch target: {key}')
                old_base, corrected = items[-1].korean, reviewed[-1].korean
                if target == old_base:
                    target = corrected
                elif corrected != old_base:
                    patch_context = context.get(key[:4])
                    if patch_context:
                        old_word, new_word = patch_context
                        if old_word in target[:-1].decode('utf-8'):
                            target = target[:-1].decode('utf-8').replace(old_word, new_word).encode('utf-8') + b'\0'
                        # Deliberately abbreviated journal omits the city; do not restore omitted text.
                    else:
                        # A different reviewed translation may deliberately omit or
                        # reword the mentioned name; do not force the main string.
                        # The released-ESP compatibility audit handles exact overlap
                        # records and preserves other reviewed patch-specific prose.
                        pass
            result[key] = (owner, base_fid, row['patch_source_sha256'], target, policy)
    if variants:
        raise ValueError('Reviewed variants have no audited forwarding identity')
    return result


def forward_text(table, plugin, kind, fid, field, editor, occurrence, identity, raw):
    item = (table or {}).get((plugin, kind, fid, field, editor, occurrence))
    if item is None:
        return None
    owner, base_fid, expected, target, policy = item
    if identity != (owner, base_fid):
        return None
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'Changed patch text source: {plugin} {kind!r} {fid:08X}')
    return target if policy == 'forward' else None
