#!/usr/bin/env python3
"""Diagnose the original directed box-contact query against overlap and contact models.

Only zero-yaw, zero-motion dyadic boxes are modeled portably here. This is not
an implementation of generic OBB/SAT overlap or the concrete player provider.
Original bytes remain unchanged; the existing bounded reference supplies calls.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct

from race_gate_containment_reference import BoxReference


def overlap(a, ah, b, bh):
    return all(abs(x-y) <= h+k for x,y,h,k in zip(a,b,ah,bh))


def directed_axis_contact(a, ah, b, bh):
    """Observed axis-aligned face-center contact policy, not general overlap.

    Inputs used for verification are exact dyadics; arbitrary float32 fused,
    rounding and tie cases are not claimed. First maximum retains source axis order (0,2,1).
    """
    if any(len(v) != 3 for v in (a,ah,b,bh)) or not all(math.isfinite(x) for v in (a,ah,b,bh) for x in v):
        raise ValueError('Finite 3D vectors required')
    if any(x <= 0 for v in (ah,bh) for x in v):
        raise ValueError('Positive half extents required')
    separation = [abs(x-y)-h-k for x,y,h,k in zip(a,b,ah,bh)]
    if max(separation) > 0:
        return False
    axis = max((0,2,1), key=lambda i: separation[i])
    return all(abs(a[i]-b[i]) <= ah[i] for i in range(3) if i != axis)


def deterministic_cases():
    rng=random.Random(0x19a8d8)
    for _ in range(160):
        a=tuple(rng.randrange(-16,17)*.5 for _ in range(3))
        b=tuple(rng.randrange(-16,17)*.5 for _ in range(3))
        ah=tuple(rng.randrange(1,9)*.5 for _ in range(3))
        bh=tuple(rng.randrange(1,9)*.5 for _ in range(3))
        yield 'original160',a,ah,b,bh
    rng=random.Random(0x80089658)
    for i in range(1000):
        a=tuple(rng.randrange(-32,33)*.25 for _ in range(3))
        ah=tuple(rng.randrange(1,17)*.25 for _ in range(3))
        bh=tuple(rng.randrange(1,17)*.25 for _ in range(3))
        if i < 500:
            b=tuple(rng.randrange(-32,33)*.25 for _ in range(3))
            kind='expanded_general'
        else:
            limits=[int((h+k)*4) for h,k in zip(ah,bh)]
            b=tuple(a[j]+rng.randrange(-limits[j],limits[j]+1)*.25 for j in range(3))
            kind='expanded_overlapping'
        yield kind,a,ah,b,bh


def trace_counterexample(raw):
    from unicorn import UC_HOOK_CODE
    box=BoxReference(raw);dots=[];pending=[];trace=[]
    def observe(u,pc,size,data):
        if pc==0x801930c8:
            first=u.reg_read(box.r.UC_PPC_REG_3);second=u.reg_read(box.r.UC_PPC_REG_4)
            pending.append((struct.unpack('>3f',bytes(u.mem_read(first,12))),
                            struct.unpack('>3f',bytes(u.mem_read(second,12)))))
        elif pc==0x801930e4:
            a,b=pending.pop();actual=box.ref.floating(1);expected=sum(x*y for x,y in zip(a,b))
            if actual != expected:
                raise AssertionError('Counterexample original dot differs from dyadic scalar oracle')
            dots.append({'first':a,'second':b,'original_result':actual,'scalar_result':expected})
        elif pc in (0x80089954,0x80089d1c,0x80089d20):
            sp=u.reg_read(box.r.UC_PPC_REG_1)
            trace.append({'pc':f'{pc:08x}',
                'selected_box':f'{u.reg_read(box.r.UC_PPC_REG_17):08x}',
                'selected_axis':struct.unpack('>i',bytes(u.mem_read(sp+0xe0,4)))[0],
                'inside_tangential_count':struct.unpack('>I',bytes(u.mem_read(sp+0xe4,4)))[0],
                'support_point':list(struct.unpack('>3f',bytes(u.mem_read(0x60002470,12))))})
    box.u.hook_add(UC_HOOK_CODE,observe)
    a=(1.5,-3,2.5);ah=(2,2,2.5);b=(-2,0,0);bh=(2.5,1.5,3.5)
    actual=box.query((a,ah,0),(b,bh,0))
    if actual or not overlap(a,ah,b,bh) or len(dots)!=46 or trace[-1]['inside_tangential_count']!=1:
        raise AssertionError('Counterexample trace changed')
    return {'first_center':a,'first_half':ah,'second_center':b,'second_half':bh,
            'plain_overlap':True,'original_contact':actual,'original_dot_checks':len(dots),
            'trace':trace,'dot_observations':dots}


def verify(raw):
    query=BoxReference(raw);counts={};differences=[];asymmetries=[];fresh=[];calls=0
    for index,(kind,a,ah,b,bh) in enumerate(deterministic_cases()):
        row=counts.setdefault(kind,{'cases':0,'overlaps':0,'directed_contacts':0,
                                    'overlap_contact_differences':0,'order_asymmetries':0})
        forward=query.query((a,ah,0),(b,bh,0));reverse=query.query((b,bh,0),(a,ah,0));calls+=2
        expected=directed_axis_contact(a,ah,b,bh);rev_expected=directed_axis_contact(b,bh,a,ah)
        if forward!=expected or reverse!=rev_expected:
            raise AssertionError(('directed contact model differs',index,a,ah,b,bh,forward,expected,reverse,rev_expected))
        plain=overlap(a,ah,b,bh);row['cases']+=1;row['overlaps']+=plain;row['directed_contacts']+=forward
        source={'case':index,'set':kind,'first_center':a,'first_half':ah,'second_center':b,'second_half':bh}
        if forward!=plain:
            row['overlap_contact_differences']+=1
            if kind=='original160':differences.append({**source,'original_contact':forward,'plain_overlap':plain})
        if forward!=reverse:
            row['order_asymmetries']+=1
            if kind=='original160':asymmetries.append({**source,'forward':forward,'reverse':reverse})
        if kind=='original160' and (forward!=plain or forward!=reverse):
            # Every original discrepancy/asymmetry is replayed with a new VM.
            clean=BoxReference(raw)
            if clean.query((a,ah,0),(b,bh,0))!=forward:
                raise AssertionError('Fresh VM differs from reused reference')
            fresh.append(index)
    traced=trace_counterexample(raw)
    if struct.unpack('>3I',query.ref.dol.read(0x803d3ef8,12))!=(0,2,1):
        raise AssertionError('Original axis order differs')
    image=query.ref.dol
    code_windows=[]
    for start,end in ((0x800897b0,0x8008985c),(0x80089954,0x800899c8),
                      (0x80089a84,0x80089ab0),(0x80089b00,0x80089b40),
                      (0x80089d0c,0x80089d20)):
        code_windows.append({'start':f'{start:08x}','end_exclusive':f'{end:08x}',
                             'sha256':hashlib.sha256(image.read(start,end-start)).hexdigest()})
    return {'schema':1,'dol_sha256':hashlib.sha256(raw).hexdigest(),'sets':counts,
            'sweep_original_query_calls':calls,'fresh_reference_replay_calls':len(fresh),
            'counterexample_trace_calls':1,'total_original_query_calls':calls+len(fresh)+1,
            'source_axis_order':{'address':'803d3ef8','values':[0,2,1],
                'sha256':hashlib.sha256(image.read(0x803d3ef8,12)).hexdigest()},
            'directed_model_mismatches':0,
            'fresh_reference_replay_cases':fresh,'original160_overlap_differences':differences,
            'original160_order_asymmetries':asymmetries,'counterexample':traced,
            'code_windows':code_windows,
            'resolution':'The compared original routine constructs directed contact data; its zero-yaw zero-motion face-center policy is not a symmetric geometric-overlap oracle.',
            'limits':['Portable model validated only for supplied exact dyadic axis-aligned zero-motion boxes',
                'No rotated OBB equivalence, concrete vehicle provider, sweep or notification-scheduling recovery is claimed',
                'Shared paired hooks still have broader floating-point limitations; all46 dots in the specific counterexample separately match scalar arithmetic',
                'No runtime/shared source edit, SDK build or original executable patch']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=verify(a.dol.read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('sets','sweep_original_query_calls','total_original_query_calls','directed_model_mismatches','fresh_reference_replay_cases')}))
