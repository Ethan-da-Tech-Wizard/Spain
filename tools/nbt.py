# ==============================================================================
# Program: nbt.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Small big-endian NBT reader/writer for Minecraft structure files and level.dat.
#          Writes gzip output with a fixed timestamp so identical input gives identical bytes.
# ==============================================================================

"""Small big-endian NBT codec for Minecraft structures and verification reports.

Architecture & Protocol Notes:
- Follows the Minecraft NBT binary specification with big-endian ('>') byte ordering.
- NBT Tag ID Type Map:
    0 = TAG_End (terminator for Compound tags)
    1 = TAG_Byte (8-bit signed integer)
    2 = TAG_Short (16-bit signed integer)
    3 = TAG_Int (32-bit signed integer)
    4 = TAG_Long (64-bit signed integer)
    5 = TAG_Float (32-bit IEEE 754 float)
    6 = TAG_Double (64-bit IEEE 754 double)
    7 = TAG_Byte_Array (length-prefixed byte buffer)
    8 = TAG_String (UTF-8 bytes prefixed by unsigned 16-bit length)
    9 = TAG_List (typed list: subtype byte + 32-bit count + payload sequence)
   10 = TAG_Compound (dictionary of named tags, terminated by TAG_End null byte)
   11 = TAG_Int_Array (length-prefixed array of 32-bit signed ints)
   12 = TAG_Long_Array (length-prefixed array of 64-bit signed ints)
- Supports optional gzip decompression/compression with deterministic timestamping (`mtime=0`).
"""
from __future__ import annotations

import gzip
import io
import struct


def string(value: str) -> bytes:
    """Encode string value as UTF-8 prefixed by 16-bit unsigned big-endian length."""
    data = value.encode('utf-8')
    return struct.pack('>H', len(data)) + data


def payload(kind: int, value) -> bytes:
    """Serialize NBT tag payload based on numeric type tag ID."""
    # Primitive scalar numeric types mapped directly to big-endian struct format specifiers
    formats = {1: '>b', 2: '>h', 3: '>i', 4: '>q', 5: '>f', 6: '>d'}
    if kind in formats: return struct.pack(formats[kind], value)
    # TAG_Byte_Array: 32-bit length followed by raw byte payload
    if kind == 7: return struct.pack('>i', len(value)) + bytes(value)
    # TAG_String: 16-bit length-prefixed UTF-8
    if kind == 8: return string(value)
    # TAG_List: 1 byte for element type ID, 32-bit integer element count, then serialized items
    if kind == 9:
        subtype, values = value
        return bytes([subtype]) + struct.pack('>i', len(values)) + b''.join(payload(subtype, v) for v in values)
    # TAG_Compound: repeated sequence of [type ID (1 byte), name string, payload], closed with null byte (0x00)
    if kind == 10:
        return b''.join(bytes([k]) + string(name) + payload(k, val) for name, (k, val) in value.items()) + b'\0'
    # TAG_Int_Array / TAG_Long_Array: 32-bit element count followed by packed 32-bit/64-bit signed integers
    if kind in (11, 12): return struct.pack('>i', len(value)) + b''.join(struct.pack('>i' if kind == 11 else '>q', v) for v in value)
    raise ValueError(f'Unsupported NBT write type {kind}')


def structure(size, blocks, palette, data_version=5023) -> bytes:
    """Construct and gzip-compress a canonical Minecraft structure schematic file."""
    # Build standard Minecraft structure compound layout: DataVersion, size, palette, blocks, entities
    root = {
        'DataVersion': (3, data_version), 'size': (9, (3, size)),
        'palette': (9, (10, [{'id': (8, 'minecraft:' + block)} for block in palette])),
        'blocks': (9, (10, [{'pos': (9, (3, list(pos))), 'state': (3, state)} for pos, state in sorted(blocks.items())])),
        'entities': (9, (10, [])),
    }
    # Compress with fixed mtime=0 to guarantee reproducible, bit-for-bit identical binary output
    return gzip.compress(b'\x0a\x00\x00' + payload(10, root), mtime=0)


def read(data: bytes, typed: bool = False):
    """Parse raw or gzip-compressed NBT binary buffer into nested Python structures."""
    # Detect standard GZIP file signature header bytes (0x1F, 0x8B)
    if data[:2] == b'\x1f\x8b': data = gzip.decompress(data)
    stream = io.BytesIO(data)
    
    # Internal helpers for sequential stream unpacking
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
        
    # Read root tag type (typically TAG_Compound = 0x0A) and root name
    kind = get('>B')
    text()
    return decode(kind)
