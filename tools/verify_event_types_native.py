#!/usr/bin/env python3
"""Compare native modes and packed source definitions to unchanged original lookup."""
import argparse
from collections import Counter
import ctypes
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from event_type_reference import Original,original_table

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dol','catalog','pack','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();raw=a.dol.read_bytes();reference=Original(raw);root=Path(__file__).resolve().parents[1]
    catalog=json.loads(a.catalog.read_text());pack=a.pack.read_bytes();assert pack[:4]==b'NRE1' and struct.unpack_from('<I',pack,4)[0]==2
    count=struct.unpack_from('<I',pack,16)[0];packed={struct.unpack_from('<I',pack,128+i*64)[0]:struct.unpack_from('<i',pack,128+i*64+44)[0] for i in range(count)}
    names={n for n,t in original_table(raw)}|{'','multipoint','CIRCUIT','drag ','Drag','unknown'}
    names|={e['fields'].get('0x0f6bcde1',{}).get('value','') for e in catalog['race_definition_candidates']}
    cases=0;types=Counter()
    with tempfile.TemporaryDirectory(prefix='mw-event-type-host-') as temporary:
        library=Path(temporary)/'types.so';subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(root/'include'),str(root/'source_bmw/mw_event_type.c'),'-o',str(library)],check=True)
        fn=ctypes.CDLL(str(library)).mw_event_type_from_source;fn.argtypes=[ctypes.c_char_p];fn.restype=ctypes.c_int32
        assert fn(None)==-1
        for name in sorted(names):assert fn(name.encode())==reference.lookup(name);cases+=1
        for event in catalog['race_definition_candidates']:
            name=event['fields'].get('0x0f6bcde1',{}).get('value','');expected=reference.lookup(name)
            assert packed[int(event['key'],16)]==expected==fn(name.encode());types[str(expected)]+=1
    result={'original_lookup_string_cases':cases,'source_events_with_native_original_type_parity':sum(types.values()),'original_type_counts':dict(sorted(types.items())),
        'limits':['Original attribute access is supplied synthetically; lookup loop, table and strcmp remain original',
                  'Unknown source types remain -1; no filename-based race classification',
                  'Host component checks only; no SDK build or playable-race claim']}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
