"""Add a box-filtered mip chain to uncompressed BGRA DDS files.

Mod textures written by Pillow (or most ad-hoc scripts) have only one mip level.
The GPU then always samples level 0, so fine cloth weave/embroidery aliases into
visible noise and shimmers at distance, while the native game textures are
mipped. This helper rewrites the DDS in place with a full mip chain. Normal maps
are re-normalised per level so their XY stay a valid tangent-space direction.

Usage:
    python dds_mips.py <Textures folder>

Only uncompressed legacy DDS (DDS header without a DX10 extension) is supported;
BC-compressed textures do not need this.
"""
import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image

HEADER_SIZE = 128


def read_dds(path):
    raw = Path(path).read_bytes()
    if raw[:4] != b'DDS ':
        raise ValueError('Not a DDS file: %s' % path)
    header = bytearray(raw[:HEADER_SIZE])
    height, width = struct.unpack('<II', raw[12:20])
    pixel = np.frombuffer(raw[HEADER_SIZE:HEADER_SIZE + width * height * 4],
                          dtype=np.uint8).reshape(height, width, 4).copy()
    return header, pixel


def write_dds(path, header, levels):
    header = bytearray(header)
    flags = struct.unpack('<I', header[8:12])[0] | 0x20000  # DDSD_MIPMAPCOUNT
    struct.pack_into('<I', header, 8, flags)
    struct.pack_into('<I', header, 28, len(levels))
    caps = struct.unpack('<I', header[108:112])[0]
    caps |= 0x8 | 0x400000  # DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
    struct.pack_into('<I', header, 108, caps)
    Path(path).write_bytes(bytes(header) + b''.join(level.tobytes() for level in levels))


def downsample(level, is_normal):
    h, w = level.shape[:2]
    pad_h, pad_w = h % 2, w % 2
    if pad_h or pad_w:
        level = np.pad(level, ((0, pad_h), (0, pad_w), (0, 0)), mode='edge')
    small = level.reshape(level.shape[0] // 2, 2, level.shape[1] // 2, 2, 4).astype('f4').mean(axis=(1, 3))
    if is_normal:
        xy = small[..., :2] / 127.5 - 1.0
        length = np.sqrt((xy ** 2).sum(axis=-1, keepdims=True))
        xy *= np.where(length > 1.0, 1.0 / np.maximum(length, 1e-6), 1.0)
        small[..., :2] = xy * 127.5 + 127.5
    return np.clip(np.rint(small), 0, 255).astype(np.uint8)


def add_mipmaps(path, is_normal=False):
    header, level = read_dds(path)
    if level.shape[0] != level.shape[1]:
        raise ValueError('Expected square texture: %s' % path)
    levels = [level]
    while level.shape[0] > 1:
        level = downsample(level, is_normal)
        levels.append(level)
    write_dds(path, header, levels)
    return len(levels)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('textures', type=Path, help='folder containing *.dds')
    args = parser.parse_args()
    for path in sorted(args.textures.glob('*.dds')):
        _, level = read_dds(path)
        if level.shape[0] <= 8:
            continue
        count = add_mipmaps(path, is_normal='normal' in path.stem.lower())
        print(path.name, level.shape[0], 'mips', count)


if __name__ == '__main__':
    main()
