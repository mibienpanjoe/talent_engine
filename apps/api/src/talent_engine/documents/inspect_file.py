"""Bounded child process: never use user names or credentials here."""

import json
import resource
import sys
import warnings
from pathlib import Path


def inspect(path):
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    with open(path, "rb") as stream:
        prefix = stream.read(16)
    if prefix.startswith(b"%PDF-"):
        from pypdf import PdfReader

        reader = PdfReader(path, strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 30:
            raise ValueError("Unreadable PDF")
        return "application/pdf"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n") or prefix.startswith(b"\xff\xd8\xff"):
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = 25000000
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.width * image.height > 25000000 or image.format not in {
                "PNG",
                "JPEG",
            }:
                raise ValueError("Image limit")
            kind = image.format
            image.verify()
        # JPEG.verify() alone does not decode the image data.
        # Reopen after verify() and fully decode under the same process limits.
        with Image.open(path) as image:
            image.load()
        return "image/png" if kind == "PNG" else "image/jpeg"
    raise ValueError("Unsupported format")


if __name__ == "__main__":
    try:
        print(json.dumps({"media_type": inspect(Path(sys.argv[1]))}))
    except Exception:
        sys.exit(1)
