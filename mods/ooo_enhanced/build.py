"""Rebuild the UTF-8 Korean overlay from exact OOO Enhanced sources.

Usage: python mods/ooo_enhanced/build.py ORIGINAL_DIRECTORY NEW_OUTPUT_DIRECTORY [--version 6.9|6.9a]
"""
from pathlib import Path
import csv, hashlib, json, re, struct, sys, zlib
from collections import defaultdict
from bytecode import commands, replace_strings

HERE = Path(__file__).resolve().parent
FORMAT = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z](?![a-zA-Z])|%)')

def sha(data): return hashlib.sha256(data).hexdigest()

def fields(body):
    i=0
    while i<len(body):
        start=i
        if i+6>len(body): raise ValueError('Truncated subrecord')
        tag,n=struct.unpack_from('<4sH',body,i); i+=6
        if tag==b'XXXX':
            if n!=4 or i+10>len(body): raise ValueError('Invalid XXXX')
            n=struct.unpack_from('<I',body,i)[0];i+=4
            tag=body[i:i+4];i+=6
        if i+n>len(body):raise ValueError('Subrecord exceeds record')
        yield tag,body[i:i+n],body[start:i+n]
        i+=n

def pack(tag,value):
    if len(value)>65535:return b'XXXX\x04\x00'+struct.pack('<I',len(value))+tag+b'\0\0'+value
    return tag+struct.pack('<H',len(value))+value

def records(data):
    def walk(i,end):
        while i<end:
            if i+20>end:raise ValueError('Truncated record')
            kind,size,flags,fid,stamp=struct.unpack_from('<4sIIII',data,i)
            stop=i+size if kind==b'GRUP' else i+20+size
            if not i+20<=stop<=end:raise ValueError('Invalid record boundary')
            if kind==b'GRUP':yield from walk(i+20,stop)
            else:
                raw=data[i+20:stop]
                if flags&0x40000:
                    body=zlib.decompress(raw[4:]);assert len(body)==struct.unpack_from('<I',raw)[0]
                else:body=raw
                yield kind,fid,list(fields(body))
            i=stop
        assert i==end
    return list(walk(0,len(data)))

def verify_script(old,new,mapping):
    a,b=commands(old),commands(new);assert len(a)==len(b)
    reloc={len(old):len(new)}
    for ac,bc in zip(a,b,strict=True):
        assert (ac['opcode'],ac['prefix'])==(bc['opcode'],bc['prefix'])
        reloc[ac['offset']]=bc['offset']
        if ac['prefix']:reloc[ac['offset']+4]=bc['offset']+4
    for ac,bc in zip(a,b,strict=True):
        ap,bp=ac['payload'],bc['payload'];op=ac['opcode']
        if op==0x10:
            assert ap[:2]==bp[:2] and ap[6:]==bp[6:]
            assert reloc[ac['end']+struct.unpack_from('<I',ap,2)[0]]==bc['end']+struct.unpack_from('<I',bp,2)[0]
        elif op in (0x176b,0x176d):
            assert reloc[struct.unpack_from('<I',ap)[0]]==struct.unpack_from('<I',bp)[0] and ap[4:]==bp[4:]
        elif op in (0x1000,0x1059):
            for en,ko in sorted(mapping.items(),key=lambda x:-len(x[1])):
                eb,kb=en.encode('cp1252'),ko.encode('utf8')
                bp=bp.replace(struct.pack('<H',len(kb))+kb,struct.pack('<H',len(eb))+eb)
            assert ap==bp,'Changed nontext command arguments'
        else:assert ap==bp,'Changed nontext command payload'

