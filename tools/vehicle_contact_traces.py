#!/usr/bin/env python3
"""Bounded original contacted-wheel reference scenarios with pinned Gekko estimate.

These are synthetic wheel-state inputs executed by original instructions, not
recordings of a complete original-game vehicle or proof of matched handling.
Scalar PSQ ABI lanes are emulated; PS1 is unused by these routines. Dolphin's
separately supplied GPL reference is host-only and is not copied into the port.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from vehicle_attributes import VehicleAttributes
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference,COMMIT,SOURCES
from vehicle_ppc_reference import OriginalPpcReference,DOL_SHA256
from vehicle_verify_original import ATTR_SHA


def traces(dol,attributes,dolphin_directory):
    raw=attributes.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ATTR_SHA:raise ValueError('Unexpected attributes source')
    db=VehicleAttributes(raw);ref=OriginalPpcReference(dol.read_bytes());ref.initialize_contact_curves()
    def layout(cls,name):
        row=db.find(cls,name);return bytes(db.bin[row['layout']:row['layout']+db.classes[row['class_key']]['base_size']])
    tire=layout('tires','bmwm3gtre46');brake=layout('brakes','bmwm3gtre46');results=[];estimate_calls=0
    surfaces=['asphalt','gravel','grass','concrete'];temporal=[]
    with DolphinFrsqrteReference(dolphin_directory) as estimate:
        for surface in surfaces:
            for axle in [0,1]:
                for speed in [-20,0,.5,20]:
                    for lateral in [-10,-1,0,1,10]:
                        for normal,hand in [(0,0),(1,0),(0,1),(1,1)]:
                            # Explicit isolated initial state, not claimed as the
                            # recovered producer's complete engine/suspension state.
                            state=bytearray(0x140);radius=ctypes_float(.6866000294685364*.5)
                            applied_hand=hand if axle else 0
                            floats={0xc4:radius,0xc8:normal,0xcc:applied_hand,0xd0:speed/radius,0xd4:4000,0xe0:100,0xe8:1,0xec:1,0xfc:speed,0x110:1,0x11c:1,0x120:1,0x124:10000,0x128:1,0x12c:1}
                            for offset,value in floats.items():struct.pack_into('>f',state,offset,value)
                            for offset,value in {0xf8:axle*2,0x10c:axle,0x138:0 if speed>0 else 2 if speed<0 else 1}.items():struct.pack_into('>I',state,offset,value)
                            arguments=[lateral,speed,abs(speed),4000,ctypes_float(1/120)]
                            returned,output=ref.contacted_wheel(tire,brake,layout('simsurface',surface),state,arguments,estimate)
                            estimate_calls+=ref.frsqrte_calls
                            fields={name:struct.unpack_from('>f',output,offset)[0] for name,offset in [('angular_speed',0xd0),('lateral_force',0xd8),('longitudinal_force',0xdc),('longitudinal_slip_speed',0xf0),('angular_acceleration',0x108),('traction_factor',0x110),('slip_angle_turns',0x118)]}
                            fields['locked']=struct.unpack_from('>I',output,0x134)[0];fields['direction']=struct.unpack_from('>I',output,0x138)[0]
                            assert returned==fields['lateral_force']
                            results.append(dict(surface=surface,axle=axle,lateral_argument=lateral,longitudinal_argument=speed,normal_input=normal,requested_handbrake=hand,applied_handbrake=applied_hand,output=fields))
        # A fixed-velocity sequence isolates lock/release response. Per-step
        # accumulator resets mirror fields explicitly reset by80246030; the
        # complete suspension/vehicle producer is still outside this harness.
        state=bytearray(0x140);radius=ctypes_float(.6866000294685364*.5)
        for offset,value in {0xc4:radius,0xd0:20/radius,0xd4:4000,0xfc:20,0x110:1,0x124:10000}.items():struct.pack_into('>f',state,offset,value)
        for offset,value in {0xf8:2,0x10c:1,0x138:0}.items():struct.pack_into('>I',state,offset,value)
        for frame in range(12):
            hand=1 if 2<=frame<6 else 0
            for offset,value in {0xc8:0,0xcc:hand,0xe0:100,0xe4:0,0xd8:0,0xdc:0,0xe8:1,0xec:1,0x11c:1,0x120:1,0x128:1,0x12c:1}.items():struct.pack_into('>f',state,offset,value)
            returned,state=ref.contacted_wheel(tire,brake,layout('simsurface','asphalt'),state,[1,20,20,4000,ctypes_float(1/120)],estimate);state=bytearray(state);estimate_calls+=ref.frsqrte_calls
            temporal.append(dict(frame=frame,handbrake=hand,angular_speed=struct.unpack_from('>f',state,0xd0)[0],lateral_force=struct.unpack_from('>f',state,0xd8)[0],longitudinal_force=struct.unpack_from('>f',state,0xdc)[0],traction_factor=struct.unpack_from('>f',state,0x110)[0],locked=struct.unpack_from('>I',state,0x134)[0]))
    return dict(dol_sha256=DOL_SHA256,attributes_sha256=ATTR_SHA,entry='0x80246580',state_initialization='explicit synthetic wheel state; see script',dolphin_commit=COMMIT,dolphin_sources=SOURCES,estimate_calls=estimate_calls,cases=len(results),fixed_velocity_lock_release=temporal,limitations=['not a recording of an original-game vehicle','wheel-state producers, full clutch/drivetrain and vehicle frames remain separate','scalar PSQ ABI lane hooks; no paired arithmetic in this selected call graph','Gekko estimate follows pinned Dolphin model; not measured on physical GameCube'],results=results)


def ctypes_float(value):return struct.unpack('>f',struct.pack('>f',value))[0]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dol',type=Path,required=True);p.add_argument('--attributes',type=Path,required=True);p.add_argument('--dolphin-reference',type=Path,required=True);a=p.parse_args();print(json.dumps(traces(a.dol,a.attributes,a.dolphin_reference),indent=2))
