#!/usr/bin/env python3
"""Read-only inspector for the supplied USA GC PFDx 5.1 music metadata.

This inventories tables, not the PathFinder interpreter or full audio streams.
Header/table interpretation is cross-checked with vgmstream's MPF/SCHl readers;
see docs/research/music-metadata-findings.md. No original bytes are emitted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

STREAM_BYTES = {'MW_MUSIC':131595008, 'MW_MUS_1':22730752,
                'MW_MUS_2':22251264, 'MW_MUS_3':28529920, 'MW_MUS_4':31780096}
SOURCE_NAMES = tuple('SOUND-PFDATA-'+k+'.MPF' for k in STREAM_BYTES)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_mpf(data, stream_bytes):
    require(len(data)>=0x48 and data[:4]==b'PFDx', 'Missing big-endian PFDx header')
    require(data[4:6]==b'\x05\x01', 'Inspector only supports observed v5.1')
    offsets=struct.unpack_from('>10I', data, 0x14)
    require(offsets[0]==0x48 and offsets[-1]==len(data), 'Header/file bounds differ')
    require(all(0x48<=x<=len(data) and x%4==0 for x in offsets), 'Unaligned/out-of-bounds table')
    require(all(a<=b for a,b in zip(offsets,offsets[1:])), 'Unordered table offsets')
    counts=dict(zip(('tracks','sections','events','routers','variables'),data[0x0d:0x12]))
    counts['nodes']=struct.unpack_from('>H',data,0x12)[0]
    require(counts['tracks']==1, 'Only observed single-track maps supported')
    require(offsets[0]+counts['nodes']*2<=offsets[1], 'Node index table exceeds region')
    nodes=[struct.unpack_from('>H',data,offsets[0]+i*2)[0]*4 for i in range(counts['nodes'])]
    require(nodes and nodes[0]==offsets[1], 'Node index/data start mismatch')
    require(all(offsets[1]<=x<offsets[2] for x in nodes), 'Node pointer exceeds node region')
    require(all(a<b for a,b in zip(nodes,nodes[1:])), 'Unordered/duplicate node pointer')
    require(not any(data[offsets[0]+counts['nodes']*2:offsets[1]]), 'Nonzero node table padding')
    track_table,track_data,samples_table,eof=offsets[6:]
    require(track_table+4<=track_data, 'Track pointer table truncated')
    track_record=struct.unpack_from('>I',data,track_table)[0]*4
    require(track_data<=track_record and track_record+12<=samples_table, 'Track record outside region')
    sample_start,subbanks=struct.unpack_from('>IH',data,track_record)
    require(sample_start==0 and subbanks==0, 'Unobserved subbank/sample-index variant')
    require((eof-samples_table)%8==0 and eof>samples_table, 'Partial/empty sample table')
    entries=[{'index':i, 'stream_offset':offset*128, 'duration_ms':duration}
             for i,(offset,duration) in enumerate(struct.iter_unpack('>II',data[samples_table:eof]))]
    require(all(0<=r['stream_offset']<stream_bytes and r['duration_ms']>0 for r in entries),
            'Sample range/duration outside paired archive entry')
    require(all(a['stream_offset']<b['stream_offset'] for a,b in zip(entries,entries[1:])),
            'Unordered/duplicate streamed sample offset')
    return {'bytes':len(data), 'sha256':sha(data), 'byte_order':'big', 'version':[5,1],
            'counts':counts, 'table_offsets_hex':[f'{x:08x}' for x in offsets],
            'table_region_sha256':[sha(data[a:b]) for a,b in zip(offsets,offsets[1:])],
            'node_pointer_count_checked':len(nodes), 'streamed_sample_count':len(entries),
            'track_checksum_hex':data[track_record+8:track_record+12].hex(),
            'expected_paired_stream_bytes':stream_bytes, 'first_samples':entries[:4],
            'last_sample':entries[-1],
            'duration_ms_range':[min(r['duration_ms'] for r in entries),max(r['duration_ms'] for r in entries)],
            'all_sample_descriptors_sha256':sha(json.dumps(entries,sort_keys=True,separators=(',',':')).encode())}


def inspect_stream_prefix(data, mpf):
    require(len(data)>=0x124, 'Music prefix too short')
    require(data[:4].hex()==mpf['track_checksum_hex'], 'MPF/MUS checksum-word mismatch')
    start=mpf['first_samples'][0]['stream_offset']
    require(data[start:start+4]==b'SCHl', 'First MPF descriptor does not point to SCHl')
    size=struct.unpack_from('<I',data,start+4)[0]
    require(size>=16 and start+size<=len(data), 'SCHl header exceeds prefix')
    require(data[start+8:start+12]==b'GSTR', 'Unobserved SCHl platform-header variant')
    cursor=start+16;patches={};ended=False
    while cursor<start+size:
        tag=data[cursor];cursor+=1
        if tag==0xff:
            ended=True
            break
        if tag in (0xfc,0xfd):
            continue
        require(cursor<start+size, 'Missing SCHl patch length')
        length=data[cursor];cursor+=1
        require(length<=4 and cursor+length<=start+size, 'Unobserved/truncated SCHl patch')
        require(tag not in patches, 'Duplicate SCHl patch')
        patches[tag]=int.from_bytes(data[cursor:cursor+length],'big');cursor+=length
    require(ended, 'Unterminated SCHl patch header')
    require({0x80,0x82,0x84,0x85}<=patches.keys(), 'Incomplete explicit stream properties')
    require(patches[0x80]==3 and 0x83 not in patches and 0xa0 not in patches,
            'Unobserved GSTR codec/version variant')
    samples,rate=patches[0x85],patches[0x84]
    require(rate>0 and round(samples*1000/rate)==mpf['first_samples'][0]['duration_ms'],
            'SCHl sample duration differs from MPF')
    blocks=[];cursor=start;truncated=None
    while cursor+8<=len(data):
        tag=data[cursor:cursor+4]
        require(tag in (b'SCHl',b'SCCl',b'SCDl',b'SCEl',b'SCLl'), 'Unrecognized EA audio block')
        size=struct.unpack_from('<I',data,cursor+4)[0]
        require(size>=8, 'Invalid EA block size')
        if cursor+size>len(data):
            truncated={'offset':cursor,'tag':tag.decode('ascii'),'declared_bytes':size,
                       'available_bytes':len(data)-cursor}
            break
        blocks.append({'offset':cursor,'tag':tag.decode('ascii'),'bytes':size})
        cursor+=size
        if tag==b'SCEl':break
    return {'bytes':len(data),'sha256':sha(data),'checksum_word_match':True,
            'first_stream_offset':start,'platform_header':'GSTR',
            'explicit_patches_hex':{f'{k:02x}':v for k,v in patches.items()},
            'sample_rate':rate,'channels':patches[0x82],'declared_samples':samples,
            'declared_duration_ms':samples*1000/rate,
            'codec_interpretation':'EA-XA R3: GSTR generic default with version patch 3; corroborate decoder separately',
            'complete_prefix_blocks':blocks,'truncated_next_block':truncated,
            'whole_first_stream_available':bool(blocks and blocks[-1]['tag']=='SCEl')}


def inspect_dol(path):
    from vehicle_dol import DolImage
    from vehicle_ppc_reference import DOL_SHA256
    data=path.read_bytes();require(sha(data)==DOL_SHA256,'Unexpected USA DOL')
    im=DolImage(data)
    refs=im.constant_xrefs([0x50464478])
    return {'sha256':sha(data), 'PFDx_constant_references':
            [{k:f'{v:08x}' if k!='register' else v for k,v in row.items()} for row in refs],
            'validated_reader_window':{'begin':'803755f8','end_exclusive':'80375744',
                                       'sha256':sha(im.read(0x803755f8,0x14c))},
            'interpretation':'80375604 compares PFDx; 8037560c..1c checks version high halfword 0501; 80375698..80375740 resolves offsets14..34 against base'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-directory',type=Path,required=True)
    p.add_argument('--stream-prefix',type=Path)
    p.add_argument('--dol',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--check-rejections',action='store_true')
    a=p.parse_args();report={'schema':1,'target':'USA GameCube NFS Most Wanted (2005)',
        'limits':['No audio decoded or runtime changed by this inspector',
                  'Sample descriptors and nodes are not song counts',
                  'No node/event/router interpreter recovered',
                  'Checksum is the matching header word; the checksum algorithm is not recovered'], 'maps':{}}
    for stem,stream_bytes in STREAM_BYTES.items():
        source=a.input_directory/('SOUND-PFDATA-'+stem+'.MPF');data=source.read_bytes()
        result=inspect_mpf(data,stream_bytes);report['maps'][stem]=result
        if a.check_rejections:
            variants=[data[:0x30],b'xxxx'+data[4:]]
            b=bytearray(data);struct.pack_into('>I',b,0x38,len(data)-1);variants.append(bytes(b))
            b=bytearray(data);struct.pack_into('>H',b,0x48,0xffff);variants.append(bytes(b))
            for variant in variants:
                try:inspect_mpf(variant,stream_bytes)
                except ValueError:pass
                else:raise AssertionError('Malformed MPF accepted')
    if a.stream_prefix:report['music_stream_prefix']=inspect_stream_prefix(a.stream_prefix.read_bytes(),report['maps']['MW_MUSIC'])
    if a.dol:report['original_reader_evidence']=inspect_dol(a.dol)
    if a.check_rejections:report['malformed_inputs_rejected']=4*len(STREAM_BYTES)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(a.output),'map_sample_counts':{k:v['streamed_sample_count'] for k,v in report['maps'].items()},
                      'malformed_inputs_rejected':report.get('malformed_inputs_rejected',0)},indent=2))


if __name__=='__main__':
    main()
