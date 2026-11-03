#!/usr/bin/env python3
"""Read observed L2RA streaming records and CARP road-network tables.

The graph is original navigation data, not rendered road surfaces or collision
geometry. Unknown record fields remain uninterpreted. No game code is executed.
"""
import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path


def chunks(data):
    offset = 0
    while offset < len(data):
        if len(data) - offset < 8:
            raise ValueError('Truncated chunk header')
        kind, size = struct.unpack_from('<II', data, offset)
        end = offset + 8 + size
        if end > len(data):
            raise ValueError('Chunk exceeds file')
        yield kind, offset + 8, end
        offset = end


def streaming_sections(payload, stream_size):
    if not payload or len(payload) % 92:
        raise ValueError('Expected complete 92-byte streaming records')
    result = []
    identifiers = set()
    previous_end = 0
    for row in struct.iter_unpack('<23I', payload):
        identifier, offset, size = row[2], row[5], row[6]
        if row[4] != 1 or row[6] != row[7] or row[6] != row[8]:
            raise ValueError('Unsupported streaming record variant')
        if identifier in identifiers:
            raise ValueError('Duplicate streaming section ID')
        if offset % 2048 or offset < previous_end or offset > stream_size or size > stream_size - offset:
            raise ValueError('Invalid streaming section range')
        identifiers.add(identifier)
        result.append(dict(id=identifier, offset=offset, bytes=size))
        previous_end = offset + size
    return result


def road_network(payload):
    # The outer chunk's payload begins with alignment padding to 16 bytes.
    # The supplied standalone L2RA file has exactly eight padding bytes here.
    if payload[:8] != b'\x11' * 8:
        raise ValueError('Unsupported CARP alignment padding')
    data = payload[8:]
    if len(data) < 192 or data[:16] != b'CARPX\0\0\3' + struct.pack('>II', 0, 1):
        raise ValueError('Unsupported CARP header/version')
    expected = ((b'CGcn', 4), (b'CGrd', 5), (b'RNhd', 7),
                (b'RNnd', 8), (b'RNpf', 9), (b'RNrd', 10), (b'RNsg', 11))
    tables = {}
    ranges = []
    for tag, index in expected:
        at = index * 16
        actual, packed_size, count, relative = struct.unpack_from('>4sIII', data, at)
        if actual != tag or packed_size >> 24 != 0x40:
            raise ValueError(f'Unexpected CARP leaf {tag!r}')
        size = packed_size & 0xffffff
        start = at + relative  # Offsets are relative to each table descriptor.
        end = start + size
        if start < 192 or start > len(data) or end > len(data):
            raise ValueError('CARP table exceeds payload')
        ranges.append((start, end))
        tables[tag.decode()] = dict(offset=start, bytes=size, count=count)
    ordered = sorted(ranges)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('Overlapping CARP tables')
    nt, st = tables['RNnd'], tables['RNsg']
    if not nt['count'] or nt['count'] > 65535 or st['count'] > 65535:
        raise ValueError('Invalid road graph counts')
    if nt['bytes'] != nt['count'] * 32 or st['bytes'] != st['count'] * 22:
        raise ValueError('Unsupported road graph record sizes')
    nodes = []
    adjacency = []
    for i in range(nt['count']):
        at = nt['offset'] + i * 32
        position = struct.unpack_from('>3f', data, at)
        identifier = struct.unpack_from('>H', data, at + 12)[0]
        degree = data[at + 16]
        if identifier != i or not 1 <= degree <= 7:
            raise ValueError('Invalid road node ID/degree')
        if not all(math.isfinite(v) and abs(v) < 1e7 for v in position):
            raise ValueError('Invalid road node position')
        refs = struct.unpack_from('>7H', data, at + 18)[:degree]
        if len(set(refs)) != len(refs):
            raise ValueError('Duplicate node adjacency')
        nodes.append(list(position))
        adjacency.append(refs)
    segments = []
    for i in range(st['count']):
        at = st['offset'] + i * 22
        a, b = struct.unpack_from('>2H', data, at)
        identifier = struct.unpack_from('>H', data, at + 8)[0]
        if identifier != i or a >= len(nodes) or b >= len(nodes) or a == b:
            raise ValueError('Invalid road segment ID/endpoints')
        segments.append([a, b])
    references = Counter()
    for node, refs in enumerate(adjacency):
        for segment in refs:
            if segment >= len(segments) or node not in segments[segment]:
                raise ValueError('Road adjacency disagrees with segment endpoints')
            references[segment] += 1
    if any(references[i] != 2 for i in range(len(segments))):
        raise ValueError('Each segment must be referenced by both endpoint nodes')
    return dict(nodes=nodes, segments=segments, tables=tables,
                bounds=[[min(p[a] for p in nodes), max(p[a] for p in nodes)] for a in range(3)],
                adjacency_references=sum(references.values()))


def decode(data, stream_size=109279744):
    parts = {}
    for kind, start, end in chunks(data):
        if kind not in (0x34110, 0x3b800):
            continue
        if kind in parts:
            raise ValueError('Duplicate required L2RA chunk')
        parts[kind] = data[start:end]
    if set(parts) != {0x34110, 0x3b800}:
        raise ValueError('Missing L2RA streaming/road-network chunks')
    return dict(source_sha256=hashlib.sha256(data).hexdigest(),
                limitations='Navigation graph only; not road mesh, collision, lane widths or original driving physics.',
                sections=streaming_sections(parts[0x34110], stream_size),
                road_network=road_network(parts[0x3b800]))


def plot_graph(network, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    nodes = network['nodes']
    edges = network['segments']
    lines = [[(nodes[a][0], nodes[a][2]), (nodes[b][0], nodes[b][2])] for a, b in edges]
    elevation = [(nodes[a][1] + nodes[b][1]) / 2 for a, b in edges]
    fig, ax = plt.subplots(figsize=(9, 10), facecolor='#11151b')
    ax.set_facecolor('#11151b')
    collection = LineCollection(lines, array=elevation, cmap='viridis', linewidths=.65)
    ax.add_collection(collection)
    ax.autoscale()
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Rockport — original navigation graph', color='white', fontsize=16)
    ax.text(.5, -.025, f'{len(nodes):,} nodes · {len(edges):,} connections\nExtracted from L2RA.BUN; this is not the rendered road mesh.',
            transform=ax.transAxes, ha='center', color='#cccccc', fontsize=10)
    fig.savefig(output, dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plot', type=Path, help='Optional graph image (requires matplotlib)')
    args = parser.parse_args()
    try:
        report = decode(args.bundle.read_bytes())
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        if args.plot:
            plot_graph(report['road_network'], args.plot)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(f"Recovered {len(report['sections'])} stream sections, "
          f"{len(report['road_network']['nodes'])} nodes, "
          f"{len(report['road_network']['segments'])} connections")
