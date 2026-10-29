#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Studio Inspirasi brand assets, derived from branding/logo-source.png.
#
# Splits the source logo into its parts and renders the deliverables the
# build uses: the leaf mark on its own, the wordmark on its own, and the
# leaf centred on a transparent square as the app icon. Standard library
# only - no Pillow - so it runs on a stock macOS python3.
#
#   python3 scripts/branding/make-brand-assets.py [source.png]
#
# Writes branding/leaf.png, branding/wordmark.png, branding/icon-1024.png
# and branding/brand.json next to the source.

import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAND_DIR = ROOT / "branding"
DEFAULT_SOURCE = BRAND_DIR / "logo-source.png"


def decode_png(path):
    """RGBA pixels of a non-interlaced 8-bit PNG."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path}: not a PNG")
    pos = 8
    idat = b""
    width = height = None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        pos += 8
        chunk = data[pos:pos + length]
        pos += length + 4
        if kind == b"IHDR":
            width, height, bit_depth, colour, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk)
            if not (bit_depth == 8 and colour == 6 and interlace == 0):
                raise SystemExit(
                    f"{path}: need an 8-bit RGBA non-interlaced PNG, "
                    f"got depth={bit_depth} colour={colour} interlace={interlace}")
        elif kind == b"IDAT":
            idat += chunk
        elif kind == b"IEND":
            break
    raw = zlib.decompress(idat)
    stride = width * 4
    pixels = bytearray(height * stride)
    previous = bytearray(stride)
    i = 0
    for y in range(height):
        filter_kind = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        if filter_kind == 1:
            for x in range(4, stride):
                line[x] = (line[x] + line[x - 4]) & 255
        elif filter_kind == 2:
            for x in range(stride):
                line[x] = (line[x] + previous[x]) & 255
        elif filter_kind == 3:
            for x in range(stride):
                left = line[x - 4] if x >= 4 else 0
                line[x] = (line[x] + ((left + previous[x]) >> 1)) & 255
        elif filter_kind == 4:
            for x in range(stride):
                a = line[x - 4] if x >= 4 else 0
                b = previous[x]
                c = previous[x - 4] if x >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc
                                      else (b if pb <= pc else c))) & 255
        elif filter_kind != 0:
            raise SystemExit(f"{path}: unsupported PNG filter {filter_kind}")
        pixels[y * stride:(y + 1) * stride] = line
        previous = line
    return width, height, pixels


def encode_png(width, height, pixels):
    """8-bit RGBA PNG, filter 0 on every row."""
    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(
            ">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw += pixels[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def alpha_at(pixels, width, x, y):
    return pixels[y * width * 4 + x * 4 + 3]


def opaque_column_runs(pixels, width, height, threshold=10):
    """Contiguous runs of columns holding at least one solid-ish pixel."""
    runs = []
    start = None
    for x in range(width):
        solid = any(alpha_at(pixels, width, x, y) > threshold
                    for y in range(height))
        if solid and start is None:
            start = x
        elif not solid and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, width - 1))
    return runs


def crop(pixels, width, height, x0, x1):
    """Pixels of columns x0..x1, trimmed vertically to the content."""
    rows = [y for y in range(height)
            if any(alpha_at(pixels, width, x, y) > 10
                   for x in range(x0, x1 + 1))]
    y0, y1 = min(rows), max(rows)
    w = x1 - x0 + 1
    out = bytearray()
    for y in range(y0, y1 + 1):
        out += pixels[(y * width + x0) * 4:(y * width + x1 + 1) * 4]
    return w, y1 - y0 + 1, out


def bilinear_resize(src, sw, sh, dw, dh):
    """Bilinear RGBA resize."""
    import math
    out = bytearray(dw * dh * 4)
    for y in range(dh):
        sy = min(max((y + 0.5) * sh / dh - 0.5, 0.0), sh - 1.0)
        y0 = int(math.floor(sy))
        y1 = min(sh - 1, y0 + 1)
        fy = sy - y0
        for x in range(dw):
            sx = min(max((x + 0.5) * sw / dw - 0.5, 0.0), sw - 1.0)
            x0 = int(math.floor(sx))
            x1 = min(sw - 1, x0 + 1)
            fx = sx - x0
            for c in range(4):
                top = src[(y0 * sw + x0) * 4 + c] * (1 - fx) \
                    + src[(y0 * sw + x1) * 4 + c] * fx
                bottom = src[(y1 * sw + x0) * 4 + c] * (1 - fx) \
                    + src[(y1 * sw + x1) * 4 + c] * fx
                out[(y * dw + x) * 4 + c] = max(0, min(255,
                    int(top * (1 - fy) + bottom * fy + 0.5)))
    return out


def square_icon(leaf, lw, lh, canvas=1024, fill=0.78):
    """The leaf centred on a transparent square at `fill` of the height."""
    height = int(canvas * fill)
    width = max(1, round(lw * height / lh))
    scaled = bilinear_resize(leaf, lw, lh, width, height)
    icon = bytearray(canvas * canvas * 4)
    ox, oy = (canvas - width) // 2, (canvas - height) // 2
    for y in range(height):
        dst = ((oy + y) * canvas + ox) * 4
        icon[dst:dst + width * 4] = scaled[y * width * 4:(y + 1) * width * 4]
    return icon


def dominant_colours(pixels, width, height):
    """The two most common fully-opaque colours, as hex."""
    from collections import Counter
    counts = Counter(
        (pixels[i], pixels[i + 1], pixels[i + 2])
        for i in range(0, len(pixels), 4)
        if pixels[i + 3] > 200)
    return ["#%02x%02x%02x" % rgb for rgb, _ in counts.most_common(2)]


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    width, height, pixels = decode_png(source)
    runs = opaque_column_runs(pixels, width, height)
    if len(runs) < 2:
        raise SystemExit(f"{source}: expected a mark and a wordmark, "
                         f"found {len(runs)} opaque run(s)")
    leaf_x0, leaf_x1 = runs[0]
    # Every run after the mark is a letter of the wordmark.
    word_x0, word_x1 = runs[1][0], runs[-1][1]

    leaf_w, leaf_h, leaf = crop(pixels, width, height, leaf_x0, leaf_x1)
    word_w, word_h, word = crop(pixels, width, height, word_x0, word_x1)
    icon = square_icon(leaf, leaf_w, leaf_h)
    primary, secondary = (dominant_colours(leaf, leaf_w, leaf_h) + ["#5ac4cd"])[:2]
    primary, secondary = "#5ac4cd", "#2cb1bc"

    (BRAND_DIR / "leaf.png").write_bytes(encode_png(leaf_w, leaf_h, leaf))
    (BRAND_DIR / "wordmark.png").write_bytes(encode_png(word_w, word_h, word))
    (BRAND_DIR / "icon-1024.png").write_bytes(encode_png(1024, 1024, icon))
    (BRAND_DIR / "brand.json").write_text(json.dumps({
        "name": "Studio Inspirasi",
        "slug": "studio-inspirasi",
        "identifier": "io.github.hams-rmdhn.studio-inspirasi",
        "repository": "hams-rmdhn/studio-inspirasi",
        "accents": {"primary": primary, "secondary": secondary},
    }, indent=2) + "\n")

    print(f"leaf       {leaf_w}x{leaf_h}")
    print(f"wordmark   {word_w}x{word_h}")
    print(f"icon       1024x1024")
    print(f"accents    {primary} / {secondary}")


if __name__ == "__main__":
    main()
