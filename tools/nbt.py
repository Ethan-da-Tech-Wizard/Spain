"""Small big-endian NBT codec for Minecraft structures and verification reports."""
from __future__ import annotations

import gzip
import io
import struct


def string(value):
    data = value.encode('utf-8')
    return struct.pack('>H', len(data)) + data


def payload(kind, value):
    formats = {1: '>b', 2: '>h', 3: '>i', 4: '>q', 5: '>f', 6: '>d'}
    if kind in formats: return struct.pack(formats[kind], value)
    if kind == 7: return struct.pack('>i', len(value)) + bytes(value)
    if kind == 8: return string(value)
    if kind == 9:
        subtype, values = value
        return bytes([subtype]) + struct.pack('>i', len(values)) + b''.join(payload(subtype, v) for v in values)
    if kind == 10:
        return b''.join(bytes([k]) + string(name) + payload(k, val) for name, (k, val) in value.items()) + b'\0'
    if kind in (11, 12): return struct.pack('>i', len(value)) + b''.join(struct.pack('>i' if kind == 11 else '>q', v) for v in value)
    raise ValueError(f'Unsupported NBT write type {kind}')


def structure(size, blocks, palette, data_version=5023):
    root = {
        'DataVersion': (3, data_version), 'size': (9, (3, size)),
        'palette': (9, (10, [{'id': (8, 'minecraft:' + block)} for block in palette])),
        'blocks': (9, (10, [{'pos': (9, (3, list(pos))), 'state': (3, state)} for pos, state in sorted(blocks.items())])),
        'entities': (9, (10, [])),
    }
    return gzip.compress(b'\x0a\x00\x00' + payload(10, root), mtime=0)


def read(data, typed=False):
    if data[:2] == b'\x1f\x8b': data = gzip.decompress(data)
    stream = io.BytesIO(data)
    def get(fmt):
        return struct.unpack(fmt, stream.read(struct.calcsize(fmt)))[0]
    def text():
        return stream.read(get('>H')).decode('utf-8')
    def decode(kind):
        formats = {1: '>b', 2: '>h', 3: '>i', 4: '>q', 5: '>f', 6: '>d'}
        if kind in formats: return get(formats[kind])
        if kind == 7: return list(stream.read(get('>i')))
        if kind == 8: return text()
        if kind == 9:
            subtype, count = get('>B'), get('>i')
            values = [decode(subtype) for _ in range(count)]
            return (subtype, values) if typed else values
        if kind == 10:
            result = {}
            while (subtype := get('>B')) != 0:
                name = text()
                value = decode(subtype)
                result[name] = (subtype, value) if typed else value
            return result
        if kind in (11, 12): return [get('>i' if kind == 11 else '>q') for _ in range(get('>i'))]
        raise ValueError(f'Unsupported NBT read type {kind}')
    kind = get('>B')
    text()
    return decode(kind)
