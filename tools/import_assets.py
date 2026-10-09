#!/usr/bin/env python3
"""Convert selected local Melty GLB art into ordinary, editable Minecraft blocks."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
from pathlib import Path

from PIL import Image
from nbt import structure

ROOT = Path(__file__).resolve().parents[1]
PALETTE = {
    'oak_planks': (162, 130, 79), 'spruce_planks': (114, 84, 48),
    'dark_oak_planks': (66, 43, 20), 'oak_log': (107, 85, 50),
    'green_terracotta': (76, 83, 42), 'green_concrete': (74, 91, 36),
    'moss_block': (90, 109, 45), 'gray_concrete': (54, 57, 61),
    'stone': (125, 125, 125), 'light_gray_concrete': (125, 125, 115),
}


def load_glb(path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', raw)
    if magic != b'glTF' or version != 2 or length != len(raw): raise ValueError('Not a GLB v2 file')
    position, document, binary = 12, None, None
    while position < length:
        size, kind = struct.unpack_from('<II', raw, position)
        chunk = raw[position + 8:position + 8 + size]
        if kind == 0x4e4f534a: document = json.loads(chunk)
        if kind == 0x004e4942: binary = chunk
        position += size + 8
    if document is None or binary is None: raise ValueError('Missing GLB chunks')
    return document, binary


def accessor(document, binary, index):
    item = document['accessors'][index]
    if 'sparse' in item: raise ValueError('Sparse accessors are not supported')
    view = document['bufferViews'][item['bufferView']]
    kind = {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[item['componentType']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[item['type']]
    fmt = '<' + kind * count
    stride = view.get('byteStride', struct.calcsize(fmt))
    offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    return [struct.unpack_from(fmt, binary, offset + i * stride) for i in range(item['count'])]


def node_transform(point, node):
    if 'matrix' in node:
        m = node['matrix']
        return tuple(sum(m[i + 4*j] * point[j] for j in range(3)) + m[i+12] for i in range(3))
    p = tuple(a*b for a, b in zip(point, node.get('scale', [1, 1, 1])))
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    vx, vy, vz = p
    tx, ty, tz = 2*(y*vz-z*vy), 2*(z*vx-x*vz), 2*(x*vy-y*vx)
    rotated = (vx+w*tx+y*tz-z*ty, vy+w*ty+z*tx-x*tz, vz+w*tz+x*ty-y*tx)
    return tuple(a+b for a, b in zip(rotated, node.get('translation', [0, 0, 0])))


def primitives(document, binary):
    result = []
    roots = document.get('scenes', [{'nodes': [i for i in range(len(document['nodes'])) if not any(i in n.get('children', []) for n in document['nodes'])]}])[document.get('scene', 0)]['nodes']
    def walk(index, parents):
        node = document['nodes'][index]
        transforms = [node] + parents
        if 'mesh' in node:
            for primitive in document['meshes'][node['mesh']]['primitives']:
                if primitive.get('mode', 4) != 4: continue
                positions = accessor(document, binary, primitive['attributes']['POSITION'])
                for transform in transforms: positions = [node_transform(p, transform) for p in positions]
                uvs = accessor(document, binary, primitive['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in primitive['attributes'] else [(0, 0)] * len(positions)
                indices = [v[0] for v in accessor(document, binary, primitive['indices'])] if 'indices' in primitive else list(range(len(positions)))
                material = document.get('materials', [{}])[primitive.get('material', 0)].get('pbrMetallicRoughness', {})
                image = None
                if 'baseColorTexture' in material:
                    image_info = document['images'][document['textures'][material['baseColorTexture']['index']]['source']]
                    if 'bufferView' not in image_info: raise ValueError('Only embedded GLB textures are supported')
                    view = document['bufferViews'][image_info['bufferView']]
                    offset = view.get('byteOffset', 0)
                    image = Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])).convert('RGBA')
                result.append((positions, uvs, indices, image, material.get('baseColorFactor', [1, 1, 1, 1])))
        for child in node.get('children', []): walk(child, transforms)
    for root in roots: walk(root, [])
    return result


def voxelize(path: Path, longest: int):
    if not 2 <= longest <= 32: raise ValueError('Asset size must be 2..32 blocks')
    document, binary = load_glb(path)
    parts = primitives(document, binary)
    points = [p for positions, *_ in parts for p in positions]
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    scale = (longest - .001) / max(b-a for a, b in zip(low, high))
    size = [max(1, math.ceil((b-a)*scale)) for a, b in zip(low, high)]
    blocks = {}
    palette = list(PALETTE)
    for positions, uvs, indices, image, factor in parts:
        vertices = [tuple((p[i]-low[i])*scale for i in range(3)) for p in positions]
        for offset in range(0, len(indices), 3):
            ids = indices[offset:offset+3]
            a, b, c = [vertices[i] for i in ids]
            samples = max(1, math.ceil(max(math.dist(a,b), math.dist(b,c), math.dist(c,a))*2))
            for row in range(samples+1):
                for column in range(samples+1-row):
                    weights = (1-(row+column)/samples, row/samples, column/samples)
                    point = tuple(sum(v[axis]*weight for v, weight in zip((a,b,c), weights)) for axis in range(3))
                    if image is not None:
                        uv = tuple(sum(uvs[i][axis]*weight for i, weight in zip(ids, weights)) for axis in range(2))
                        color = image.getpixel((int((uv[0] % 1)*image.width), int((uv[1] % 1)*image.height)))
                    else: color = (255, 255, 255, 255)
                    if color[3]*factor[3] < 100: continue
                    rgb = tuple(color[i]*factor[i] for i in range(3))
                    match = min(range(len(palette)), key=lambda i: sum((rgb[k]-PALETTE[palette[i]][k])**2 for k in range(3)))
                    cell = tuple(max(0, min(size[i]-1, math.floor(point[i]))) for i in range(3))
                    blocks[cell] = match
    if not blocks: raise ValueError('Asset conversion produced no blocks')
    return structure(size, blocks, palette), {'size': size, 'blocks': len(blocks), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT.parent/'meltyblndr/holy-order/assets/waw/models')
    args = parser.parse_args()
    output = ROOT/'local-assets/structures'
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for name, longest in [('crate', 3), ('pine', 12)]:
        path = args.source/(name+'.glb')
        data, record = voxelize(path, longest)
        (output/(name+'.nbt')).write_bytes(data)
        records.append({'id': name, 'source': str(path.resolve()), **record})
        print(f'{name}: {record["blocks"]} blocks, {record["size"]}')
    (ROOT/'local-assets/provenance.json').write_text(json.dumps({'source_project': 'meltyblndr/Holy Order', 'upstream_art': 'Call of Duty: World at War (Activision / Treyarch)', 'conversion': 'Local GLB geometry and embedded texture colors sampled into vanilla Minecraft blocks. Original game rights remain with their holders.', 'assets': records}, indent=2)+'\n')


if __name__ == '__main__': main()
