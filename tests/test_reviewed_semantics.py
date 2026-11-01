import unittest
from pathlib import Path
from build_vanilla_overlay import load_translations
from reviewed_semantics import correct_reviewed_semantics, RULES, correct_forwarding
from unofficial_text_forwarding import load_text_forwarding
ROOT=Path(__file__).resolve().parents[1]
class ReviewedSemanticsTests(unittest.TestCase):
 def test_real_corpus_and_fail_closed(self):
  t=load_translations(ROOT/'canonical_translation_v2.csv',(),encoded_column='obcjk_utf8_hex')
  before={(k,i):a for k,v in t.items() for i,a in enumerate(v)}
  self.assertEqual(correct_reviewed_semantics(t),7)
  changed=[(k,i) for k,v in t.items() for i,a in enumerate(v) if a!=before[k,i]]
  self.assertEqual(len(changed),7)
  for k,i in changed:
   self.assertEqual(t[k][i].english,before[k,i].english)
   self.assertEqual(t[k][i].editor_id,before[k,i].editor_id)
  with self.assertRaises(ValueError): correct_reviewed_semantics(t)
 def test_uop_forwarding(self):
  old=load_text_forwarding(ROOT);new=correct_forwarding(dict(old))
  changed=[k for k in old if old[k]!=new[k]]
  self.assertEqual(len(changed),1)
  self.assertEqual(new[changed[0]][3],'침묵'.encode()+b'\0')
