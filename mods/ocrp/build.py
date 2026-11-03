"""Rebuild OCRP Korean UTF-8 ESPs from the exact unmodified source files.

Usage:
    python mods/ocrp/build.py ORIGINALS_DIRECTORY NEW_OUTPUT_DIRECTORY

Requires Python 3.10+. Reads each original ESP recursively by file name and
SHA-256, and writes separate replacements. Never overwrites existing output.
Only approved visible text and verified compiled Message/MessageBox literals change; all other binary fields are preserved.
"""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import re
import struct
import sys
import zlib
from bytecode import commands, replace_strings

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "sources_ocrp_1.3.json"
TABLE = HERE / "translations_ocrp_1.3.csv"
SCRIPT_TABLE = HERE / "scripts_ocrp_1.3.csv"
FMT = re.compile(r"%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z](?![a-zA-Z])|%)")
TAGS = re.compile(r"<[^>]*>")

def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def fields(body):
    i = 0
    while i < len(body):
        start = i
        if i + 6 > len(body):
            raise ValueError("Truncated TES4 subrecord header")
        tag, size = struct.unpack_from("<4sH", body, i)
        i += 6
        if tag == b"XXXX":
            if size != 4 or i + 10 > len(body):
                raise ValueError("Invalid XXXX extended subrecord")
            size = struct.unpack_from("<I", body, i)[0]
            i += 4
            tag = body[i:i+4]
            i += 6
        if i + size > len(body):
            raise ValueError("Truncated TES4 subrecord payload")
        yield tag, body[i:i+size], body[start:i+size]
        i += size

def pack_field(tag, content):
    if len(content) > 65535:
        return b"XXXX\x04\x00" + struct.pack("<I", len(content)) + tag + b"\0\0" + content
    return tag + struct.pack("<H", len(content)) + content

def records(data):
    def walk(pos, end):
        while pos < end:
            if pos + 20 > end:
                raise ValueError("Truncated TES4 record header")
            kind, size, flags, fid, stamp = struct.unpack_from("<4sIIII", data, pos)
            stop = pos + size if kind == b"GRUP" else pos + 20 + size
            if not pos + 20 <= stop <= end:
                raise ValueError("Invalid TES4 record boundary")
            if kind == b"GRUP":
                yield from walk(pos+20, stop)
            else:
                raw = data[pos+20:stop]
                if flags & 0x40000:
                    expected = struct.unpack_from("<I", raw, 0)[0]
                    body = zlib.decompress(raw[4:])
                    if len(body) != expected:
                        raise ValueError("Compressed record size mismatch")
                else:
                    body = raw
                yield kind, fid, flags, stamp, list(fields(body))
            pos = stop
        if pos != end:
            raise ValueError("Invalid trailing data")
    return list(walk(0, len(data)))

def verify_script(old, new, mapping):
    a, b = commands(old), commands(new)
    if len(a) != len(b):
        raise ValueError("Compiled script command count changed")
    relocated = {len(old):len(new)}
    for ac, bc in zip(a,b,strict=True):
        if (ac["opcode"],ac["prefix"]) != (bc["opcode"],bc["prefix"]):
            raise ValueError("Compiled script opcode changed")
        relocated[ac["offset"]] = bc["offset"]
        if ac["prefix"]:
            relocated[ac["offset"]+4] = bc["offset"]+4
    for ac,bc in zip(a,b,strict=True):
        op=ac["opcode"]
        before, after = ac["payload"],bc["payload"]
        if op == 0x10:
            assert before[:2]==after[:2] and before[6:]==after[6:]
            assert relocated[ac["end"]+struct.unpack_from("<I",before,2)[0]] == bc["end"]+struct.unpack_from("<I",after,2)[0]
        elif op in (0x176b,0x176d):
            assert relocated[struct.unpack_from("<I",before)[0]]==struct.unpack_from("<I",after)[0]
            assert before[4:]==after[4:]
        elif op in (0x1000,0x1059):
            for en,ko in sorted(mapping.items(),key=lambda pair:-len(pair[1])):
                eb,kb=en.encode("cp1252"),ko.encode("utf-8")
                after=after.replace(struct.pack("<H",len(kb))+kb,struct.pack("<H",len(eb))+eb)
            assert before==after,"Nontext Message/MessageBox operands changed"
        else:
            assert before==after,"Non-message bytecode payload changed"

