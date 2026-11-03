#!/usr/bin/env python3
"""Strict reader for the observed GameCube VPAK/legacy Attrib database.

VPAK metadata is little-endian; embedded BIN/VLT data is big-endian. The GC
optional-entry flag is a byte followed by padding, not a swapped PC uint16.
Names supplied externally are hash labels, not evidence for physical units.
Layouts cross-checked with NFSTools/VaultLib (MIT), commit
c1c9e94044ef0eae9ebc43c5a2b3a70ef5369d86. This independent reader retains
raw field/provenance information and never executes the database contents.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from vehicle_vlt_hash import vlt_hash

# Candidate labels match original schema keys. Numeric units are established
# separately by original-code consumers; these names alone do not prove units.
KNOWN_LABELS = ['AERO_CG', 'AERO_COEFFICIENT', 'ASPECT_RATIO', 'BASE_MATERIAL', 'BEHAVIOR_MECHANIC_AUDIO', 'BEHAVIOR_MECHANIC_DAMAGE', 'BEHAVIOR_MECHANIC_DRAW', 'BEHAVIOR_MECHANIC_EFFECTS', 'BEHAVIOR_MECHANIC_ENGINE', 'BEHAVIOR_MECHANIC_INPUT', 'BEHAVIOR_MECHANIC_RESET', 'BEHAVIOR_MECHANIC_RIGIDBODY', 'BEHAVIOR_MECHANIC_SUSPENSION', 'BEHAVIOR_ORDER', 'BRAKES', 'BRAKE_LOCK', 'BodyDive', 'BodyRoll', 'BodySquat', 'CAMERA_NOISE', 'CG', 'CLASS', 'CLUTCH_SLIP', 'COLLISION_BOX_PAD', 'CamberFront', 'CamberRear', 'CollectionName', 'DEBUG_COLOUR', 'DEFAULT_COL_BOX', 'DIFFERENTIAL', 'DRAG', 'DRAG_ANGULAR', 'DRAG_COEFFICIENT', 'DRIVE_GRIP', 'DYNAMIC_GRIP', 'DamageEffect', 'DeathEffect', 'DefaultPresetRide', 'EBRAKE', 'ENGINE_BRAKING', 'EngineBlownEffect', 'EngineRev', 'EngineRevAngle', 'EngineRevSpeed', 'EngineVibrationFreq', 'EngineVibrationMax', 'EngineVibrationMin', 'EventSequencer', 'ExtraPitch', 'ExtraRearTireOffset', 'FECompressions', 'FFB_ROLL', 'FFB_SKID', 'FFB_SLIP', 'FINAL_GEAR', 'FLOW_RATE', 'FLYWHEEL_MASS', 'FRONT_AXLE', 'FRONT_WEIGHT_BIAS', 'FrontCamber', 'GEAR_EFFICIENCY', 'GEAR_RATIO', 'GRAVITY', 'GRIP_SCALE', 'GROUND_ELASTICITY', 'GROUND_FRICTION', 'GROUND_MOMENT_SCALE', 'HIGH_BOOST', 'HandlingRating', 'HitchHeat', 'HornType', 'IDLE', 'IMMOBILE_OBJECT_COLLISIONS', 'INSTANCE_COLLISIONS_3D', 'IsSkinned', 'KitWheelOffsetFront', 'KitWheelOffsetRear', 'LATERAL_GRIP', 'LIGHT_COPBLUE', 'LIGHT_COPRED', 'LIGHT_COPWHITE', 'LOW_BOOST', 'MASS', 'MATERIAL_STRENGTH', 'MAX_RPM', 'MODEL', 'MaxTireSteer', 'MissShiftEffect', 'NATURAL_ANGULAR_DAMPING', 'NOSEffect', 'NOS_CAPACITY', 'NOS_DISENGAGE', 'NO_GROUND_COLLISIONS', 'NO_OBJ_COLLISIONS', 'NO_WORLD_COLLISIONS', 'OBJ_ELASTICITY', 'OBJ_FRICTION', 'OBJ_MOMENT_SCALE', 'OPTIMAL_SHIFT', 'OnBottomOut', 'OnBottomScrape', 'OnHitGround', 'OnHitWorld', 'OnScrapeGround', 'OnScrapeWorld', 'OnTireBlow', 'PSI', 'PlayerUsable', 'RECHARGE_MAX', 'RECHARGE_MAX_SPEED', 'RECHARGE_MIN', 'RECHARGE_MIN_SPEED', 'RED_LINE', 'RENDER_MOTION', 'RIDE_HEIGHT', 'RIM_SIZE', 'ROLLING_RESISTANCE', 'ROLL_CENTER', 'RSNMCHUNK_FERESNAMES', 'RandomOpponent', 'ReflectionOffset', 'RenderNoise', 'RideHeight', 'RiskCar_Tier', 'RoadNoise', 'SECTION_WIDTH', 'SHIFT_SPEED', 'SHOCK_BLOWOUT', 'SHOCK_DIGRESSION', 'SHOCK_EXT_STIFFNESS', 'SHOCK_STIFFNESS', 'SHOCK_VALVING', 'SLEEP_VELOCITY', 'SPEED_LIMITER', 'SPOOL', 'SPOOL_TIME_DOWN', 'SPOOL_TIME_UP', 'SPRING_PROGRESSION', 'SPRING_STIFFNESS', 'STATIC_GRIP', 'STEERING', 'STICK', 'SWAYBAR_STIFFNESS', 'ShiftAngle', 'ShiftSND', 'ShiftSpeed', 'SkidFX', 'SlipFX', 'SteerSpeed', 'TENSOR_SCALE', 'TORQUE', 'TORQUE_BOOST', 'TORQUE_CONVERTER', 'TORQUE_SPLIT', 'TRACK_WIDTH', 'TRAVEL', 'TireDriveEffects', 'TireOffsets', 'TireSkidWidth', 'TireSkidWidthKitScale', 'TireSlideEffects', 'TireSlipEffects', 'TrafficEngType', 'Trailer', 'TurboSND', 'VACUUM', 'VerbalType', 'WALL_ELASTICITY', 'WALL_FRICTION', 'WHEEL_BASE', 'WORLD_FRICTION', 'WORLD_MOMENT_SCALE', 'WheelEffectFrequency', 'WheelEffectIntensity', 'WheelHopScale', 'WheelSpokeCount', 'WheelSurfaceEffect', 'WheelWell', 'WooshType', 'YAW_CONTROL', 'YAW_SPEED', 'acceltrans', 'aivehicle', 'aud_moment_strm', 'aud_stitch_loop', 'audioimpact', 'audioscrape', 'audiosystem', 'brakes', 'brakes_current', 'brakes_upgrades', 'camerainfo', 'chassis', 'chassis_current', 'chassis_upgrades', 'chopperspecs', 'collisionreactions', 'controller', 'damagespecs', 'default', 'ecar', 'effects', 'emitterdata', 'emittergroup', 'emitteruv', 'engine', 'engine_current', 'engine_upgrades', 'engineaudio', 'explosion', 'fecooling', 'frontend', 'fuelcell_effect', 'fuelcell_emitter', 'gameplay', 'induction', 'induction_current', 'induction_upgrades', 'infractions', 'junkman', 'light_flares_cg', 'milestonetypes', 'music', 'nos', 'nos_current', 'nos_upgrades', 'ocean', 'presetride', 'pursuitescalation', 'pursuitlevels', 'pursuitsupport', 'pvehicle', 'racers', 'rigidbodyspecs', 'shiftpattern', 'simsurface', 'smackable', 'speech', 'speechtune', 'system', 'tires', 'tires_current', 'tires_upgrades', 'trafficpattern', 'transmission', 'transmission_current', 'transmission_upgrades', 'turbosfx', 'visuallook', 'visuallookeffect', 'visuallooktransition', 'world']


def checked(data, offset, size):
    if not isinstance(offset, int) or not isinstance(size, int) or offset < 0 or size < 0 or offset+size > len(data):
        raise ValueError('Attribute range exceeds its stream')
    return memoryview(data)[offset:offset+size]


def unpack(fmt, data, offset):
    return struct.unpack(fmt, checked(data, offset, struct.calcsize(fmt)))


def string(data, offset, limit=4096):
    if offset < 0 or offset >= len(data):
        raise ValueError('String pointer exceeds BIN')
    end = data.find(b'\0', offset, min(len(data), offset+limit))
    if end < 0:
        raise ValueError('Unterminated bounded BIN string')
    return bytes(data[offset:end]).decode('ascii')


def chunks(data):
    result = {}
    at = 0
    while at < len(data):
        key, size = unpack('>II', data, at)
        if size < 8 or at+size > len(data) or key in result:
            raise ValueError('Invalid or duplicate VLT chunk')
        result[key] = (at+8, at+size)
        at += size
    return result


class VehicleAttributes:
    def __init__(self, raw, labels=(), dependency=None):
        self.raw = bytes(raw)
        self.sha256=hashlib.sha256(self.raw).hexdigest();self.dependency=dependency
        if len(raw) < 128 or raw[:4] != b'VPAK':
            raise ValueError('Missing VPAK header')
        version, header_size, variant, reserved, bin_size, vlt_size, bin_offset, vlt_offset = unpack('<8I', raw, 4)
        if (version,header_size,reserved)!=(1,64,0) or variant not in (3,9):
            raise ValueError('Unsupported VPAK variant')
        self.variant=variant;alignment=128 if variant==3 else 64
        if bin_offset < 128 or vlt_offset < 128 or bin_offset % alignment or vlt_offset % alignment or min(bin_size, vlt_size) < 8:
            raise ValueError('Invalid VPAK stream alignment/size')
        checked(raw, bin_offset, bin_size); checked(raw, vlt_offset, vlt_size)
        if max(bin_offset, vlt_offset) < min(bin_offset+bin_size, vlt_offset+vlt_size):
            raise ValueError('Overlapping VPAK streams')
        self.offsets = {'bin':bin_offset, 'vlt':vlt_offset}
        self.original = {'bin':bytes(raw[bin_offset:bin_offset+bin_size]), 'vlt':bytes(raw[vlt_offset:vlt_offset+vlt_size])}
        self.bin = bytearray(self.original['bin']); self.vlt = bytearray(self.original['vlt'])
        self.names = {}
        for label in (*KNOWN_LABELS, *labels):
            if label and not label.startswith('0x'):
                try: key=vlt_hash(label)
                except UnicodeEncodeError: continue
                self.names.setdefault(key, set()).add(label)
        tag, size = unpack('>II', self.bin, 0)
        if tag != 0x53747245 or size < 8 or size > len(self.bin):
            raise ValueError('Missing bounded StrE name table')
        at = 8
        while at < size:
            label = string(self.bin, at, size-at)
            if label:
                self.names.setdefault(vlt_hash(label), set()).add(label)
            at += len(label)+1
        if dependency:
            for key,names in dependency.names.items():self.names.setdefault(key,set()).update(names)
        self.chunk_ranges = chunks(self.vlt)
        if not {0x4465704e, 0x5374724e, 0x4461744e, 0x4578704e, 0x5074724e} <= self.chunk_ranges.keys():
            raise ValueError('Incomplete VLT directory')
        self.fixups = []; seen = set(); target = None; ended = False
        start, end = self.chunk_ranges[0x5074724e]
        at = start
        while at+12 <= end:
            offset, kind, index, destination = unpack('>IHHI', self.vlt, at); at += 12
            if kind == 0:
                ended = True
                if any(self.vlt[at:end]): raise ValueError('Nonzero pointer-table trailer')
                break
            if kind == 2:
                if index not in (0,1) or offset or destination: raise ValueError('Invalid pointer target selector')
                target = 'vlt' if index == 0 else 'bin'
                continue
            if target is None or kind not in (1,3) or (kind == 1 and (index or destination)) or (kind == 3 and index != 1):
                raise ValueError('Unsupported pointer relocation')
            if (target, offset) in seen: raise ValueError('Duplicate relocation slot')
            seen.add((target, offset));data = self.vlt if target == 'vlt' else self.bin
            checked(data, offset, 4)
            if destination and destination >= len(self.bin): raise ValueError('Relocation destination exceeds BIN')
            struct.pack_into('>I', data, offset, destination)
            self.fixups.append(dict(stream=target, offset=offset, destination=destination, kind=kind))
        if not ended: raise ValueError('Unterminated pointer table')
        start, end = self.chunk_ranges[0x4578704e]
        count, = unpack('>I', self.vlt, start)
        if count > 100000 or start+4+count*20 > end: raise ValueError('Invalid export count')
        exports = [unpack('>5I', self.vlt, start+4+i*20) for i in range(count)]
        data_start, data_end = self.chunk_ranges[0x4461744e]
        for key, kind, zero, size, offset in exports:
            if zero or offset < data_start or offset+size > data_end: raise ValueError('Export outside DatN')
        databases = [e for e in exports if e[1] == 0xcbbc628f]
        if databases:
            if len(databases)!=1:raise ValueError('Expected one database definition')
            _, _, _, size, offset = databases[0]
            class_reserve, default_size, ntypes, names_offset = unpack('>4I', self.vlt, offset)
            if ntypes > 4096 or size != 16+ntypes*4: raise ValueError('Invalid type directory')
            self.types = {}
            for i in range(ntypes):
                label = string(self.bin, names_offset); names_offset += len(label)+1
                key = vlt_hash(label);type_size, = unpack('>I', self.vlt, offset+16+i*4)
                if key in self.types: raise ValueError('Duplicate type definition')
                self.types[key] = dict(name=label, size=type_size)
                self.names.setdefault(key,set()).add(label)
        elif dependency is not None and variant==9:
            self.types=dict(dependency.types)
        else:raise ValueError('Dependent attribute database requires its schema source')
        self.classes = dict(dependency.classes) if dependency else {}; self.collections = {}
        for export_key, kind, _, size, offset in exports:
            if kind != 0x5e970cbc: continue
            if size != 28: raise ValueError('Unsupported class header')
            key, reserve, count, definitions, base_size, zero, required = unpack('>7I', self.vlt, offset)
            if key != export_key or zero or count > 4096 or required > count or key in self.classes:
                raise ValueError('Invalid class definition')
            checked(self.bin, definitions, count*16);fields = {}
            for i in range(count):
                fk, typ, position, item_size, capacity, flags, power = unpack('>IIHHHBB', self.bin, definitions+i*16)
                if fk in fields or typ not in self.types or not item_size or not capacity or power>4 or flags & ~0x2f:
                    raise ValueError('Invalid field definition')
                if flags & 2 and position+item_size > base_size: raise ValueError('Field outside required layout')
                fields[fk] = dict(key=fk, type_key=typ, offset=position, size=item_size, capacity=capacity, flags=flags, alignment=1<<power,
                                  definition_offset=definitions+i*16)
            if sum((f['flags'] & 0x0a)==2 for f in fields.values()) != required: raise ValueError('Required searchable field count mismatch')
            self.classes[key] = dict(key=key, reserve=reserve, base_size=base_size, fields=fields, export_offset=offset)
        for export_key, kind, _, size, offset in exports:
            if kind in (0xcbbc628f,0x5e970cbc): continue
            if kind != 0x8e112eb7 or size < 32: raise ValueError('Unsupported export type/size')
            key, cls, parent, reserve, zero, count, ntypes, layout = unpack('>8I', self.vlt, offset)
            if cls not in self.classes or zero or reserve != count or count > 4096 or ntypes > 4096 or size != 32+ntypes*4+count*12:
                raise ValueError('Invalid collection header')
            types = unpack('>'+str(ntypes)+'I', self.vlt, offset+32)
            if any(t not in self.types for t in types): raise ValueError('Unknown collection type')
            cl = self.classes[cls]
            if cl['base_size'] and not layout: raise ValueError('Missing required layout')
            if layout: checked(self.bin, layout, cl['base_size'])
            entries = {}
            for i in range(count):
                at = offset+32+ntypes*4+i*12
                fk, value, type_index, flags, pad = unpack('>IIHBB', self.vlt, at)
                if fk not in cl['fields'] or fk in entries or pad or type_index >= ntypes:
                    raise ValueError('Invalid collection field entry')
                field = cl['fields'][fk];inline = field['size'] <= 4 and not field['flags']&1
                if types[type_index] != field['type_key'] or flags != (0x20 if inline else 2 if field['flags']&1 else 0):
                    raise ValueError('Collection field type/flags mismatch')
                entries[fk] = dict(stream='vlt' if inline else 'bin', offset=at+4 if inline else value)
            if (cls,key) in self.collections: raise ValueError('Duplicate collection')
            self.collections[cls,key] = dict(key=key, class_key=cls, parent=parent, layout=layout, entries=entries, export_offset=offset)
        for (cls,key), row in self.collections.items():
            ancestors=set();database=self
            while row['parent']:
                if row['parent'] in ancestors:raise ValueError('Cyclic collection parent')
                ancestors.add(row['parent']);row,database=database._resolve_collection(cls,row['parent'])

    def _resolve_collection(self,cls,key):
        if (cls,key) in self.collections:return self.collections[cls,key],self
        if self.dependency:return self.dependency._resolve_collection(cls,key)
        raise ValueError('Missing collection parent')

    def label(self, key):
        labels = self.names.get(key, ())
        return next(iter(labels)) if len(labels)==1 else f'0x{key:08x}'

    def find(self, cls, collection):
        return self.collections[(vlt_hash(cls) if isinstance(cls,str) else cls, vlt_hash(collection) if isinstance(collection,str) else collection)]

    def _value(self, stream, offset, field):
        data = self.vlt if stream == 'vlt' else self.bin
        size = field['size'];typ = self.types[field['type_key']]['name']
        if field['flags'] & 1:
            capacity,count,item_size,flags = unpack('>4H', data, offset)
            if count>capacity or capacity>field['capacity'] or item_size!=size or flags not in (0,0x8000): raise ValueError('Invalid typed array header')
            cursor=offset+8;values=[];item=dict(field,flags=field['flags']&~1)
            for i in range(capacity):
                cursor=(cursor+field['alignment']-1)&-field['alignment'];checked(data,cursor,size)
                if i<count: values.append(self._value(stream,cursor,item)[0])
                cursor+=size
            return dict(capacity=capacity,count=count,values=values), cursor-offset
        raw=checked(data,offset,size)
        formats={'type_bStringHash':'>I','EA::Reflection::Float':'>f','EA::Reflection::UInt32':'>I','EA::Reflection::Int32':'>i','EA::Reflection::UInt16':'>H','EA::Reflection::Int16':'>h','EA::Reflection::UInt8':'>B','EA::Reflection::Int8':'>b','EA::Reflection::Bool':'>I','AxlePair':'>2f','Attrib::Types::Vector2':'>2f','Attrib::Types::Vector3':'>3f','Attrib::Types::Vector4':'>4f'}
        if typ in formats:
            if struct.calcsize(formats[typ])!=size: raise ValueError('Primitive type size mismatch')
            values=struct.unpack(formats[typ],raw)
            if any(isinstance(v,float) and not math.isfinite(v) for v in values): raise ValueError('Nonfinite attribute value')
            value=values[0] if len(values)==1 else list(values)
            if typ=='EA::Reflection::Bool':
                if value not in (0,1): raise ValueError('Invalid bool value')
                value=bool(value)
        elif typ=='EA::Reflection::Text':
            pointer,=unpack('>I',data,offset);value=string(self.bin,pointer) if pointer else None
        elif typ=='Attrib::RefSpec':
            cls,key,pointer=unpack('>3I',data,offset);value=dict(class_key=cls,collection_key=key,class_name=self.label(cls),collection_name=self.label(key),runtime_pointer=pointer)
        elif typ=='Attrib::StringKey' and size==16:
            wide,key,pointer=unpack('>QII',data,offset);label=string(self.bin,pointer) if pointer else None
            if label is not None and vlt_hash(label)!=key: raise ValueError('StringKey hash/text mismatch')
            value=dict(text=label,hash32=key,hash64=wide)
        else: value=dict(raw_hex=bytes(raw).hex(),type=typ)
        return value,size

    def field_value(self, row, field, inherited=True):
        fk=vlt_hash(field) if isinstance(field,str) else field;cl=self.classes[row['class_key']]
        definition=cl['fields'][fk];owner=row;database=self
        while True:
            if definition['flags']&2:
                stream='bin';offset=owner['layout']+definition['offset'];break
            if fk in owner['entries']:
                stream=owner['entries'][fk]['stream'];offset=owner['entries'][fk]['offset'];break
            if not inherited or not owner['parent']: raise KeyError(f'Missing optional field {self.label(fk)}')
            owner,database=database._resolve_collection(owner['class_key'],owner['parent'])
        value,size=database._value(stream,offset,definition)
        if definition['flags']&2 and definition['offset']+size > cl['base_size']:
            raise ValueError('Typed field exceeds required layout')
        return dict(field_key=fk,field_name=self.label(fk),type=self.types[definition['type_key']]['name'],value=value,
                    source_collection=owner['key'],stream=stream,stream_offset=offset,file_offset=database.offsets[stream]+offset,source_sha256=database.sha256,
                    original_bytes=bytes(checked(database.original[stream],offset,size)).hex())

    def fields(self, row, inherited=True):
        result={}
        for key in self.classes[row['class_key']]['fields']:
            try: result[self.label(key)]=self.field_value(row,key,inherited)
            except KeyError: pass
        return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attributes',type=Path);parser.add_argument('--labels',type=Path)
    parser.add_argument('--collection',default='bmwm3gtre46');parser.add_argument('--dependency',type=Path)
    args=parser.parse_args();labels=args.labels.read_text(encoding='utf-8-sig').splitlines() if args.labels else ()
    dependency=VehicleAttributes(args.dependency.read_bytes(),labels) if args.dependency else None
    db=VehicleAttributes(args.attributes.read_bytes(),labels,dependency)
    rows=[]
    for (cls,key),row in db.collections.items():
        if key==vlt_hash(args.collection): rows.append(dict(class_name=db.label(cls),class_key=cls,collection=db.label(key),parent=db.label(row['parent']) if row['parent'] else None,fields=db.fields(row)))
    print(json.dumps(dict(sha256=hashlib.sha256(db.raw).hexdigest(),classes=len(db.classes),collections=len(db.collections),fixups=len(db.fixups),rows=rows),indent=2))
