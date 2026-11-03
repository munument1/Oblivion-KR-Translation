"""Read-only risk audit of historical canonical translation memory.

A candidate is NOT proof that a translation is wrong. No automatic edits.
"""
from pathlib import Path
from collections import Counter
import argparse
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
GLOSS = re.compile(r'(?<=[가-힣])\([A-Za-z][^()]{1,160}\)')
HTML = re.compile(r'<[^>]*>')
LATIN = re.compile(r'[A-Za-z]')

def audit(path):
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            sha.update(block)
    counts, kinds, sources, examples = Counter(), Counter(), Counter(), []
    csv.field_size_limit(100_000_000)
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'new_korean', 'old_english', 'obcjk_utf8_hex',
                    'record_type', 'field', 'raw_formid'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('Historical canonical schema drift')
        for row in reader:
            counts['rows'] += 1
            ko = row['new_korean']
            en = row['old_english']
            kinds[row['record_type']] += 1
            sources[row.get('effective_source', '')] += 1
            reasons = []
            if GLOSS.search(ko):
                counts['english_gloss_candidates'] += 1
                reasons.append('english_gloss')
            if LATIN.search(HTML.sub('', ko)):
                counts['target_has_latin_letters'] += 1
                reasons.append('latin_letters')
            if not ko.strip() and en.strip():
                counts['empty_target'] += 1
                reasons.append('empty_target')
            if '\ufffd' in ko:
                counts['replacement_character'] += 1
                reasons.append('replacement_character')
            encoded = row['obcjk_utf8_hex']
            if encoded:
                try:
                    raw = bytes.fromhex(encoded)
                    if not raw.endswith(b'\0') or b'\0' in raw[:-1]:
                        raise ValueError('Invalid target NUL framing')
                    compiled = raw[:-1].decode('utf-8')
                except (UnicodeError, ValueError):
                    counts['invalid_utf8_hex'] += 1
                    reasons.append('invalid_utf8_hex')
                else:
                    if compiled != ko:
                        counts['text_and_utf8_hex_disagree'] += 1
                        reasons.append('unicode_hex_disagreement')
            else:
                counts['missing_utf8_hex'] += 1
            if reasons:
                counts['flagged_rows_union'] += 1
                if len(examples) < 60:
                    examples.append({'source': row.get('effective_source',''),
                        'type': row['record_type'], 'formid': row['raw_formid'],
                        'field': row['field'], 'reasons': reasons,
                        'english_preview': en[:125], 'korean_preview': ko[:125]})
    return {
        'source': path.name, 'sha256': sha.hexdigest(),
        'status': 'unreviewed_historical_memory',
        'notice': 'Counts are review candidates, not proven errors; never reuse this CSV alone.',
        'counts': dict(counts),
        'record_types': dict(kinds.most_common(30)),
        'sources': dict(sources.most_common(20)),
        'examples': examples,
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--canonical', type=Path, default=ROOT / 'canonical_translation_v2.csv')
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    data = audit(args.canonical)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(data['counts'], ensure_ascii=False))

if __name__ == '__main__':
    main()