def rebuild(source: bytes, by_record, script_records):
    changed=set()
    script_changed=set()
    script_seen=set()
    script_edits=0
    def walk(pos, end):
        nonlocal script_edits
        chunks = []
        while pos < end:
            kind, size, flags, fid, stamp = struct.unpack_from("<4sIIII", source, pos)
            header = bytearray(source[pos:pos+20])
            stop = pos + size if kind == b"GRUP" else pos + 20 + size
            if not pos + 20 <= stop <= end:
                raise ValueError("Corrupt record boundary")
            if kind == b"GRUP":
                contents = walk(pos+20, stop)
                struct.pack_into("<I", header, 4, len(contents)+20)
                chunks.extend((header, contents))
                pos = stop
                continue
            raw = source[pos+20:stop]
            if (kind, fid) in by_record or (kind, fid) in script_records:
                if flags & 0x40000:
                    expected = struct.unpack_from("<I", raw)[0]
                    body = zlib.decompress(raw[4:])
                    if len(body) != expected:
                        raise ValueError("Compressed source size mismatch")
                else:
                    body = raw
                sub = list(fields(body))
                changes = {}
                for index, row in by_record.get((kind, fid),{}).items():
                    if index >= len(sub):
                        raise ValueError(f"Missing subrecord index: {kind!r} {fid:08X} {index}")
                    tag, value, original_field = sub[index]
                    if tag.decode("ascii") != row["tag"]:
                        raise ValueError(f"Unexpected tag: {kind!r} {fid:08X} {index}")
                    nul_suffix = len(value) - len(value.rstrip(b"\0"))
                    old = value[:len(value)-nul_suffix] if nul_suffix else value
                    if old.decode("cp1252") != row["english"]:
                        raise ValueError(f"Source differs from translation table: {kind!r} {fid:08X} {index}")
                    new = row["korean"].encode("utf-8") + b"\0" * nul_suffix
                    if new != value:
                        changes[index] = new
                        changed.add((kind, fid, index))
                if (kind, fid) in script_records:
                    if kind != b"SCPT":
                        raise ValueError("Unexpected script record type")
                    mapping=script_records[(kind,fid)]
                    indices={t:i for i,(t,v,rawsub) in enumerate(sub) if t in (b"SCHR",b"SCDA",b"SCTX")}
                    if set(indices)!={b"SCHR",b"SCDA",b"SCTX"}:
                        raise ValueError(f"Missing compiled script subrecords: {fid:08X}")
                    sci,txi,hei=indices[b"SCDA"],indices[b"SCTX"],indices[b"SCHR"]
                    sctext=sub[txi][1].rstrip(b"\0").decode("cp1252")
                    for en in mapping:
                        if '"' + en + '"' not in sctext:
                            raise ValueError(f"Literal absent from SCTX: {fid:08X} {en}")
                    original_code=sub[sci][1]
                    new_code, edits = replace_strings(original_code, mapping)
                    actual={en:ko for offset,en,ko in edits}
                    if actual != mapping:
                        raise ValueError(f"Message literal not matched in bytecode: {fid:08X}: {set(mapping)-set(actual)}")
                    verify_script(original_code,new_code,actual)
                    schr=bytearray(sub[hei][1])
                    if len(schr)<12 or struct.unpack_from("<I",schr,8)[0]!=len(original_code):
                        raise ValueError("SCHR compiled code size mismatch")
                    struct.pack_into("<I",schr,8,len(new_code))
                    nul_suffix=len(sub[txi][1])-len(sub[txi][1].rstrip(b"\0"))
                    newtext=re.sub(r'"([^"\r\n]*)"',lambda m:'"'+mapping.get(m[1],m[1])+'"',sctext)
                    changes.update({sci:new_code,hei:bytes(schr),txi:newtext.encode("utf-8")+b"\0"*nul_suffix})
                    script_changed.update({(kind,fid,sci),(kind,fid,hei),(kind,fid,txi)})
                    script_seen.add((kind,fid))
                    script_edits+=len(edits)
                    changed.update({(kind,fid,sci),(kind,fid,hei),(kind,fid,txi)})
                if changes:
                    body = b"".join(
                        pack_field(t, changes[i]) if i in changes else subfield
                        for i, (t, v, subfield) in enumerate(sub)
                    )
                    raw = struct.pack("<I", len(body)) + zlib.compress(body, 9) if flags & 0x40000 else body
                    struct.pack_into("<I", header, 4, len(raw))
            chunks.extend((header, raw))
            pos = stop
        if pos != end:
            raise ValueError("Invalid group tail")
        return b"".join(chunks)
    result = walk(0, len(source))
    if set(script_records)!=script_seen:
        raise ValueError(f"Unprocessed script records: {set(script_records)-script_seen}")
    return result, changed, script_changed, script_edits

