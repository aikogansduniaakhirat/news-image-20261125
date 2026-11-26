#!/usr/bin/env python3
"""Publish the rendered front page into the make.fun output directory.

Standard library only: no Pillow, no network, no clock.  The renderer in
art/render.py is the only part that needs Pillow; this copier moves the finished
PNG into place and refuses to publish anything that breaks the bounty's gate.

Two runs write identical bytes by construction, because the source is a
committed file and nothing here transforms it.  The assertions make that
explicit rather than assumed: if the committed art drifts out of the gate, this
fails loudly instead of shipping a non-compliant entry.
"""

import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "art" / "entry.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_EDGE = 1024
MAX_BYTES = 1048576


def ihdr_size(data):
    """Return (width, height) from the PNG's IHDR chunk.

    The offsets are fixed by the PNG spec, so this needs no dependency: an
    8-byte signature, then a 4-byte length and the "IHDR" tag, then the two
    4-byte big-endian dimensions.
    """
    assert data[:8] == PNG_SIGNATURE, "not a PNG: bad signature"
    assert data[12:16] == b"IHDR", "not a PNG: first chunk is not IHDR"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def main():
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    if not SOURCE.exists():
        print("error: source image missing: %s\n"
              "       render it first with: python3 art/render.py" % SOURCE,
              file=sys.stderr)
        return 1

    data = SOURCE.read_bytes()
    width, height = ihdr_size(data)
    problems = []

    if width > MAX_EDGE:
        problems.append("width %d exceeds %d" % (width, MAX_EDGE))
    if height > MAX_EDGE:
        problems.append("height %d exceeds %d" % (height, MAX_EDGE))
    if len(data) > MAX_BYTES:
        problems.append("size %d exceeds %d" % (len(data), MAX_BYTES))
    if width != height:
        # The bounty asks for a whole image; a square is what the feed and the
        # judge's contact sheet assume, so a non-square render is a bug here.
        problems.append("image is %dx%d, not square" % (width, height))
    if problems:
        # Report every breach at once: a renderer change can break two rules.
        print("error: entry.png breaks the image gate: %s" % "; ".join(problems),
              file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "entry.png"
    written = target.write_bytes(data)
    assert written == len(data), "wrote %d of %d bytes" % (written, len(data))
    assert target.read_bytes() == data, "bytes on disk differ from source"

    # Print the digest so a run's log shows the artifact is the same bytes twice
    # without anyone having to diff the two output directories by hand.
    import hashlib
    print("copied %s -> %s (%d bytes, %dx%d, sha256 %s)"
          % (SOURCE, target, len(data), width, height,
             hashlib.sha256(data).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
