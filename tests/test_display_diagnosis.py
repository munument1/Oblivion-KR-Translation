import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from build_vanilla_overlay import encode_subrecord
from diagnose_display import diagnose, inspect_plugin, MOJIBAKE


def record(kind,fid,fields):
    body=b''.join(encode_subrecord(k,v) for k,v in fields)
    return struct.pack('<4sIIII',kind,len(body),0,fid,0)+body


class DisplayDiagnosisTests(unittest.TestCase):
    def plugin(self,name,text,own=False):
        header=record(b'TES4',0,[(b'MAST',b'Oblivion.esm\0')]) if name!='Oblivion.esm' else record(b'TES4',0,[])
        fid=0x010229A2 if own else 0x229A2
        return header+record(b'ARMO',fid,[(b'EDID',b'SteelCuirass\0'),(b'FULL',text.encode()+b'\0')])

    def test_exact_gbk_pattern_and_foreign_form_rejection(self):
        self.assertEqual(MOJIBAKE['강철 흉갑'],'臧曥矤 頋夑皯')
        self.assertEqual(MOJIBAKE['작자미상'],'鞛戩瀽氙胳儊')
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'Foreign.esp'
            p.write_bytes(self.plugin(p.name,'강철 흉갑',own=True))
            self.assertEqual(inspect_plugin(p),[])
            p.write_bytes(self.plugin(p.name,MOJIBAKE['강철 흉갑']))
            self.assertEqual(inspect_plugin(p)[0]['mojibake_matches'],['강철 흉갑'])

    def test_only_explicit_active_order_selects_winner_and_files_never_change(self):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/'Data';data.mkdir()
            for name,text in [('Oblivion.esm','강철 흉갑'),('Bad.esp',MOJIBAKE['강철 흉갑'])]:
                (data/name).write_bytes(self.plugin(name,text))
            before={p.name:p.read_bytes() for p in data.iterdir()}
            self.assertIsNone(diagnose(data)['winning_overrides'])
            order=Path(temp)/'active.txt';order.write_text('Oblivion.esm\n*Bad.esp\n')
            self.assertEqual(diagnose(data,order)['winning_overrides'][0]['plugin'],'Bad.esp')
            order.write_text('Oblivion.esm\n')
            self.assertEqual(diagnose(data,order)['winning_overrides'][0]['plugin'],'Oblivion.esm')
            self.assertEqual(before,{p.name:p.read_bytes() for p in data.iterdir()})

    def test_cli_diagnosis_never_runs_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'Oblivion.esm';p.write_bytes(self.plugin(p.name,'강철 흉갑'))
            root=Path(__file__).resolve().parents[1]
            run=subprocess.run([sys.executable,str(root/'install_obcjk.py'),'--diagnose-display','--data-dir',temp],capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads(run.stdout)
            self.assertTrue(report['read_only'])
            self.assertEqual([x.name for x in Path(temp).iterdir()],['Oblivion.esm'])
