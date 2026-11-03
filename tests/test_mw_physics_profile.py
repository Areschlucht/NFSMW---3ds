"""Profile selection must follow RefSpecs, including distinct upgrade rows."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from vehicle_export_contact import component_reference
from vehicle_vlt_hash import vlt_hash as h

class Database:
    def __init__(self,value):self.value=value;self.lookups=[]
    def field_value(self,row,role):return {'value':self.value,'file_offset':128,'source_collection':row['key']}
    def find(self,cls,key):self.lookups.append((cls,key));return {'class_key':cls,'key':key}

class ProfileSelectionTests(unittest.TestCase):
    def test_refspec_target_differs_from_physical_profile(self):
        db=Database({'values':[{'class_key':h('tires'),'collection_key':h('another_car_tires')}]})
        row,selection=component_reference(db,{'key':h('physical_car')},'tires')
        self.assertEqual(row['key'],h('another_car_tires'))
        self.assertEqual(selection['upgrade_index'],0)
        self.assertEqual(selection['field_provenance']['file_offset'],128)

    def test_upgrade_array_requires_choice_and_uses_chosen_target(self):
        db=Database({'values':[{'class_key':h('brakes'),'collection_key':h(name)} for name in ['stock','upgrade']]})
        with self.assertRaises(ValueError):component_reference(db,{'key':1},'brakes')
        self.assertEqual(db.lookups,[])
        row,selection=component_reference(db,{'key':1},'brakes',1)
        self.assertEqual(row['key'],h('upgrade'));self.assertEqual(selection['upgrade_index'],1)
        for bad in [-1,2]:
            with self.assertRaises(ValueError):component_reference(db,{'key':1},'brakes',bad)

    def test_wrong_class_and_scalar_upgrade_are_rejected(self):
        db=Database({'class_key':h('engine'),'collection_key':2})
        with self.assertRaises(ValueError):component_reference(db,{'key':1},'tires')
        db=Database({'class_key':h('chassis'),'collection_key':3})
        with self.assertRaises(ValueError):component_reference(db,{'key':1},'chassis',1)
        row,selection=component_reference(db,{'key':1},'chassis')
        self.assertEqual(row['key'],3);self.assertEqual(selection['upgrade_index'],0)

if __name__=='__main__':unittest.main()
