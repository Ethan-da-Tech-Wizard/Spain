#!/usr/bin/env python3
# ==============================================================================
# Program: import_assets.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Converts local .glb 3D models (crate and pine) into vanilla Minecraft block
#          structures (.nbt): reads the glTF mesh, samples every triangle into a voxel grid
#          and picks the nearest block colour from a small palette.
# ==============================================================================

"""Convert selected local Melty GLB art into ordinary, editable Minecraft blocks."""
from __future__ import annotations

# Fit in the repo: optional local-art importer. It is run by scripts/update.sh only when the owner has
# a sibling project (meltyblndr/holy-order) with .glb models, and writes local-assets/structures/crate.nbt
# and pine.nbt plus local-assets/provenance.json. build_pack.py then places these structures in every
# generated city. The files are kept local: the models come from a third-party game, so only the
# converter is published, not its output.
#
# How the conversion works (see voxelize): read the GLB (binary glTF 2.0), apply each node's
# transform, scale the whole model so its longest side equals the requested number of blocks, then
# sample points over every triangle at half-block spacing and snap each point to a block cell whose colour
# is the nearest entry in PALETTE. Texture colours come from the model's embedded base-colour image.
#
# Input : --source folder (default ../meltyblndr/holy-order/assets/waw/models) containing crate.glb and pine.glb.
# Output: .nbt structure files readable by Minecraft's `place template`.
# Limits: triangle meshes only; embedded textures only; no sparse accessors; models of 2..32 blocks
# (32 keeps imported structures small and quick to place). Only the first UV set is used.
# Needs : Pillow (PIL) for texture decoding.
import argparse
import hashlib
import io
import json
import math
import struct
from pathlib import Path

from PIL import Image
from nbt import structure

# Repository root.
ROOT = Path(__file__).resolve().parents[1]

# Block name -> typical average RGB colour. Only earthy, low-saturation blocks are used on purpose, so a
# converted wooden crate or pine tree looks natural in a Minecraft landscape. Colours are approximate values
# of the block textures, tuned by eye; they are not read from the game.
PALETTE = {
    'oak_planks': (162, 130, 79), 'spruce_planks': (114, 84, 48),
    'dark_oak_planks': (66, 43, 20), 'oak_log': (107, 85, 50),
    'green_terracotta': (76, 83, 42), 'green_concrete': (74, 91, 36),
    'moss_block': (90, 109, 45), 'gray_concrete': (54, 57, 61),
    'stone': (125, 125, 125), 'light_gray_concrete': (125, 125, 115),
}


