"""news-image-20261120 R1 — publish the chosen front-page image.

The repository ships one finished picture (``entry.png`` — a JPEG file that
keeps the .png name the competition requires).  This program validates the
picture against the competition gate and then copies it, byte for byte, to
``$MAKEFUN_OUTPUT_DIR/entry.png`` (``/output`` when the variable is unset).

Standard library only.  No network, no clock, no randomness, so two runs
produce byte-identical output.
"""

import hashlib
import os
import struct
import sys

PICTURE = "entry.png"
MAX_BYTES = 1_048_576          # competition limit: 1 MiB
MAX_SIDE_PX = 1024             # competition limit: 1024 px per side
SOI = b"\xff\xd8\xff"           # JPEG start-of-image marker
EOI = b"\xff\xd9"              # JPEG end-of-image marker
SOF_MARKERS = set(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


def here() -> str:
    """Folder containing this script — the repository root."""
    return os.path.dirname(os.path.abspath(__file__))


def destination_dir() -> str:
    """Grader output directory, honouring MAKEFUN_OUTPUT_DIR."""
    return os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"


def jpeg_dimensions(blob: bytes) -> tuple[int, int]:
    """Return (width, height) from the first SOF segment of a JPEG blob.

    Steps through the marker chain, skipping standalone markers and
    length-prefixed segments, until a Start-Of-Frame marker yields the
    dimensions stored as (height, width) in the segment payload.
    """
    if blob[:3] != SOI:
        raise ValueError("not a JPEG: SOI marker missing at offset 0")
    cursor = 2
    while cursor + 9 <= len(blob):
        if blob[cursor] != 0xFF:
            raise ValueError("not a JPEG: marker prefix lost mid-stream")
        marker = blob[cursor + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            cursor += 2
            continue
        length = struct.unpack(">H", blob[cursor + 2:cursor + 4])[0]
        if length < 2 or cursor + 2 + length > len(blob):
            raise ValueError("not a JPEG: segment length runs past EOF")
        if marker in SOF_MARKERS:
            height, width = struct.unpack(">HH", blob[cursor + 5:cursor + 9])
            return width, height
        cursor += 2 + length
    raise ValueError("not a JPEG: no SOF marker in stream")


def gate(blob: bytes) -> tuple[int, int]:
    """Apply every competition limit to the picture bytes; return its size."""
    if not blob:
        raise ValueError("picture is empty")
    if len(blob) > MAX_BYTES:
        raise ValueError(f"picture is {len(blob)} bytes, over {MAX_BYTES}")
    if blob[:4] == b"\x89PNG":
        raise ValueError("picture is a PNG, not a JPEG")
    if blob[-2:] != EOI:
        raise ValueError("picture is truncated: EOI marker missing")
    width, height = jpeg_dimensions(blob)
    if width == 0 or height == 0:
        raise ValueError("picture reports a zero side in its SOF marker")
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX:
        raise ValueError(f"picture is {width}x{height}, over {MAX_SIDE_PX}px")
    return width, height


def main() -> int:
    source = os.path.join(here(), PICTURE)
    with open(source, "rb") as handle:
        blob = handle.read()
    width, height = gate(blob)
    digest = hashlib.sha256(blob).hexdigest()

    out_dir = destination_dir()
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, PICTURE)
    if os.path.isdir(target):
        raise ValueError(f"output path {target} is a directory, not a file")
    with open(target, "wb") as handle:
        handle.write(blob)
    # Prove the copy on disk is the same picture: re-read it, compare
    # bytes and hash, and re-parse its dimensions from scratch.
    with open(target, "rb") as handle:
        landed = handle.read()
    if landed != blob:
        raise ValueError("written picture differs from the source picture")
    if hashlib.sha256(landed).hexdigest() != digest:
        raise ValueError("written picture hash differs from source hash")
    landed_w, landed_h = jpeg_dimensions(landed)
    if (landed_w, landed_h) != (width, height):
        raise ValueError("written picture dimensions differ from source")

    print(f"wrote {target} ({width}x{height}, {len(blob)} bytes)")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
