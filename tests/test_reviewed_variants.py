import copy
import csv
from pathlib import Path
import unittest
from unofficial_target_variants import apply_variant, load_variants
from unofficial_text_forwarding import load_text_forwarding, main_translations

ROOT=Path(__file__).resolve().parents[1]


class ReviewedVariantsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table=load_text_forwarding(ROOT)
        cls.base=main_translations(ROOT)
        cls.variants=load_variants(ROOT)
        with (ROOT/'unofficial_text_forwarding_v1.csv').open(encoding='utf8',newline='') as f:
            cls.pins={(r['plugin'],r['record_type'].encode(),int(r['formid'],16),r['field'].encode(),
                       r['editor_id'].encode(),int(r['occurrence'])):r for r in csv.DictReader(f)}

    def target(self,plugin,fid,kind=b'INFO',field=b'NAM1',occurrence=0):
        return next(v[3][:-1].decode('utf8') for k,v in self.table.items()
                    if k[:4]==(plugin,kind,fid,field) and k[-1]==occurrence)

    def test_changed_directions_and_training_preserve_patch_meaning(self):
        uop='Unofficial Oblivion Patch.esp'
        direction=self.target(uop,0x35672,occurrence=4)
        self.assertIn('길 북쪽',direction)
        self.assertNotIn('길 남쪽',direction)
        training=self.target(uop,0x47688)
        self.assertIn('경갑 기술',training)
        self.assertNotIn('잠금해제',training)

    def test_typo_only_dialogue_inherits_current_main_not_old_patch(self):
        text=self.target('Unofficial Oblivion Patch.esp',0x1DC28,occurrence=3)
        self.assertIn('도와줄 거지?',text)
        self.assertNotIn('꺼지',text)

    def test_reviewed_books_keep_current_prose_and_patch_corrections(self):
        text=self.target('Unofficial Oblivion Patch.esp',0x22DB4,b'BOOK',b'DESC')
        self.assertIn('시간의 모래시계',text)
        self.assertIn('4) 임페리얼 황궁으로',text)
        self.assertNotIn('Glass of Time',text)
        pelagius=self.target('Unofficial Shivering Isles Patch.esp',0x43F76,b'BOOK',b'DESC')
        self.assertIn('솔리튜드',pelagius)
        self.assertNotIn('센티넬',pelagius)

    def test_patch_recipe_names_follow_current_inventory(self):
        text=self.target('Unofficial Shivering Isles Patch.esp',0x452E9,b'BOOK',b'DESC')
        self.assertIn('레티퍼 오르카 소화 점액',text)
        self.assertIn('물뿌리 꼬투리 속',text)
        self.assertIn('골수 (섐블에서 채취)',text)

    def test_source_and_replacement_drift_are_rejected(self):
        key=next(k for k,v in self.variants.items() if v['mode']=='replace')
        entry=copy.deepcopy(self.variants[key]);row=self.pins[key]
        target=self.base[row['owner'],key[1],int(row['base_formid'],16),key[3]][-1].korean
        wrong=copy.deepcopy(row);wrong['patch_source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'provenance'):
            apply_variant(entry,wrong,target,self.base)
        entry['replacements'][0]['find']='not an existing Korean phrase'
        with self.assertRaisesRegex(ValueError,'replacement changed'):
            apply_variant(entry,row,target,self.base)

    def test_reordered_response_uses_pinned_latest_target(self):
        variants=[v for v in self.variants.values() if v['mode']=='lookup' and v['type']=='INFO']
        self.assertGreaterEqual(len(variants),7)
        for entry in variants:
            self.assertEqual(len(entry['target_source_sha256']),64)