def build(original_dir: Path, output_dir: Path):
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output_dir}")
    meta = json.loads(MANIFEST.read_text("utf-8"))
    if sha(TABLE.read_bytes()) != meta["translation_sha256"]:
        raise ValueError("Translation CSV checksum mismatch")
    if sha(SCRIPT_TABLE.read_bytes()) != meta["script_translation_sha256"]:
        raise ValueError("Script translation CSV checksum mismatch")
    with SCRIPT_TABLE.open(encoding="utf-8-sig",newline="") as fh:
        script_rows=list(csv.DictReader(fh))
    if len(script_rows)!=meta["script_entries"]:
        raise ValueError("Script table line count differs from manifest")
    scripts=defaultdict(lambda:defaultdict(dict))
    for row in script_rows:
        key=(b"SCPT",int(row["fid"],16))
        name=row["file"]
        en,ko=row["english"],row["korean"]
        if en in scripts[name][key] or not ko or "\ufffd" in ko or "\0" in ko or "\n" in ko or "\r" in ko:
            raise ValueError(f"Invalid duplicate or malformed script translation: {key} {en}")
        if FMT.findall(en)!=FMT.findall(ko):
            raise ValueError("Script placeholder mismatch")
        scripts[name][key][en]=ko
    with TABLE.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    translations = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        name, kind, fid, index = row["file"], row["kind"].encode("ascii"), int(row["fid"], 16), int(row["index"])
        key = kind, fid
        if index in translations[name][key]:
            raise ValueError(f"Duplicate translation field: {name} {key} {index}")
        if row["korean"].strip() == "" or "\ufffd" in row["korean"] or "\0" in row["korean"]:
            raise ValueError("Invalid Korean text")
        if FMT.findall(row["english"]) != FMT.findall(row["korean"]):
            raise ValueError("Changed format specifiers")
        if TAGS.findall(row["english"]) != TAGS.findall(row["korean"]):
            raise ValueError("Changed markup")
        if re.search(r"[A-Za-z]", TAGS.sub("",row["korean"])):
            raise ValueError("Unreviewed Latin text in Korean translation (possibly old bilingual memory)")
        if row["english"].count("\r\n") != row["korean"].count("\r\n"):
            raise ValueError("Changed CRLF structure")
        translations[name][key][index] = row
    prepared = {}
    for name, spec in meta["plugins"].items():
        matches = [p for p in original_dir.rglob(name) if p.is_file() and sha(p.read_bytes()) == spec["sha256"]]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one matching SHA-256 source for {name}, got {len(matches)}")
        original = matches[0].read_bytes()
        if len(original) != spec["size"]:
            raise ValueError("Source size mismatch")
        replacement, changed, script_changed, script_edits = rebuild(original, translations[name], scripts[name])
        expected_keys = {
            (kind, fid, index)
            for (kind, fid), indices in translations[name].items()
            for index in indices
        }
        visible_translation_count=len(expected_keys)
        expected_keys |= script_changed
        a, b = records(original), records(replacement)
        if len(a) != spec["records"] or len(a) != len(b):
            raise ValueError(f"Record count changed for {name}")
        for (ak, af, afl, ast, fs1), (bk, bf, bfl, bst, fs2) in zip(a, b, strict=True):
            if (ak, af, afl, ast) != (bk, bf, bfl, bst) or len(fs1) != len(fs2):
                raise ValueError("Record metadata changed")
            for idx, ((at, av, _), (bt, bv, _)) in enumerate(zip(fs1, fs2, strict=True)):
                if at != bt:
                    raise ValueError("Subrecord tags changed")
                if (ak, af, idx) not in expected_keys and av != bv:
                    raise ValueError(f"Untranslated binary field changed: {name} {ak!r} {af:08X} {idx}")
                if at in (b"SCDA",b"SCTX",b"SCHR") and av != bv and (ak,af,idx) not in script_changed:
                    raise ValueError("Unauthorized script source, size or bytecode change")
                if at==b"SCDA" and (ak,af,idx) in script_changed:
                    verify_script(av,bv,scripts[name][(ak,af)])
        if not changed.issubset(expected_keys):
            raise ValueError("Unexpected changed fields")
        prepared[name] = (replacement, {"source_sha256":sha(original),"output_sha256":sha(replacement),
            "records":len(a),"translation_rows":visible_translation_count,"fields_modified":len(changed),
            "script_literal_edits":script_edits,"script_modified_subrecords":len(script_changed),
            "script_nontext_operands_preserved":True,"source_path":str(matches[0])})
    output_dir.mkdir(parents=True)
    for name, (payload, details) in prepared.items():
        (output_dir/name).write_bytes(payload)
        print(f"{name}: {details['fields_modified']} translated fields, {details['records']} records", flush=True)
    report = {"version":meta["version"],"in_game_tested":False,"plugins":{n:v[1] for n,v in prepared.items()},
              "excluded_internal":meta["excluded_internal"],"script_messages_translated":True,
              "script_translation_rows":len(script_rows),"script_translation_sha256":meta["script_translation_sha256"]}
    (output_dir/"OCRP_KR_STATIC_VALIDATION.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2]))
