"""Reproducible OCRP translation build and integrity checks.

Usage: python mods/ocrp/test_build.py ORIGINALS_DIRECTORY
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import csv
import re

import build

def sha(data):
    return hashlib.sha256(data).hexdigest()

def test(source_dir):
    meta=json.loads(build.MANIFEST.read_text("utf8"))
    with build.TABLE.open(encoding="utf-8-sig",newline="") as f:
        text_rows=list(csv.DictReader(f))
    with build.SCRIPT_TABLE.open(encoding="utf-8-sig",newline="") as f:
        script_rows=list(csv.DictReader(f))
    assert len(text_rows)==1388
    assert len(script_rows)==59
    for row in text_rows:
        assert not re.search(r"[A-Za-z]", re.sub(r"<[^>]+>","",row["korean"])), (row["fid"],row["korean"])
    assert sum(row["method"]=="manual_legacy_review" for row in text_rows)==47
    assert sum(row["method"]=="manual_source_review" for row in text_rows)==8
    syl=next(r for r in text_rows if r["fid"]=="0001351B" and r["english"].startswith("Kithlan has told"))
    assert "낮에" in syl["korean"] and "한밤중" not in syl["korean"]
    boots=next(r for r in text_rows if r["english"]=="The Gray Fox thanked me for getting him the boots.")
    assert "500" not in boots["korean"]
    assert len(meta["excluded_internal"])==8
    assert sha(build.TABLE.read_bytes())==meta["translation_sha256"]
    assert sha(build.SCRIPT_TABLE.read_bytes())==meta["script_translation_sha256"]
    with tempfile.TemporaryDirectory(prefix="ocrp_kr_test_") as dir_name:
        root=Path(dir_name)
        out1=root/"build_1"
        out2=root/"build_2"
        first=build.build(source_dir,out1)
        second=build.build(source_dir,out2)
        assert first["script_messages_translated"] and second["script_messages_translated"]
        assert first["script_translation_rows"]==59
        assert sum(x["script_literal_edits"] for x in first["plugins"].values())==59
        assert sum(x["translation_rows"] for x in first["plugins"].values())==1388
        for name, spec in meta["plugins"].items():
            binary1=(out1/name).read_bytes()
            binary2=(out2/name).read_bytes()
            assert binary1 == binary2, f"Nondeterministic build: {name}"
            assert sha(binary1)==first["plugins"][name]["output_sha256"]
            assert len(build.records(binary1))==spec["records"]
        try:
            build.build(source_dir,out1)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing output directory overwritten")
    print(json.dumps({"result":"PASS","files":len(meta["plugins"]),"translated_text_fields":len(text_rows),
         "script_message_literals":len(script_rows),"unmodified_internal_identifiers":8,
         "deterministic_binary_rebuild":True,"source_hash_verified":True,
         "gameplay_tested":False},ensure_ascii=False,indent=2))

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit(__doc__)
    test(Path(sys.argv[1]))
