"""Forward audited BOOK identities even when a patch corrected English typos.

Both English sources are hash-pinned. No fuzzy English matching or bare FormID
matching is permitted. Intentional content changes are enumerated as exceptions.
The canonical main-game UTF-8 target is read on every build, not copied here.
"""
import csv
import hashlib
from pathlib import Path


def source_hash(text):
    return hashlib.sha256(text.encode('cp1252') + b'\0').hexdigest()


def load_book_forwarding(root: Path):
    def rows(name):
        with (root / name).open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))

    base = {}
    for row in rows('canonical_translation_v2.csv'):
        if row['record_type'] == 'BOOK' and row['field'] in ('FULL', 'DESC'):
            key = (row['effective_source'], row['raw_formid'], row['field'],
                   row['editor_id'], row['occurrence'])
            if key in base:
                raise ValueError(f'Duplicate canonical book identity: {key}')
            base[key] = row
    patch = {}
    for row in rows('canonical_unofficial_translation_v2.csv'):
        if row['record_type'] == 'BOOK':
            key = (row['effective_source'], row['raw_formid'], row['field'],
                   row['editor_id'], row['occurrence'])
            if key in patch:
                raise ValueError(f'Duplicate patch book identity: {key}')
            patch[key] = row
    result = {}
    for row in rows('unofficial_book_forwarding_v1.csv'):
        key = (row['plugin'], row['formid'], row['field'], row['editor_id'], row['occurrence'])
        base_key = (row['owner'], row['base_formid'], row['field'], row['editor_id'], row['occurrence'])
        old, canonical = patch[key], base[base_key]
        if (source_hash(old['old_english']) != row['patch_source_sha256']
                or source_hash(canonical['old_english']) != row['base_source_sha256']):
            raise ValueError(f'Changed audited book source: {key}')
        target = bytes.fromhex(canonical['obcjk_utf8_hex'])
        if not target.endswith(b'\0') or b'\0' in target[:-1]:
            raise ValueError(f'Invalid canonical book target: {key}')
        if target[:-1].decode('utf-8') != canonical['new_korean']:
            raise ValueError(f'Inconsistent canonical book target: {key}')
        lookup = (row['plugin'], int(row['formid'], 16), row['field'].encode(),
                  row['editor_id'].encode(), int(row['occurrence']))
        if lookup in result:
            raise ValueError(f'Duplicate book forwarding: {key}')
        result[lookup] = (row['owner'], int(row['base_formid'], 16),
                          row['patch_source_sha256'], target, row['policy'])
    return result


def forward_book(table, plugin, formid, field, editor, occurrence, identity, raw):
    item = (table or {}).get((plugin, formid, field, editor, occurrence))
    if item is None:
        return None
    owner, base_formid, expected, target, policy = item
    if identity != (owner, base_formid):
        return None
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'Changed patch BOOK source: {plugin} {formid:08X}')
    return target if policy == 'forward' else None
