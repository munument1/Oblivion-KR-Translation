import struct

def commands(data):
    out=[];i=0
    while i<len(data):
        start=i;op,n=struct.unpack_from('<HH',data,i);prefix=b''
        if op==0x1c:
            prefix=data[i:i+4];i+=4;op,n=struct.unpack_from('<HH',data,i)
        assert i+4+n<=len(data),(start,hex(op),n,len(data))
        out.append(dict(offset=start,prefix=prefix,opcode=op,payload=data[i+4:i+4+n],end=i+4+n));i+=4+n
    assert i==len(data)
    return out

def replace_strings(data,mapping):
    old=commands(data);new=[];edits=[];relocations={len(data):None};position=0
    for c in old:
        payload=c['payload'];changed=payload
        # MessageBox, Message and SetName are native commands using UInt16-prefixed literal strings.
        # Only replace literals in commands that actually contain the declared string arguments.
        if c['opcode'] in (0x1000,0x1059):
            spans=[]
            for en,ko in sorted(mapping.items(),key=lambda x:-len(x[0])):
                eb=en.encode('cp1252');kb=ko.encode('utf8')
                needle=struct.pack('<H',len(eb))+eb
                assert len(kb)<=65535
                start=0
                while True:
                    found=payload.find(needle,start)
                    if found<0:break
                    spans.append((found,found+len(needle),struct.pack('<H',len(kb))+kb,en,ko));start=found+len(needle)
            spans.sort();cursor=0;chunks=[];restore=[];new_cursor=0
            for start,end,replacement,en,ko in spans:
                assert start>=cursor,'overlapping literal spans'
                chunks.append(payload[cursor:start]);new_cursor+=start-cursor
                restore.append((new_cursor,new_cursor+len(replacement),payload[start:end]))
                chunks.append(replacement);new_cursor+=len(replacement);cursor=end
                edits.append((c['offset'],en,ko))
            chunks.append(payload[cursor:]);changed=b''.join(chunks)
            restored=[];cursor=0
            for start,end,original in restore:restored.extend((changed[cursor:start],original));cursor=end
            restored.append(changed[cursor:]);assert b''.join(restored)==payload
        relocations[c['offset']]=position
        if c['prefix']:relocations[c['offset']+4]=position+4
        new.append(dict(**c,new_offset=position,new_payload=changed))
        position+=len(c['prefix'])+4+len(changed)
    relocations[len(data)]=position
    for c in new:
        p=bytearray(c['new_payload'])
        if c['opcode'] in (0x176b,0x176d):
            target=struct.unpack_from('<I',c['payload'])[0]
            assert target in relocations,('unmapped loop target',target)
            struct.pack_into('<I',p,0,relocations[target])
        if c['opcode']==0x10:
            length=struct.unpack_from('<I',c['payload'],2)[0]
            target=c['end']+length
            assert target in relocations,('unmapped block end',target)
            new_end=c['new_offset']+len(c['prefix'])+4+len(p)
            struct.pack_into('<I',p,2,relocations[target]-new_end)
        c['new_payload']=bytes(p)
    result=b''.join(c['prefix']+struct.pack('<HH',c['opcode'],len(c['new_payload']))+c['new_payload'] for c in new)
    assert len(result)==position
    parsed=commands(result);assert len(parsed)==len(old)
    for a,b in zip(old,parsed):
        assert a['opcode']==b['opcode'] and a['prefix']==b['prefix']
        if a['opcode'] in (0x176b,0x176d):assert struct.unpack_from('<I',b['payload'])[0]==relocations[struct.unpack_from('<I',a['payload'])[0]]
    return result,edits
