#!/usr/bin/env python3
"""Package an existing build with the exact user-supplied test asset."""
import argparse
import hashlib
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('asset', type=Path)
args = parser.parse_args()
project = Path(__file__).resolve().parent.parent
asset = args.asset.read_bytes()
expected = 'd95baa36b180c0dba10debff4f8de2dab5f3aa96faa606485478928a113a8ff5'
if hashlib.sha256(asset).hexdigest() != expected:
    raise SystemExit('Asset does not match the inspected sample; refusing to package')
binary = project/'nfsmw-brake-viewer.3dsx'
if binary.read_bytes()[:4] != b'3DSX':
    raise SystemExit('Missing or invalid 3DSX build')
out = project/'dist'
out.mkdir(exist_ok=True)
destination = out/'nfsmw-brake-viewer-v0.3.zip'
prefix = '3ds/nfsmw-brake-viewer/'
with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    archive.write(binary, prefix+binary.name)
    archive.write(project/'nfsmw-brake-viewer.smdh', prefix+'nfsmw-brake-viewer.smdh')
    archive.writestr(prefix+'brakes-geometry.bin', asset)
    archive.write(project/'README.md', prefix+'README.md')
with zipfile.ZipFile(destination) as archive:
    if archive.testzip() is not None:
        raise SystemExit('ZIP integrity check failed')
print(destination)
print('ZIP SHA-256:', hashlib.sha256(destination.read_bytes()).hexdigest())
