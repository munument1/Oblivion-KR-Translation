"""Audit every tracked patch text against current main-game translations.

Only reviewed, explicit spelling equivalents are normalized for classification.
Runtime forwarding uses the generated exact identity and dual-source hash pins.
"""
import argparse
import csv
import difflib
import json
import gzip
from collections import Counter
from pathlib import Path
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_unofficial_release import read_records, reviewed_identity
from build_vanilla_overlay import normalize_source_text
from unofficial_text_forwarding import main_translations, source_sha

# Reviewed English spelling equivalents. No edit-distance or fuzzy matching.
SPELLINGS = dict(pair.split('=') for pair in '''
prefering=preferring dreamword=dreamworld venemous=venomous vengence=vengeance
cermonial=ceremonial putrification=putrefaction ayelid=ayleid ayeleid=ayleid
ashame=a_shame depair=despair jyggylag=jyggalag sorceror=sorcerer
competiton=competition daugher=daughter forebearance=forbearance geneology=genealogy
millenia=millennia phylacetary=phylactery resistence=resistance cameleon=chameleon
cowardness=cowardice apparenlty=apparently undergound=underground
accomodated=accommodated accomodation=accommodation acolytle=acolyte addtion=addition
beleive=believe brough=brought cemetary=cemetery choosen=chosen
commemerate=commemorate commited=committed commiting=committing
curiousity=curiosity decending=descending decieve=deceive delievered=delivered
desposits=deposits distict=district ecstacy=ecstasy embarassing=embarrassing
endevour=endeavor eveyone=everyone execellent=excellent exhausing=exhausting
fullfill=fulfill hearby=hereby
inflitrate=infiltrate inkeeper=innkeeper inseperable=inseparable
irresistably=irresistibly kynsman=kinsman loathesome=loathsome
moreso=more_so obessing=obsessing obscenties=obscenities occassions=occasions
occured=occurred posioned=poisoned prefecting=perfecting publically=publicly
pygmys=pygmies reassinged=reassigned recinded=rescinded recuits=recruits
regiment=regimen retreive=retrieve seige=siege speciality=specialty
strategem=stratagem tyrranical=tyrannical unsecure=insecure unsual=unusual
unusal=unusual vegeance=vengeance visitng=visiting vistor=visitor vists=visits
whatsover=whatsoever souless=soulless brainrot=brain_rot
arenabasinrenewel=arena_basin_renewal
khajitt=khajiit khajjit=khajiit sumerset=summerset
akiviri=akaviri akavari=akaviri cheyhindal=cheydinhal cheydhinhal=cheydinhal
cheydinhaal=cheydinhal hieronymous=hieronymus guilded=gilded
teekeus=teekeeus teeekeeus=teekeeus nirnoot=nirnroot
shelgorath=sheogorath shegorath=sheogorath illiac=iliac
'''.split() if '=' in pair)


def spelling_key(text):
    text = re.sub(r'<[^>]+>', '', text).lower()
    for old, new in (("i'm", 'i am'), ("you're", 'you are'), ("we're", 'we are'),
                     ("they're", 'they are'), ("i've", 'i have'), ("i'll", 'i will'),
                     ("you'll", 'you will'), ("it's", 'it is')):
        text = text.replace(old, new)
    text = re.sub(r'\b\w+\b', lambda m: SPELLINGS.get(m[0], m[0]).replace('_', ' '), text)
    return re.sub(r'[^a-z0-9]', '', text)


def spelling_equivalent(left, right):
    if spelling_key(left) == spelling_key(right):
        return True
    # English articles and a few reviewed inflection repairs do not change
    # the Korean referent, quantities, conditions or directions.
    a = re.findall(r"[a-z0-9]+", left.lower())
    b = re.findall(r"[a-z0-9]+", right.lower())
    edits = [(a[i:j], b[k:l]) for op,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if op != 'equal']
    articles = {'a','an','the'}
    safe = {('know','known'),('follower','followers'),('instruction','instructions'),
            ('prepare','prepares'),('easy','easily'),('did','do'),('been','be'),
            ('past','passed'),('passed','past'),('recuits','recruits')}
    return bool(edits) and all(
        (set(old + new) <= articles) or
        (len(old) == len(new) == 1 and (old[0],new[0]) in safe)
        for old,new in edits)


