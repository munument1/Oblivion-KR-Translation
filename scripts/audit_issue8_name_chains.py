#!/usr/bin/env python3
"""Issue #8: source-anchored, NON-MUTATING name consistency audit.

This outputs candidates only. Do not treat a lexical mismatch as a translation
error, and never rewrite canonical CSV, glossary, ESM/ESP or release assets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

# The entries below are review anchors, not forced replacements.
# Cheydinhal's glossary value conflicts with live map/world names.
TERMS = {
    'Cheydinhal': {
        'en': re.compile(r'(?<![A-Za-z])Cheydinhal(?![A-Za-z])', re.I),
        'reference': '체이딘할',
        'variants': ('셰이딘홀', '쉐이딘홀', '체이딘홀', '체이딘할'),
        'priority': 1,
    },
    'Mythic Dawn': {
        'en': re.compile(r'(?<![A-Za-z])Mythic Dawn(?![A-Za-z])', re.I),
        'reference': '미식 던',
        'variants': ('미식 던', '미씩 던', '미시크 던'),
        'priority': 2,
    },
    'Mysterium Xarxes': {
        'en': re.compile(r'(?<![A-Za-z])Mysterium Xarxes(?![A-Za-z])', re.I),
        'reference': '작시스의 신비',
        'variants': ('작시스의 신비', '자서스의 신비', '미스테리움 자서스', '미스테리움 작시스'),
        'priority': 2,
    },
    'Knights of the Nine': {
        'en': re.compile(r'(?<![A-Za-z])Knights of the Nine(?![A-Za-z])', re.I),
        'reference': '나인의 기사단',
        'variants': ('나인의 기사단', '나인 디바인의 기사단', '나인 디바인 기사단', '나인 기사단'),
        'priority': 3,
    },
    'Crusader equipment': {
        'en': re.compile(
            r'(?<![A-Za-z])(?:of the Crusader|Crusader\s+(?:Sword|Shield|Helm|Helmet|Gauntlets|Boots|Cuirass|Mace))(?![A-Za-z])', re.I),
        'reference': '성기사',
        'variants': ('성기사', '성전사'),
        'priority': 3,
    },
}
HEADERS = (
    'priority', 'term', 'classification', 'surface', 'effective_source',
    'record_type', 'raw_formid', 'editor_id', 'field', 'occurrence',
    'old_english', 'current_korean', 'reference_not_mandatory',
    'found_variants', 'korean_sha256', 'source_csv', 'line_number',
)


def surface_of(record_type, field):
    if record_type in ('CELL', 'WRLD', 'REFR', 'REGN'):
        return 'LOCATION'
    if record_type in ('INFO', 'DIAL'):
        return 'DIALOGUE'
    if record_type == 'BOOK':
        return 'BOOK_TITLE' if field == 'FULL' else 'BOOK_BODY'
    if record_type == 'QUST':
        return 'QUEST_JOURNAL' if field == 'CNAM' else 'QUEST_OTHER'
    return 'FULL_NAME' if field == 'FULL' else 'OTHER'


def analyze_row(row, path, line):
    english = row.get('old_english', '')
    korean = row.get('obcjk_unicode_text', '')
    if not korean and row.get('obcjk_utf8_hex'):
        try:
            korean = bytes.fromhex(row['obcjk_utf8_hex']).rstrip(b'\0').decode('utf-8')
        except (UnicodeError, ValueError):
            pass
    found = []
    for term, spec in TERMS.items():
        if not spec['en'].search(english):
            continue
        matches = [v for v in spec['variants'] if v in korean]
        if not matches:
            classification = 'CONTEXT_CHECK'
        elif len(matches) > 1:
            classification = 'MIXED_VARIANTS_REVIEW'
        elif spec['reference'] not in korean:
            classification = 'REFERENCE_CONFLICT_REVIEW'
        else:
            classification = 'REFERENCE_MATCH'
        found.append({
            'priority': spec['priority'], 'term': term,
            'classification': classification,
            'surface': surface_of(row.get('record_type', ''), row.get('field', '')),
            'effective_source': row.get('effective_source', ''),
            'record_type': row.get('record_type', ''),
            'raw_formid': row.get('raw_formid', ''),
            'editor_id': row.get('editor_id', ''),
            'field': row.get('field', ''),
            'occurrence': row.get('occurrence', ''),
            'old_english': english, 'current_korean': korean,
            'reference_not_mandatory': spec['reference'],
            'found_variants': ' | '.join(matches),
            'korean_sha256': hashlib.sha256(korean.encode('utf-8')).hexdigest(),
            'source_csv': path.name, 'line_number': line,
        })
    return found


def build(translation_csv, location_csv, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    hits, source_hashes, input_rows = [], {}, Counter()
    for path in (translation_csv, location_csv):
        sha = hashlib.sha256()
        with path.open('rb') as f:
            for data in iter(lambda: f.read(1024 * 1024), b''):
                sha.update(data)
        source_hashes[path.name] = sha.hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            required = {'effective_source', 'record_type', 'raw_formid', 'field', 'old_english'}
            if not required <= set(reader.fieldnames or ()):
                raise ValueError(f'{path.name}: missing identity fields')
            if not {'obcjk_unicode_text', 'obcjk_utf8_hex'} & set(reader.fieldnames or ()):
                raise ValueError(f'{path.name}: missing Korean display fields')
            for line, row in enumerate(reader, 2):
                input_rows[path.name] += 1
                hits.extend(analyze_row(row, path, line))
    hits.sort(key=lambda r: (r['priority'], r['term'], r['surface'],
                             r['effective_source'], r['record_type'],
                             r['raw_formid'], r['field'], r['occurrence'],
                             r['line_number']))
    csv_out = outdir / 'ISSUE8_NAME_CHAIN_CANDIDATES.csv'
    with csv_out.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(hits)
    groups = {}
    for term, spec in TERMS.items():
        term_hits = [h for h in hits if h['term'] == term]
        groups[term] = {
            'reference_not_mandatory': spec['reference'],
            'total': len(term_hits),
            'classification': dict(Counter(h['classification'] for h in term_hits)),
            'surface': dict(Counter(h['surface'] for h in term_hits)),
            'observed_variants': dict(Counter(
                v for h in term_hits for v in h['found_variants'].split(' | ') if v)),
            'examples_needing_review': [
                {k: h[k] for k in ('effective_source', 'record_type', 'raw_formid',
                                  'editor_id', 'field', 'occurrence',
                                  'old_english', 'current_korean', 'classification')}
                for h in term_hits if h['classification'] != 'REFERENCE_MATCH'
            ][:12],
        }
    summary = {
        'warning': 'Static candidate audit only; NO row is automatically approved for edit.',
        'sources_sha256': source_hashes,
        'input_records': dict(input_rows),
        'candidate_rows': len(hits),
        'terms': groups,
        'required_followup': [
            'Resolve Cheydinhal glossary 체이딘할 vs world/map 셰이딘홀.',
            'Compare source/plugin/FormID and FULL, INFO/DIAL, BOOK, QUST CNAM chains.',
            'Preserve Korean particles, formatting, and source English when editing.',
            'Check built output and gameplay before release.',
        ],
    }
    (outdir / 'ISSUE8_NAME_CHAIN_SUMMARY.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--translations', type=Path, default=Path('canonical_translation_v2.csv'))
    parser.add_argument('--locations', type=Path, default=Path('canonical_locations_v2.csv'))
    parser.add_argument('--outdir', type=Path, default=Path('issue8_name_review'))
    args = parser.parse_args()
    summary = build(args.translations, args.locations, args.outdir)
    print(json.dumps({
        'candidate_rows': summary['candidate_rows'],
        'groups': {k: v['classification'] for k, v in summary['terms'].items()},
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
