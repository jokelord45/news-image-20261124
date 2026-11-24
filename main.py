#!/usr/bin/env python3
"""news-image-20261124 entrypoint: THE TUESDAY GLOBE front page.

Writes the bundled front-page picture to the directory named by
MAKEFUN_OUTPUT_DIR (or /output when the variable is unset), as
entry.png. The written file is hashed and compared with the bundled
file, so two runs always produce the same bytes.

Only the Python standard library is used: the grading sandbox
provides nothing else. The picture was drawn while building this
entry with PIL (see draw.py, kept next to this repository); it is a
JPEG of 768 by 1024 pixels, about 219 KB, inside the competition's
limits of 1 MiB and 1024 by 1024 pixels.
"""
import hashlib
import os
import shutil
import struct
import sys
from pathlib import Path

ENTRY_NAME = "entry.png"
MAX_FILE_BYTES = 1_048_576
MAX_DIMENSION = 1024

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
SOF_MARKERS = {0xC0, 0xC1, 0xC2}
NO_LENGTH_MARKERS = {0xD8, 0x01} | set(range(0xD0, 0xD8 + 1))


def die(message):
    print("error:", message, file=sys.stderr)
    raise SystemExit(1)


def read_jpeg_size(blob):
    """Return (width, height) of a JPEG byte string, or None.

    Walks the marker segments after the SOI marker until the first
    Start-Of-Frame segment; returns None for anything that is not a
    JPEG or that ends before a frame appears.
    """
    if len(blob) < 4 or blob[:2] != SOI:
        return None
    pos = 2
    while pos + 9 <= len(blob):
        if blob[pos] != 0xFF:
            return None
        marker = blob[pos + 1]
        if marker in SOF_MARKERS:
            height, width = struct.unpack(">HH", blob[pos + 5:pos + 9])
            return width, height
        if marker == 0xDA:
            return None  # scan data follows; no frame header after this
        if marker in NO_LENGTH_MARKERS:
            pos += 2
            continue
        size = struct.unpack(">H", blob[pos + 2:pos + 4])[0]
        pos += 2 + size
    return None


def check_image(blob):
    """Refuse anything that is not a complete JPEG within the limits."""
    if len(blob) < 4:
        die("bundled image is too short to be a JPEG")
    if len(blob) > MAX_FILE_BYTES:
        die("bundled image is too large: %d bytes" % len(blob))
    if blob[-2:] != EOI:
        die("bundled image has no JPEG end marker")
    size = read_jpeg_size(blob)
    if size is None:
        die("cannot read the bundled image's dimensions")
    width, height = size
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        die("bundled image is too big: %dx%d" % (width, height))
    return width, height


def main():
    source = Path(__file__).resolve().parent / ENTRY_NAME
    if not source.is_file():
        die("bundled image missing: %s" % source)
    blob = source.read_bytes()
    width, height = check_image(blob)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    destination = Path(out_dir) / ENTRY_NAME
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        die("cannot create output directory %s: %s" % (out_dir, exc))
    if not destination.parent.is_dir():
        die("output path is not a directory: %s" % out_dir)
    shutil.copyfile(source, destination)
    written = destination.read_bytes()
    if written != blob:
        die("written output differs from the bundled image")
    # Second layer: the bytes on disk must still parse as the same JPEG.
    out_width, out_height = check_image(written)
    if (out_width, out_height) != (width, height):
        die("written output dimensions changed: %dx%d"
            % (out_width, out_height))

    digest = hashlib.sha256(written).hexdigest()
    print("entry.png: %dx%d, %d bytes, sha256 %s -> %s"
          % (width, height, len(written), digest, destination))


if __name__ == "__main__":
    main()
