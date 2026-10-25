"""Reviewed latest-main derivatives for patch English variants, with fail-closed pins."""
import hashlib
import json


def load_variants(root):
    entries=json.loads((root/'unofficial_reviewed_variants_v2.json').read_text(encoding='utf8'))
    result={}
    for r in entries:
        key=(r['plugin'],r['type'].encode(),int(r['formid'],16),r['field'].encode(),
             r['editor_id'].encode(),int(r['occurrence']))
        if key in result or r['mode'] not in ('main','replace','lookup','literal','ingredient_list','patch'):
            raise ValueError('Duplicate or unknown reviewed variant')
        result[key]=r
    return result


def lookup(table,r,prefix=''):
    owner=r[prefix+'source'];kind=r[prefix+'type'].encode();fid=int(r[prefix+'formid'],16)
    field=r[prefix+'field'].encode();editor=r[prefix+'editor_id'].encode();occ=int(r[prefix+'occurrence'])
    found=[x for x in table.get((owner,kind,fid,field),()) if x.source==owner
           and (x.editor_id or b'')==editor and x.occurrence==occ
           and hashlib.sha256((x.english+'\0').encode('cp1252')).hexdigest()==r[prefix+'source_sha256']]
    if len({x.korean for x in found})!=1:
        raise ValueError('Reviewed target lookup changed or ambiguous')
    return found[-1].korean[:-1].decode('utf8')


def apply_variant(r,row,target,table):
    if (r['patch_source_sha256']!=row['patch_source_sha256']
            or r['base_source_sha256']!=row['base_source_sha256']):
        raise ValueError('Reviewed variant English provenance changed')
    if r['mode']=='patch':
        if row['policy']!='patch':raise ValueError('Reviewed preserve policy changed')
        return None
    text=target[:-1].decode('utf8')
    if r['mode']=='literal':text=r['korean']
    elif r['mode']=='lookup':text=lookup(table,r,'target_')
    elif r['mode']=='ingredient_list':
        if text.count(r['list_start'])!=1:
            raise ValueError('Ingredient list boundary changed')
        text=text[:text.index(r['list_start'])]+''.join(lookup(table,item)+item['suffix']+'<br>\n' for item in r['items'])
    elif r['mode']=='replace':
        if 'move_to_end' in r:
            move=r['move_to_end']
            if text.count(move['start'])!=1 or text.count(move['end'])!=1:
                raise ValueError('Reviewed paragraph boundary changed')
            start=text.index(move['start']);end=text.index(move['end'])
            if end<=start:raise ValueError('Reviewed paragraph order changed')
            paragraph=text[start:end];text=text[:start]+text[end:]+paragraph
        for change in r['replacements']:
            if not change['find'] or change['count']<1 or text.count(change['find'])!=change['count']:
                raise ValueError(f'Reviewed Korean replacement changed: {r["formid"]} {change["find"]}')
            text=text.replace(change['find'],change['replace'])
    if '\0' in text or not text.strip():raise ValueError('Invalid reviewed variant text')
    return text.encode('utf8')+b'\0'
