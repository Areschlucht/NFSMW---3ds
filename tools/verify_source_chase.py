#!/usr/bin/env python3
"""Compare the native source-motion adapter's channels with original PPC parts.

This verifies component composition for explicit inputs. It does not execute the
whole original chase update or prove the native controller matches its providers.
"""
import argparse,ctypes,hashlib,json,math,struct,subprocess,tempfile
from pathlib import Path
from camera_recovery_cubic_verify import Cubic,CubicReference,packed
from camera_recovery_direction_verify import DirectionReference
from camera_recovery_tuning_verify import Tuning,TuningReference
from vehicle_dolphin_frsqrte import DolphinFrsqrteReference
from vehicle_ppc_reference import DOL_SHA256

class Profile(ctypes.Structure):
    _fields_=[(n,ctypes.c_float*2) for n in ('angle','lag','height','lateral','fov','stiffness')]+[('tilting',ctypes.c_uint32*2)]
class Cache(ctypes.Structure):
    _fields_=[('angle',ctypes.c_uint16),('lag',ctypes.c_float),('height',ctypes.c_float),('lat',ctypes.c_float),('fov',ctypes.c_uint16),('stiffness',ctypes.c_float),('tilting',ctypes.c_uint16),('index',ctypes.c_uint)]
class Config(ctypes.Structure):
    _fields_=[('profile',Profile),('cache',Cache),('lower',Tuning),('upper',Tuning),('ecar',ctypes.c_uint32),('mode',ctypes.c_uint)]
class Asset(ctypes.Structure):
    _fields_=[('data',ctypes.c_void_p),('bytes',ctypes.c_size_t),('count',ctypes.c_uint32),('profiles',ctypes.c_uint32),('tuning',ctypes.c_uint32)]
class Motion(ctypes.Structure):
    _fields_=[('channel',Cubic*3),('direction',ctypes.c_float*3),('initialized',ctypes.c_bool)]

def set_original_targets(reference,channels,target):
    from unicorn import ppc_const as r
    u=reference.uc;u.mem_write(reference.INSTANCE,b''.join(packed(c) for c in channels));u.mem_write(reference.LAYOUT,target)
    u.reg_write(r.UC_PPC_REG_3,reference.INSTANCE);u.reg_write(r.UC_PPC_REG_4,reference.LAYOUT);u.reg_write(r.UC_PPC_REG_LR,0x81700100)
    reference.allowed=((0x8020836c,0x802083c4),);reference.run(0x8020836c,0x81700100)
    result=bytes(u.mem_read(reference.INSTANCE,132))
    return [Cubic(*struct.unpack('>4f',result[i*44:i*44+16]),(ctypes.c_float*4)(*struct.unpack('>4f',result[i*44+16:i*44+32])),*struct.unpack('>2f2h',result[i*44+32:i*44+44])) for i in range(3)]

