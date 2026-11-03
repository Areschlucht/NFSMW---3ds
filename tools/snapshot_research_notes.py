#!/usr/bin/env python3
"""Snapshot small research notes/proofs for Git; game assets stay in private backups."""
from pathlib import Path
import hashlib,json
SOURCE=Path('/workspace/port-research')
DEST=Path(__file__).resolve().parents[1]/'research'
EXTENSIONS={'.md','.json','.csv','.py','.c','.h','.inc','.ps1','.sh','.txt'}
SKIP={'emulator-state','state','renderer-probe-baseline','scene-native','reproducibility','references'}

def main():
    records=[];omitted=[]
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file() or path.is_symlink():continue
        relative=path.relative_to(SOURCE)
        if any(p in SKIP or p.endswith('-project') for p in relative.parts):continue
        if path.suffix.lower() not in EXTENSIONS:continue
        before=path.stat()
        if before.st_size>2*1024*1024:
            omitted.append({'path':str(relative),'reason':'Large generated catalogue retained in private research backup'});continue
        raw=path.read_bytes();after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            omitted.append({'path':str(relative),'reason':'Changing during snapshot; retry at next checkpoint'});continue
        try:
            raw.decode('utf-8-sig')
            if path.suffix.lower()=='.json':json.loads(raw.decode('utf-8-sig'))
        except (ValueError,UnicodeError):
            omitted.append({'path':str(relative),'reason':'Not a complete UTF-8 text document'});continue
        target=DEST/'notes'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        records.append({'path':str(relative),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    DEST.mkdir(exist_ok=True)
    (DEST/'INDEX.json').write_text(json.dumps({'scope':'Small authored research notes and comparison reports; not game assets','files':records,'omitted':omitted},indent=2)+'\n')
    (DEST/'README.md').write_text('''# Research checkpoint\n\nThese are snapshots of authored notes, source-data provenance and comparison\nreports. They record component-level recovery and do not establish a completed\n1:1 game or hardware performance. Current development sources live in the\nnormal include/source/tools/tests directories.\n\nOriginal game inputs, converted meshes/textures, executable builds, large\ngenerated catalogues, external reference packages and emulator/SDK caches are\nnot copied here. Keep the private full-directory ZIP backups and original\ninputs; use the committed tools to reproduce asset-dependent analysis.\n\nINDEX.json lists every copied document, its SHA-256 and omitted large/changing\ndocuments. Refresh with `python3 tools/snapshot_research_notes.py` from the\nrestored workspace at a stable checkpoint. Historical notes can contain earlier\ninterpretations; later verified corrections and current source APIs take\nprecedence.\n''')
    print(f'Snapshotted {len(records)} research documents ({sum(r["bytes"] for r in records)} bytes); {len(omitted)} explicitly omitted.')
if __name__=='__main__':main()
