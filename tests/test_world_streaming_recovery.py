import struct
import unittest

from test_world_geometry import fixture
from world_render_recovery_geometry import diagnose_model
from world_streaming_manifest import ordered_ranges
from world_streaming_policy import bind_lod_hashes, section_fallback
from world_streaming_regions import polygon_contains, decode as decode_regions, ContainingRegionSelector, NoContainingRegion
from world_streaming_containment import relate


class RecoveryTests(unittest.TestCase):
    def mismatch(self, compiled=False):
        raw, offsets = fixture(compiled=compiled)
        struct.pack_into('<H', raw, offsets[0x134011]+20, 7)
        return raw, offsets

    def test_retains_header_and_diagnostic(self):
        raw, _ = self.mismatch()
        before = bytes(raw)
        model, diagnostic = diagnose_model(raw, 0, len(raw))
        self.assertEqual(bytes(raw), before)
        self.assertEqual(len(model['faces']), 1)
        self.assertEqual(diagnostic['declared_triangles'], 7)
        self.assertEqual(diagnostic['emitted_position_index_triangles'], 1)

    def test_mismatch_does_not_bypass_consumed_constraints(self):
        for corrupt, expected in (
            (lambda raw, at: raw.__setitem__(at[0x134802], 250), 'Attribute arrays'),
            (lambda raw, at: struct.pack_into('>f', raw, at[0x134802]+12, float('nan')), 'Invalid decoded'),
            (lambda raw, at: struct.pack_into('>f', raw, at[0x134802]+12, 20), 'stored bounds'),
            (lambda raw, at: struct.pack_into('>I', raw, at[0x134801], 0xffffffff), 'Strip exceeds')):
            raw, at = self.mismatch()
            corrupt(raw, at)
            with self.assertRaisesRegex(ValueError, expected):
                diagnose_model(raw, 0, len(raw))
        raw, at = self.mismatch(compiled=True)
        raw[at[0x134802]] = 0x90
        with self.assertRaisesRegex(ValueError, 'primitive'):
            diagnose_model(raw, 0, len(raw))

    def test_source_range_validation(self):
        self.assertEqual(ordered_ranges([dict(offset=10, bytes=5)], 15), [(10, 15)])
        for sections in ([dict(offset=10, bytes=6)],
                         [dict(offset=0, bytes=10), dict(offset=9, bytes=2)]):
            with self.assertRaises(ValueError):
                ordered_ranges(sections, 15)

    def test_original_four_slot_fallback_and_sentinels(self):
        self.assertEqual(bind_lod_hashes([0,12,0,15]), [12,12,12,15])
        self.assertEqual(bind_lod_hashes([0xBE43EDBB,12,0x90F70174,0]), [12,12,12,None])
        self.assertEqual(bind_lod_hashes([7,7,7,7]), [7,7,7,7])
        self.assertEqual(bind_lod_hashes([0,0,0,0]), [None]*4)
        with self.assertRaises(ValueError):
            bind_lod_hashes([1,2,3])

    def test_original_conditional_section_fallback(self):
        self.assertEqual(section_fallback(101,{141},40),141)
        self.assertEqual(section_fallback(101,{101,141},40),101)
        self.assertEqual(section_fallback(101,set(),40),101)
        for identifier in (100,140,141,2101,-101):
            self.assertEqual(section_fallback(identifier,{identifier+40},40),identifier)

    def test_original_polygon_edge_rule(self):
        square=[(0,0),(1,0),(1,1),(0,1)]
        for point in ((0,0),(.5,.5),(0,.5)):
            self.assertTrue(polygon_contains(point,square))
        for point in ((1,1),(1,.5),(-1,.5)):
            self.assertFalse(polygon_contains(point,square))
        with self.assertRaises(ValueError):
            polygon_contains((float('nan'),0),square)

    def region_fixture(self):
        chunk=lambda key,data:struct.pack('<II',key,len(data))+data
        polygon=bytearray(60)
        struct.pack_into('<hBB',polygon,8,101,3,0)
        struct.pack_into('<4f',polygon,12,0,0,1,1)
        for i,point in enumerate(((0,0),(1,0),(0,1))):
            struct.pack_into('<2f',polygon,36+i*8,*point)
        dependency=bytearray(22)
        struct.pack_into('<hBBhh',dependency,12,101,1,1,1,141)
        return chunk(0x80034150,chunk(0x34151,struct.pack('<IIh',40,1,101))+
                     chunk(0x34152,polygon)+chunk(0x34153,dependency)+chunk(0x34155,bytes(76)))

    def test_original_region_layout_and_corruption(self):
        raw=self.region_fixture()
        region=decode_regions(raw)
        self.assertEqual(region['section_span'],40)
        self.assertEqual(region['dependencies'][0]['section_ids'],[141])
        self.assertEqual(len(region['polygons'][0]['points']),3)
        bad=bytearray(raw)
        at=region['polygons'][0]['offset']
        bad[at+10]=127
        with self.assertRaisesRegex(ValueError,'vertex count'):
            decode_regions(bad)
        bad=bytearray(raw)
        struct.pack_into('<f',bad,at+36,float('nan'))
        with self.assertRaisesRegex(ValueError,'Nonfinite'):
            decode_regions(bad)

    def test_collision_source_containment_rejects_crossing(self):
        render=dict(source_sha256='same',sections=[dict(id=141,offset=20,bytes=30)])
        collision=dict(source_sha256='same',physical_packages=[dict(id=101,offset=25,bytes=20,sha256='packet')])
        self.assertEqual(relate(render,collision)['relations'][0]['section_id'],141)
        collision['physical_packages'][0]['bytes']=30
        with self.assertRaisesRegex(ValueError,'boundary'):
            relate(render,collision)

    def test_original_selector_preserves_history_at_overlaps(self):
        polygons=[]
        for identifier,low,high in ((101,0,2),(102,1,3)):
            polygons.append(dict(id=identifier,bounds=[low,0,high,1],
                                 points=[(low,0),(high,0),(high,1),(low,1)]))
        selector=ContainingRegionSelector(dict(polygons=polygons,
                                               dependencies=[dict(id=101),dict(id=102)]))
        self.assertEqual(selector.select((1.5,.5))['id'],101)
        self.assertEqual(selector.select((2.5,.5))['id'],102)
        self.assertEqual(selector.select((1.5,.5))['id'],102)
        with self.assertRaises(NoContainingRegion):
            selector.select((10,10))


if __name__ == '__main__':
    unittest.main()