def load_glb(path):
    """Parse a binary glTF (.glb) file and return (json_document, binary_buffer).

    A GLB is a 12-byte header (magic 'glTF', version 2, total length) followed by chunks of
    [length, type, data]. Type 0x4E4F534A is the JSON scene description, 0x004E4942 the binary buffer that holds
    vertex data. The length check rejects truncated downloads (covered by a unit test).

    Raises:
        ValueError: if the magic/version/length is wrong or either chunk is missing.
    """
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
    """Read one glTF accessor (a typed view onto the buffer) and return a list of tuples, one per element.

    componentType codes: 5121 unsigned byte, 5123 unsigned short, 5125 unsigned int, 5126 float. `type` gives
    the tuple width (SCALAR 1, VEC2 2, VEC3 3, VEC4 4). Elements are `byteStride` apart when the buffer is
    interleaved (position and normal stored together), otherwise tightly packed. Offsets add the buffer-view
    and accessor offsets. Sparse accessors are not supported.
    """
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
    """Apply one glTF node's transform to a 3D point and return the new point.

    A node holds either a column-major 4x4 `matrix`, or separate scale, rotation (unit quaternion x, y, z, w)
    and translation applied in that order. The quaternion rotation uses the formula v' = v + w*t + q x t with
    t = 2 (q x v), which avoids building a rotation matrix.
    """
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
    """Collect every triangle mesh in the default scene as (positions, uvs, indices, image, color_factor).

    Walks the node tree from the scene roots, applying each ancestor's transform to the vertex positions.
    Only triangle lists (primitive mode 4) are used; other modes are skipped. The base colour texture is
    decoded to an RGBA image, and only textures embedded in the file are supported.
    """
    result = []
    roots = document.get('scenes', [{'nodes': [i for i in range(len(document['nodes'])) if not any(i in n.get('children', []) for n in document['nodes'])]}])[document.get('scene', 0)]['nodes']

    # Depth-first traversal. `transforms` is this node followed by its ancestors, so the point is transformed
    # by the node first and its parents afterwards, which is the order glTF defines for a hierarchy.
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
    """Convert the model at `path` into a Minecraft structure; return (nbt_bytes, info).

    Args:
        path: a .glb file.
        longest: size in blocks of the model's longest axis (2 to 32).

    Returns:
        The gzip-compressed .nbt bytes and a dict with size, number of blocks and the file's SHA-256 (recorded in provenance.json).

    Raises:
        ValueError: for an out-of-range size, an invalid file or a model that yields no blocks.
    """
    if not 2 <= longest <= 32: raise ValueError('Asset size must be 2..32 blocks')
    document, binary = load_glb(path)
    parts = primitives(document, binary)
    points = [p for positions, *_ in parts for p in positions]
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]

    # Uniform scale that maps the longest side to just under `longest`, so floor() never produces an index equal to `longest` (off the edge of the grid).
    scale = (longest - .001) / max(b-a for a, b in zip(low, high))
    size = [max(1, math.ceil((b-a)*scale)) for a, b in zip(low, high)]
    blocks = {}
    palette = list(PALETTE)
    for positions, uvs, indices, image, factor in parts:
        vertices = [tuple((p[i]-low[i])*scale for i in range(3)) for p in positions]
        for offset in range(0, len(indices), 3):
            ids = indices[offset:offset+3]
            a, b, c = [vertices[i] for i in ids]

            # Sampling density: two samples per block along the triangle's longest edge, so no gaps appear in the shell of the voxel model.
            samples = max(1, math.ceil(max(math.dist(a,b), math.dist(b,c), math.dist(c,a))*2))
            for row in range(samples+1):
                for column in range(samples+1-row):
                    # Barycentric coordinates of a grid point inside the triangle (weights sum to 1), used to interpolate both position and texture coordinate.
                    weights = (1-(row+column)/samples, row/samples, column/samples)
                    point = tuple(sum(v[axis]*weight for v, weight in zip((a,b,c), weights)) for axis in range(3))
                    if image is not None:
                        uv = tuple(sum(uvs[i][axis]*weight for i, weight in zip(ids, weights)) for axis in range(2))

                        # Texture lookup with `% 1` so UVs outside 0..1 wrap (repeat), as glTF samplers do by default.
                        color = image.getpixel((int((uv[0] % 1)*image.width), int((uv[1] % 1)*image.height)))
                    else: color = (255, 255, 255, 255)

                    # Skip mostly transparent texels (alpha below 100 of 255) so leaf cut-outs and holes stay empty.
                    if color[3]*factor[3] < 100: continue
                    rgb = tuple(color[i]*factor[i] for i in range(3))

                    # Nearest palette colour by squared distance in RGB. Simple and fast; it does not match perceptual colour distance.
                    match = min(range(len(palette)), key=lambda i: sum((rgb[k]-PALETTE[palette[i]][k])**2 for k in range(3)))
                    cell = tuple(max(0, min(size[i]-1, math.floor(point[i]))) for i in range(3))

                    # One block per cell; later samples overwrite earlier ones, which only matters where triangles overlap.
                    blocks[cell] = match
    if not blocks: raise ValueError('Asset conversion produced no blocks')
    return structure(size, blocks, palette), {'size': size, 'blocks': len(blocks), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    """Convert the two fixed assets (a 3-block crate and a 12-block pine) and write the provenance record.

    provenance.json states where the art came from and that rights stay with the original owner, so anyone who
    sees the local files knows they are not original work.
    """
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


# Entry point.
if __name__ == '__main__': main()