def audit(baseline, output, manifest):
    table = main_translations(ROOT)
    book_policies = {}
    with (ROOT / 'unofficial_book_forwarding_v1.csv').open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            book_policies[(row['plugin'], row['formid'], row['field'], int(row['occurrence']))] = row
    records = {p.name: read_records(p) for p in baseline.glob('*.esp')}
    report, forwarding, seen = [], [], set()
    for filename in ('canonical_unofficial_translation_v2.csv', 'canonical_unofficial_locations_v2.csv', 'canonical_locations_v2.csv', 'unofficial_extra_sources_v1.csv'):
        with (ROOT / filename).open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                if row['effective_source'] not in records:
                    continue
                plugin, kind, fid, field = row['effective_source'], row['record_type'].encode(), int(row['raw_formid'], 16), row['field'].encode()
                occurrence = int(row.get('occurrence') or 0)
                key = (plugin, kind, fid, field, occurrence)
                if key in seen:
                    if filename == 'canonical_locations_v2.csv':
                        continue  # Dedicated patch locations take precedence.
                    raise ValueError(f'Duplicate patch identity {key}')
                seen.add(key)
                record = records[plugin]
                identity = reviewed_identity(record, fid)
                editor = row['editor_id'].encode()
                fields = record[(kind, fid)]
                actual_editor = next((v.rstrip(b'\0') for f,v in fields if f == b'EDID'), b'')
                if editor != actual_editor:
                    raise ValueError(f'Patch metadata editor mismatch {key}')
                old = [v for f,v in fields if f == field][occurrence]
                entry = dict(plugin=plugin, record_type=kind.decode(), formid=f'{fid:08X}',
                    field=field.decode(), occurrence=occurrence, editor_id=editor.decode(),
                    owner=identity[0] if identity else '', base_formid=f'{identity[1]:08X}' if identity else '',
                    policy='patch', reason='patch-owned identity', differs_from_main=False)
                if identity:
                    owner, base_fid = identity
                    all_items = [x for x in table.get((owner, kind, base_fid, field), ())
                                 if x.source == owner and (x.editor_id or b'') == editor]
                    same_occ = [x for x in all_items if x.occurrence == occurrence]
                    exact = [x for x in all_items if normalize_source_text(x.english) == normalize_source_text(row['old_english'])]
                    # A unique English response can move to another occurrence.
                    if exact and len({x.korean for x in exact}) == 1:
                        candidate = exact[-1]
                        policy, reason = 'forward', 'exact English; explicit original occurrence'
                    elif same_occ:
                        candidate = same_occ[-1]
                        policy, reason = ('forward', 'reviewed English spelling/format equivalent') if spelling_equivalent(candidate.english, row['old_english']) else ('patch', 'English content changed; retain patch-specific translation')
                    else:
                        candidate = None
                        policy, reason = 'patch', 'no unambiguous main-game source identity'
                    if candidate is not None:
                        if kind == b'BOOK':
                            bp = book_policies.get((plugin, f'{fid:08X}', field.decode(), occurrence))
                            if bp:
                                policy, reason = bp['policy'], bp['reason']
                        if kind == b'RACE' and field == b'FULL':
                            policy, reason = 'patch', 'voice-folder safety: race name stays English'
                        entry.update(policy=policy, reason=reason,
                            base_occurrence=candidate.occurrence,
                            patch_source_sha256=source_sha(row['old_english']),
                            base_source_sha256=source_sha(candidate.english),
                            differs_from_main=old != candidate.korean,
                            patch_english=row['old_english'], base_english=candidate.english,
                            current_korean=old.rstrip(b'\0').decode('utf-8'),
                            main_korean=candidate.korean[:-1].decode('utf-8'))
                        forwarding.append(entry)
                report.append(entry)
    coverage = Counter()
    uncovered = []
    for plugin, recs in records.items():
        for (kind, fid), fields in recs.items():
            if kind == b'TES4':
                continue
            editor = next((v.rstrip(b'\0') for f,v in fields if f == b'EDID'), b'')
            occurrence_counts = Counter()
            for field, value in fields:
                occ = occurrence_counts[field]
                occurrence_counts[field] += 1
                visible = (field in (b'FULL', b'DESC') or
                    (kind == b'INFO' and field == b'NAM1') or
                    (kind == b'QUST' and field == b'CNAM') or
                    (kind == b'FACT' and field in (b'MNAM', b'FNAM')) or
                    (kind == b'REGN' and field == b'RDMP') or
                    (kind == b'GMST' and field == b'DATA' and editor.startswith(b's')))
                if not visible or not value.endswith(b'\0') or b'\0' in value[:-1]:
                    continue
                if (plugin, kind, fid, field, occ) in seen:
                    coverage['tracked_patch_text'] += 1
                    continue
                identity = reviewed_identity(recs, fid)
                items = ([x for x in table.get((identity[0],kind,identity[1],field), ())
                         if x.source == identity[0] and (x.editor_id or b'') == editor
                         and x.occurrence == occ] if identity else [])
                if items and value == items[-1].korean:
                    coverage['untracked_already_matches_main'] += 1
                elif kind == b'RACE' and field == b'FULL':
                    coverage['voice_safe_race_name'] += 1
                elif items:
                    coverage['untracked_different_from_main'] += 1
                    uncovered.append(dict(plugin=plugin,record_type=kind.decode(),formid=f'{fid:08X}',field=field.decode(),occurrence=occ,editor_id=editor.decode(),current_hex=value.hex(),main_hex=items[-1].korean.hex(),reason='no tracked patch-English provenance; preserve until source known'))
                else:
                    coverage['patch_owned_or_no_main_text'] += 1
    for item in report:
        if not item['differs_from_main']:
            for key in ('patch_english','base_english','current_korean','main_korean'):
                item.pop(key, None)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded_report = (json.dumps({'summary': dict(Counter((x['policy'] + '/' + str(x['differs_from_main'])) for x in report)), 'coverage':dict(coverage), 'untracked_differences':uncovered, 'fields':report}, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    output.write_bytes(gzip.compress(encoded_report, compresslevel=9, mtime=0) if output.suffix == '.gz' else encoded_report)
    names = ['plugin','record_type','formid','field','editor_id','occurrence','owner','base_formid','base_occurrence','patch_source_sha256','base_source_sha256','policy','reason']
    with manifest.open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream, names, extrasaction='ignore', lineterminator='\n')
        writer.writeheader();writer.writerows(forwarding)
    print('Audited', len(report), Counter((x['policy'],x['differs_from_main']) for x in report))
    print('Coverage', coverage)
    print('Changes', Counter(x['record_type'] for x in report if x['policy']=='forward' and x['differs_from_main']))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    audit(args.baseline,args.output,args.manifest)