def verify(dol,asset_path,dolphin):
    root=Path(__file__).resolve().parents[1];raw=dol.read_bytes();data=asset_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DOL_SHA256:raise ValueError('Unexpected DOL')
    estimate=DolphinFrsqrteReference(dolphin);direction=DirectionReference(raw,estimate.estimate);tuning=TuningReference(raw);cubic=CubicReference(raw)
    count=0;directions=0
    with tempfile.TemporaryDirectory(prefix='source-chase-') as temporary:
        so=Path(temporary)/'source.so';sources=['mw_chase_source','mw_original_camera_direction','mw_original_camera_profile','mw_original_camera_tuning','mw_original_camera_cubic','mw_gekko_math']
        subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fno-fast-math','-ffp-contract=off','-shared','-fPIC','-I'+str(root/'include'),*[str(root/'source_bmw'/(s+'.c')) for s in sources],'-lm','-o',str(so)],check=True)
        lib=ctypes.CDLL(str(so));open_=lib.mw_chase_asset_open;open_.argtypes=[ctypes.POINTER(Asset),ctypes.c_void_p,ctypes.c_size_t];open_.restype=ctypes.c_bool
        find=lib.mw_chase_asset_vehicle;find.argtypes=[ctypes.POINTER(Asset),ctypes.c_uint32,ctypes.c_uint,ctypes.c_int,ctypes.c_float,ctypes.POINTER(Config)];find.restype=ctypes.c_bool
        arr=ctypes.c_float*3;reset=lib.mw_chase_source_reset;reset.argtypes=[ctypes.POINTER(Motion),ctypes.POINTER(Config),arr,arr,ctypes.c_float];reset.restype=ctypes.c_bool
        step=lib.mw_chase_source_step;step.argtypes=[ctypes.POINTER(Motion),ctypes.POINTER(Config),arr,arr,ctypes.c_float,ctypes.c_float];step.restype=ctypes.c_bool
        storage=ctypes.create_string_buffer(data);a=Asset();assert open_(ctypes.byref(a),storage,len(data))
        for mode in (2,3,5):
            config=Config();assert find(ctypes.byref(a),0x4e085fb3,mode,0,1,ctypes.byref(config));motion=Motion();assert reset(ctypes.byref(motion),ctypes.byref(config),arr(0,0,0),arr(0,0,1),0)
            expected=[Cubic.from_buffer_copy(bytes(c)) for c in motion.channel]
            for frame in range(64):
                yaw=frame*.037;forward=arr(math.sin(yaw),0,math.cos(yaw));speed=ctypes.c_float((0,7,8,10,13,22,45,71)[frame%8]).value
                lateral=math.sin(frame*.19)*8;sign=-1 if 24<=frame<40 else 1
                velocity=arr(sign*speed*forward[0]+lateral*forward[2],0,sign*speed*forward[2]-lateral*forward[0]);dt=ctypes.c_float((1/30,1/60,1/120)[frame%3]).value
                param=tuning.parameter(speed);sample=tuning.blend(struct.pack('>44f',*config.lower.fields),struct.pack('>44f',*config.upper.fields),param)
                durations=struct.unpack_from('>3f',sample,160)
                for axis in range(3):
                    expected[axis].duration=durations[axis];part=cubic.step(expected[axis],dt,0,0)
                    values=struct.unpack('>10f2h',part);expected[axis]=Cubic(*values[:4],(ctypes.c_float*4)(*values[4:8]),*values[8:])
                target=direction.direction(velocity,forward,speed);directions+=1;old_direction=[c.value for c in expected]
                expected=set_original_targets(cubic,expected,target)
                assert step(ctypes.byref(motion),ctypes.byref(config),velocity,forward,speed,dt)
                for axis in range(3):
                    if packed(motion.channel[axis])!=packed(expected[axis]):raise AssertionError((mode,frame,axis,'whole channel differs'))
                    if struct.pack('>f',motion.direction[axis])!=struct.pack('>f',old_direction[axis]):raise AssertionError('published value differs')
                    count+=1
    estimate.close()
    return {'dol_sha256':DOL_SHA256,'asset_sha256':hashlib.sha256(data).hexdigest(),'complete_channel_bit_cases':count,'direction_target_cases':directions,'original_windows':['80073028..80073100','80071BB8..80071EC0','80073EF8..80073F24','80208128..80208268','8020836C..802083C0'],'guest_bytes_patched':0,'limits':['Component sequence with explicit native controller inputs, not a full original chase execution','Duration biases and post-target timer/vertical attenuation explicitly absent in current adapter','Dolphin reference supplies original frsqrte estimate; scalar PSQ stack ABI model reused','Original pose providers, placement, input mode policy, collision and timestamp scheduler remain incomplete']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dol','asset','dolphin','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=verify(a.dol,a.asset,a.dolphin);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('complete_channel_bit_cases','direction_target_cases','guest_bytes_patched')}))
