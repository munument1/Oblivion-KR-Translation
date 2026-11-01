"""Source-anchored FULL labels reviewed on 2026-11-02; canonical input stays immutable."""
from dataclasses import replace
RULES = (('DLCBattlehornCastle.esp', 'CONT', '0100776A', 'Drawers', '선반', '서랍'), ('DLCBattlehornCastle.esp', 'CONT', '0100776C', 'Drawers', '선반', '서랍'), ('Oblivion.esm', 'BOOK', '00015AD3', 'Summon Lich', '달인소환 - 시체', '달인소환 - 리치'), ('Oblivion.esm', 'SPEL', '00084B17', 'Silence', '은밀', '침묵'), ('Oblivion.esm', 'SPEL', '000AA04D', 'Silence', '은밀', '침묵'), ('DLCSpellTomes.esp', 'BOOK', '01002338', 'Silence Tome', '주문서: 은밀', '주문서: 침묵'), ('Oblivion.esm', 'MGEF', '00001881', 'Invisibility', '은신', '투명화'))

def correct_reviewed_semantics(table):
    planned=[]
    for source,kind,fid,english,before,after in RULES:
        key=(source,kind.encode(),int(fid,16),b'FULL')
        matches=[(i,a) for i,a in enumerate(table.get(key,[])) if a.source==source and a.english==english]
        if len(matches)!=1 or matches[0][1].korean != before.encode()+b'\0':
            raise ValueError(f'Reviewed semantic source drift: {key}')
        i,a=matches[0];planned.append((key,i,replace(a,korean=after.encode()+b'\0')))
    for key,i,a in planned: table[key][i]=a
    return len(planned)

def correct_forwarding(table):
    for key,(owner,fid,sha,target,policy) in list(table.items()):
        for source,kind,raw,en,before,after in RULES:
            if owner==source and fid==int(raw,16) and key[1]==kind.encode() and key[3]==b'FULL':
                if target != before.encode()+b'\0':
                    raise ValueError('Reviewed forwarding source changed')
                table[key]=(owner,fid,sha,after.encode()+b'\0',policy)
    return table
