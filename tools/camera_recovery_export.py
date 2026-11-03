#!/usr/bin/env python3
"""Export original camerainfo and BMW references with byte provenance."""
import argparse,hashlib,json
from pathlib import Path
from camera_recovery_verify import ATTR_SHA,LABELS
from vehicle_attributes import VehicleAttributes
from vehicle_vlt_hash import vlt_hash
FIELDS=[0x585517f3,0xd74c1435,0x0c2da793,0xccf03cb3,0x10204a90,0x4b675dc8,0xd76a6fad]
NAMES=['bumper','hood','close','far','superfar','drift','pursuit']
def export(path):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('ATTRIBUTES source differs')
    db=VehicleAttributes(raw,LABELS);vehicle=db.find('ecar','bmwm3gtre46');rows=[]
    for mode,(field,name) in enumerate(zip(FIELDS,NAMES)):
        reference=db.field_value(vehicle,field);value=reference['value'];row=db.find(value['class_key'],value['collection_key'])
        rows.append(dict(mode=mode,selector_name=name,ecar_field_key=f'{field:08x}',reference=reference,collection_key=f'{row["key"]:08x}',collection_name=db.label(row['key']),fields=db.fields(row)))
    return dict(attributes_sha256=ATTR_SHA,vehicle='bmwm3gtre46',mode_selector='800687C8..800688B0',profile_cache='800688DC..80068AF0',profile_index='1 if original_view_state==3 else0; notspeed interpolation',modes=rows,limitations=['Camera profile scalar data/reference bindings only','No complete camera position/dynamics, viewport producer or original input preference claim'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--attributes',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(export(a.attributes),indent=2)+'\n');print(a.output)