def build(source,output,version='6.9a'):
    if version not in ('6.9','6.9a'):raise ValueError('Unsupported source version')
    if output.exists():raise FileExistsError(output)
    manifest=json.loads((HERE/f'sources_{version}.json').read_text(encoding='utf8'))
    table=HERE/f'translations_{version}.csv'
    assert sha(table.read_bytes())==manifest['translation_sha256']
    with table.open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    by_file=defaultdict(list)
    for r in rows:
        assert r['korean'] and '\ufffd' not in r['korean'] and '\0' not in r['korean']
        by_file[r['file']].append(r)
    # Validate every input before creating the output directory.
    for rel,info in manifest['plugins'].items():
        assert sha((source/rel).read_bytes())==info['sha256'],f'Wrong source version: {rel}'
    output.mkdir(parents=True)
    report={'version':f'{version}-KR1.0','plugins':{},'in_game_tested':False}
    for rel,info in manifest['plugins'].items():
        original=(source/rel).read_bytes();lookup=defaultdict(list)
        for r in by_file[rel]:lookup[(r['kind'].encode(),int(r['fid'],16))].append(r)
        allowed=set();script_maps={};used=set();script_edits=0;source_only=[]
        def rewrite(i,end):
            nonlocal script_edits
            chunks=[]
            while i<end:
                kind,size,flags,fid,stamp=struct.unpack_from('<4sIIII',original,i)
                header=bytearray(original[i:i+20]);stop=i+size if kind==b'GRUP' else i+20+size
                assert i+20<=stop<=end
                if kind==b'GRUP':
                    body=rewrite(i+20,stop);struct.pack_into('<I',header,4,len(body)+20)
                    chunks.extend((header,body));i=stop;continue
                raw=original[i+20:stop]
                body=zlib.decompress(raw[4:]) if flags&0x40000 else raw
                fs=list(fields(body));updates={};scripts=defaultdict(dict)
                for r in lookup[(kind,fid)]:
                    index=int(r['index']);tag,value,_=fs[index]
                    if r['tag']=='SCRIPT':scripts[index][r['english']]=r['korean'];continue
                    assert tag.decode()==r['tag']
                    assert value.rstrip(b'\0').decode('cp1252')==r['english']
                    assert FORMAT.findall(r['english'])==FORMAT.findall(r['korean']),(r['english'],r['korean'])
                    new=r['korean'].encode('utf8')+(b'\0' if value.endswith(b'\0') else b'')
                    if new!=value:updates[index]=new
                    used.add((kind,fid,index,r['english']))
                for sctx,mapping in scripts.items():
                    assert fs[sctx][0]==b'SCTX'
                    text=fs[sctx][1].rstrip(b'\0').decode('cp1252')
                    for en,ko in mapping.items():
                        assert '"'+en+'"' in text
                        assert FORMAT.findall(en)==FORMAT.findall(ko)
                        used.add((kind,fid,sctx,en))
                    mapping={en:ko.replace('"',"'") for en,ko in mapping.items() if en!=ko}
                    scda=next(j for j in range(sctx-1,-1,-1) if fs[j][0]==b'SCDA')
                    schr=next(j for j in range(scda-1,-1,-1) if fs[j][0]==b'SCHR')
                    patched,edits=replace_strings(fs[scda][1],mapping)
                    actual={en:ko for _,en,ko in edits}
                    source_only.extend(dict(fid=f'{fid:08X}',english=en) for en in mapping if en not in actual)
                    if patched==fs[scda][1]:continue
                    verify_script(fs[scda][1],patched,actual)
                    script_maps[(kind,fid,scda)]=actual;script_edits+=len(edits)
                    updates[scda]=patched
                    header_script=bytearray(fs[schr][1]);assert struct.unpack_from('<I',header_script,8)[0]==len(fs[scda][1])
                    struct.pack_into('<I',header_script,8,len(patched));updates[schr]=bytes(header_script)
                    # Replace source literals simultaneously, avoiding substring collisions.
                    newtext=re.sub(r'"([^"\r\n]*)"',lambda m:'"'+actual.get(m[1],m[1])+'"',text)
                    updates[sctx]=newtext.encode('utf8')+(b'\0' if fs[sctx][1].endswith(b'\0') else b'')
                if updates:
                    allowed.update((kind,fid,j) for j in updates)
                    body=b''.join(pack(t,updates[j]) if j in updates else rawfield for j,(t,v,rawfield) in enumerate(fs))
                    raw=struct.pack('<I',len(body))+zlib.compress(body,9) if flags&0x40000 else body
                    struct.pack_into('<I',header,4,len(raw))
                chunks.extend((header,raw));i=stop
            assert i==end
            return b''.join(chunks)
        result=rewrite(0,len(original))
        assert len(used)==len({(r['kind'],r['fid'],r['index'],r['english']) for r in by_file[rel]})
        old,new=records(original),records(result);assert len(old)==len(new)
        scripts_checked=0
        for (kind,fid,fs),(nk,nf,nfs) in zip(old,new,strict=True):
            assert (kind,fid)==(nk,nf) and len(fs)==len(nfs)
            for j,((tag,value,_),(nt,nv,_)) in enumerate(zip(fs,nfs,strict=True)):
                assert tag==nt
                if (kind,fid,j) not in allowed:assert value==nv,'Changed nontranslation data'
                if tag==b'SCDA':verify_script(value,nv,script_maps.get((kind,fid,j),{}));scripts_checked+=1
        destination=output/rel;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(result)
        report['plugins'][rel]=dict(source_sha256=sha(original),output_sha256=sha(result),records=len(old),translated_fields=len(allowed),script_literal_edits=script_edits,scripts_checked=scripts_checked,source_only_literals=source_only)
        print(Path(rel).name,len(allowed),'fields validated',flush=True)
    (output/'STATIC_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--version',choices=('6.9','6.9a'),default='6.9a')
    args=parser.parse_args()
    build(args.source,args.output,args.version)
