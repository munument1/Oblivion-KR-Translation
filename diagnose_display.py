"""Read-only diagnosis of the three display targets in Nexus comment 178027815."""
from __future__ import annotations
import configparser
import hashlib
from pathlib import Path
import struct

from build_obcjk_overlay import records

TARGETS = {(b'ARMO', 0x229A2): b'FULL', (b'BOOK', 0x24564): b'DESC',
           (b'ACTI', 0x1E7A5): b'SCRI', (b'SCPT', 0x4CAEE): b'SCDA'}
MOJIBAKE = {text: text.encode('utf-8').decode('gbk')
            for text in ('강철 흉갑', '작자미상')}


def inspect_plugin(path):
    """Return only exact Oblivion-owned targets, never same-number foreign forms."""
    path = Path(path)
    masters = []
    found = []
    for (kind, fid), header, parts, groups in records(path):
        if kind == b'TES4':
            masters = [v.rstrip(b'\0').decode('cp1252') for f, v, _ in parts if f == b'MAST']
            continue
        field = TARGETS.get((kind, fid & 0xFFFFFF))
        if field is None:
            continue
        index = fid >> 24
        owner = masters[index] if index < len(masters) else path.name if index == len(masters) else None
        if not owner or owner.casefold() != 'oblivion.esm':
            continue
        values = [v for f, v, _ in parts if f == field]
        if len(values) != 1:
            raise ValueError('Display target has missing/duplicate field')
        raw = values[0]
        row = {'plugin': path.name, 'record_type': kind.decode(),
               'formid': f'{fid & 0xFFFFFF:08X}', 'field': field.decode(),
               'editor_id': next((v.rstrip(b'\0').decode('cp1252') for f,v,_ in parts if f==b'EDID'), ''),
               'field_sha256': hashlib.sha256(raw).hexdigest()}
        if field == b'SCRI':
            if len(raw)!=4:
                raise ValueError('Invalid script reference')
            row['linked_script_raw_formid']=f'{struct.unpack("<I",raw)[0]:08X}'
        elif field == b'SCDA':
            row['english_gate_message_present']=b'This gate is opened remotely.' in raw
            row['korean_gate_message_present']='장치로 여는 문입니다.'.encode() in raw
        else:
            try:
                text=raw.rstrip(b'\0').decode('utf-8', errors='strict')
                row['valid_utf8']=True
                row['text_prefix']=text[:180]
                row['mojibake_matches']=[original for original,bad in MOJIBAKE.items() if bad in text]
                row['expected_text_present']=[t for t in ('강철 흉갑','작자미상','작가 미상') if t in text]
            except UnicodeDecodeError:
                row['valid_utf8']=False
                row['raw_prefix_hex']=raw[:100].hex()
        found.append(row)
    return found


def diagnose(data_dir, load_order=None):
    data=Path(data_dir).resolve()
    if not data.is_dir():
        raise ValueError('Data folder does not exist')
    available={p.name.casefold():p for p in data.iterdir() if p.suffix.lower() in ('.esm','.esp') and p.is_file()}
    if load_order:
        names=[]
        for line in Path(load_order).read_text(encoding='utf-8-sig').splitlines():
            name=line.strip()
            if not name or name.startswith('#'):
                continue
            name=name.removeprefix('*')
            if '/' in name or '\\' in name or Path(name).suffix.lower() not in ('.esm','.esp'):
                raise ValueError('Load order must contain only active plugin basenames')
            if name.casefold() in [n.casefold() for n in names]:
                raise ValueError('Duplicate plugin in load order')
            names.append(name)
        missing=[n for n in names if n.casefold() not in available]
        if missing:
            raise ValueError(f'Active plugins not visible in Data: {missing}')
        paths=[available[n.casefold()] for n in names]
    else:
        paths=sorted(available.values(),key=lambda p:p.name.casefold())
    matches=[r for p in paths for r in inspect_plugin(p)]
    winner={}
    if load_order:
        for row in matches:
            winner[(row['record_type'],row['formid'])]=row
    ini=data/'OBSE/plugins/obCJK/obCJK.ini'
    runtime=data/'OBSE/plugins/obCJK.dll'
    config=configparser.ConfigParser(interpolation=None)
    if ini.is_file():
        config.read_string(ini.read_text(encoding='utf-8-sig'))
    from obcjk_runtime import VERIFIED_SHA256
    digest=hashlib.sha256(runtime.read_bytes()).hexdigest() if runtime.is_file() else None
    return {'read_only':True, 'inspected_plugins':len(paths),
            'active_load_order_supplied':bool(load_order),
            'winning_overrides':list(winner.values()) if load_order else None,
            'all_matching_records':matches,
            'effective_ini_present':ini.is_file(),
            'active_code_page':config.get('obCJK','ActiveCodePage',fallback=None),
            'xobse_utf8_enabled':config.get('obCJK','XOBSEStringUtf8Enable',fallback=None),
            'obcjk_dll_sha256':digest,'matches_bundled_runtime':digest==VERIFIED_SHA256,
            'limitations':['Run through MO2 to inspect its virtual Data, including loose-file overrides.',
                          'Without an active load order, no winning plugin is inferred.',
                          'Runtime string mutations and in-memory hook conflicts are not observable here.']}
