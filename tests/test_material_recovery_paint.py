import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from material_recovery_paint import pack_paint_word,remap_word,masked_word,rgb5a3_cpu_word,cpu_word_rgb5a3


class PaintRecoveryTests(unittest.TestCase):
    def test_original_native_palette_expansion_and_packback(self):
        self.assertEqual(rgb5a3_cpu_word(0x3136),0x60603010)
        self.assertEqual(cpu_word_rgb5a3(0x60603010),0x3136)
        self.assertEqual(rgb5a3_cpu_word(0xffff),0xfff8f8f8)
        self.assertEqual(cpu_word_rgb5a3(0xefffffff),0x7fff)
        self.assertEqual(cpu_word_rgb5a3(0xf0ffffff),0xffff)
        with self.assertRaises(ValueError):rgb5a3_cpu_word(65536)

    def test_original_attribute_word_order(self):
        self.assertEqual(pack_paint_word(0x12,0x34,0x56,0x78),0x78563412)
        with self.assertRaises(ValueError):pack_paint_word(256,0,0,0)

    def test_primary_mask_selects_original_palette_word(self):
        p=[0x12345678,0x90abcdef,0xfedcba98]
        for i in range(3):self.assertEqual(remap_word(255<<(8*i),p),p[i])
        self.assertEqual(remap_word(0,p),0)

    def test_separate_mask_uses128_scale_and_retains_fourth_byte(self):
        self.assertEqual(masked_word(0,0xffffffff,0),0)
        self.assertEqual(masked_word(0,0xffffffff,64),0x7f7f7f7f)
        self.assertEqual(masked_word(0,0xffffffff,127),0xfdfdfdfd)
        self.assertEqual(masked_word(0,0xffffffff,128),0xffffffff)
        self.assertEqual(masked_word(0x80b7b7b7,0x00663311,255),0x00663311)
        with self.assertRaises(ValueError):masked_word(0,0,256)

    def test_original_maximum_native_last_byte_and_saturation(self):
        self.assertEqual(remap_word(0xffffff,[0x01020380,0x01020340,0x01020320]),0x03060980)
        self.assertEqual(remap_word(0xffffff,[0xffffffff]*3),0xffffffff)
        with self.assertRaises(ValueError):remap_word(0,[0,0])
        with self.assertRaises(ValueError):remap_word(-1,[0,0,0])


if __name__=='__main__':unittest.main()
