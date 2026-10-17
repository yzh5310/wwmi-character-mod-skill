"""Determine the game's texture V convention from a WWMI capture pair.

Why: an atlas baked in image-space ("image row 0 = V1") looks correct in an
offline renderer but is sampled mirrored by Direct3D ("row 0 = V0"). That was
the root cause of "red/black fragment" clothing in the Hiyuki case.

This script takes one captured component (Component N.fmt/.vb/.ib from a WWMI
FrameAnalysis extraction), its captured diffuse DDS, and renders the mesh under
both V conventions. The convention that shows coherent trim/panel layout is the
one the game uses. It is evidence for how the *captured* pair behaves; it does
not by itself prove a modded mesh's UVs match.

Usage:
    python probe_texture_v_convention.py --capture <folder> --component 4 \
        --diffuse "<folder>/Components-4 t=....dds" --output out.png
"""
import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def read_component(folder, cid):
    folder = Path(folder)
    fmt = (folder / ('Component %d.fmt' % cid)).read_text(encoding='utf-8', errors='replace')
    stride = int(re.search(r'^stride: (\d+)', fmt).group(1))
    raw = (folder / ('Component %d.vb' % cid)).read_bytes()
    data = np.frombuffer(raw, dtype=np.uint8).reshape(-1, stride)
    fields = {}
    for block in re.split(r'element\[\d+\]:', fmt)[1:]:
        def field(key):
            return re.search(key + r': (\S+)', block).group(1)
        sem, index, offset = field('SemanticName'), int(field('SemanticIndex')), int(field('AlignedByteOffset'))
        fields[(sem, index)] = {'offset': offset, 'format': field('Format')}
    offsets = sorted({info['offset'] for info in fields.values()} | {stride})
    for key, info in fields.items():
        start = info['offset']
        end = offsets[offsets.index(start) + 1]
        payload = np.ascontiguousarray(data[:, start:end])
        bits = re.search(r'R(\d+)', info['format']).group(1)
        suffix = info['format'].split('_')[-1]
        dtype = {'FLOAT': '<f', 'SNORM': '<i', 'SINT': '<i'}.get(suffix, '<u') + str(int(bits) // 8)
        info['data'] = payload.view(dtype).reshape(len(data), -1)
    indices = np.fromfile(folder / ('Component %d.ib' % cid), dtype='<u2').astype(np.uint32)
    return fields, indices


def sample_render(vertices_yup, faces, uv, texture, angle, flip_v, width=460, height=760):
    """Render with the texture sampled by one V convention.

    flip_v=True  -> image row 0 is V0 (Direct3D convention)
    flip_v=False -> image row 0 is V1 (image/OpenGL convention)
    """
    vertices = vertices_yup - vertices_yup.mean(axis=0)
    c, s = np.cos(angle), np.sin(angle)
    rotated = vertices @ np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
    scale = min((width - 30) / np.ptp(rotated[:, 0]), (height - 60) / np.ptp(rotated[:, 1]))
    points = np.column_stack((width / 2 + rotated[:, 0] * scale,
                              height / 2 - rotated[:, 1] * scale, rotated[:, 2]))
    rgb = np.full((height, width, 3), [233, 236, 240], dtype=np.float32)
    depth = np.full((height, width), -np.inf)
    triangles = rotated[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
    light = np.array([-0.4, 0.6, 0.7]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(normals @ light)
    tex = np.asarray(texture.convert('RGB'))
    for idx, ids in enumerate(faces):
        a, b, cpt = points[ids]
        lo = np.maximum(np.floor(points[ids, :2].min(0)).astype(int), 0)
        hi = np.minimum(np.ceil(points[ids, :2].max(0)).astype(int), [width - 1, height - 1])
        if np.any(lo > hi):
            continue
        denom = (b[1] - cpt[1]) * (a[0] - cpt[0]) + (cpt[0] - b[0]) * (a[1] - cpt[1])
        if abs(denom) < 1e-8:
            continue
        yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        x, y = xx + 0.5, yy + 0.5
        w0 = ((b[1] - cpt[1]) * (x - cpt[0]) + (cpt[0] - b[0]) * (y - cpt[1])) / denom
        w1 = ((cpt[1] - a[1]) * (x - cpt[0]) + (a[0] - cpt[0]) * (y - cpt[1])) / denom
        w2 = 1 - w0 - w1
        z = w0 * a[2] + w1 * b[2] + w2 * cpt[2]
        mask = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (z > depth[yy, xx])
        if not mask.any():
            continue
        weights = np.column_stack((w0[mask], w1[mask], w2[mask]))
        tuv = weights @ uv[ids]
        tx = (np.mod(tuv[:, 0], 1) * (tex.shape[1] - 1)).astype(int)
        vv = np.mod(tuv[:, 1], 1) if flip_v else 1.0 - np.mod(tuv[:, 1], 1)
        ty = (vv * (tex.shape[0] - 1)).astype(int)
        rgb[yy[mask], xx[mask]] = tex[ty, tx].astype(float) * shade[idx]
        depth[yy[mask], xx[mask]] = z[mask]
    return Image.fromarray(rgb.clip(0, 255).astype(np.uint8))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', type=Path, required=True, help='folder with Component N.fmt/.vb/.ib')
    parser.add_argument('--component', type=int, required=True)
    parser.add_argument('--diffuse', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('v-convention.png'))
    args = parser.parse_args()

    fields, indices = read_component(args.capture, args.component)
    position = fields[('POSITION', 0)]['data'].astype('f4')
    uv = fields[('TEXCOORD', 0)]['data'].astype('f4')[:, :2]
    triangles = indices.reshape(-1, 3)
    used, remapped = np.unique(triangles, return_inverse=True)
    # WWMI captures are Z-up; convert to Y-up for the preview renderer.
    xyz = np.column_stack((position[used][:, 0], position[used][:, 2], -position[used][:, 1]))
    faces = remapped.reshape(-1, 3)
    texture = Image.open(args.diffuse).convert('RGB')

    cells = []
    for flip_v, label in ((True, 'A: row0 = V0 (Direct3D)'), (False, 'B: row0 = V1 (image)')):
        for angle, angle_label in ((0.0, 'front'), (np.pi, 'back')):
            cells.append((sample_render(xyz, faces, uv[used], texture, angle, flip_v),
                          '%s / %s' % (label, angle_label)))
    canvas = Image.new('RGB', (460 * 4, 800), '#e9ecf0')
    draw = ImageDraw.Draw(canvas)
    for i, (image, label) in enumerate(cells):
        canvas.paste(image, (460 * i, 30))
        draw.text((460 * i + 8, 8), label, fill='#263748')
    canvas.save(args.output)
    print(args.output)


if __name__ == '__main__':
    main()
