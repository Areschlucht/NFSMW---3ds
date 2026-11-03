"""Observed Rockport instance records; all placement comes from the game data."""
import math
import struct
from pathlib import Path
from decode_world import decode
from nfs_rockport import chunks


def complete_prefix(data):
    """Return only complete top-level chunks from an explicitly supplied prefix."""
    offset = 0
    while offset + 8 <= len(data):
        _, size = struct.unpack_from('<II', data, offset)
        end = offset + 8 + size
        if end > len(data):
            break
        offset = end
    return data[:offset]


def catalog_files(paths):
    catalog, rejected = {}, []
    for path in paths:
        models, bad = decode(complete_prefix(Path(path).read_bytes()), lambda name: True)
        rejected.extend(dict(source=Path(path).name, **r) for r in bad)
        for model in models:
            old = catalog.get(model['hash'])
            if old and any(old[k] != model[k] for k in ('positions', 'texcoords', 'colors', 'faces')):
                raise ValueError(f'Conflicting geometry for {model["hash"]}')
            catalog.setdefault(model['hash'], model)
    return catalog, rejected


def transform_points(points, matrix, translation):
    if len(matrix) != 9 or len(translation) != 3:
        raise ValueError('Invalid instance transform shape')
    if not all(math.isfinite(v) for v in (*matrix, *translation)):
        raise ValueError('Nonfinite instance transform')
    # Packed matrices act on row vectors. Header modeling transforms are not
    # applied again. Stored world bounds independently validate this convention.
    return [tuple(translation[a] + sum(p[c] * matrix[c * 3 + a] for c in range(3))
                  for a in range(3)) for p in points]


def read_instances(data):
    result = []
    for kind, start, end in chunks(data):
        if kind != 0x80034100:
            continue
        parts = {k: (start + a, start + b) for k, a, b in chunks(data[start:end])}
        if 0x34102 not in parts:
            continue
        if 0x34103 not in parts:
            raise ValueError('Object table lacks instance records')
        a, b = parts[0x34102]
        if (b - a) % 72:
            raise ValueError('Malformed 72-byte object table')
        objects = []
        for p in range(a, b, 72):
            name = data[p:p + 28].split(b'\0')[0].decode('ascii')
            keys = [f'{key:08x}' for key in struct.unpack_from('<3I', data, p + 28) if key]
            objects.append((name, keys))
        a, b = parts[0x34103]
        a = (a + 15) & ~15
        if (b - a) % 64:
            raise ValueError('Malformed aligned 64-byte instance table')
        for p in range(a, b, 64):
            index = struct.unpack_from('<H', data, p + 62)[0]
            if index >= len(objects):
                raise ValueError('Instance references invalid object index')
            name, keys = objects[index]
            bounds = struct.unpack_from('<6f', data, p)
            if not all(math.isfinite(v) for v in bounds) or any(bounds[i] > bounds[i + 3] for i in range(3)):
                raise ValueError('Invalid stored instance bounds')
            result.append(dict(name=name, keys=keys, bounds=bounds, offset=p,
                               translation=struct.unpack_from('<3f', data, p + 32),
                               matrix=[v / 8192 for v in struct.unpack_from('<9h', data, p + 44)]))
    return result


def place_instance(instance, catalog):
    for key in instance['keys']:
        if key not in catalog:
            continue
        model = catalog[key]
        points = transform_points(model['positions'], instance['matrix'], instance['translation'])
        low = [min(p[a] for p in points) for a in range(3)]
        high = [max(p[a] for p in points) for a in range(3)]
        error = max(abs(a - b) for a, b in zip(low + high, instance['bounds']))
        if error > .15:
            continue
        return dict(model, positions=points, instance_offset=instance['offset'],
                    instance_name=instance['name'], instance_bounds_error=error)
    return None
