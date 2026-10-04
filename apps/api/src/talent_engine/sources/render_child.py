"""Credential-free PDF/image rasterization, never executes document code."""

import hashlib
import io
import resource
import sys


def render(path, expected, number):
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    with open(path, "rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("Content changed")
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 25000000
    if number:
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(path) as pdf:
            if not (1 <= len(pdf) <= 30 and 1 <= number <= len(pdf)):
                raise ValueError("PDF pages limit")
            page = pdf[number - 1]
            width, height = page.get_size()
            if width <= 0 or height <= 0:
                raise ValueError("Invalid size")
            bitmap = page.render(scale=min(2, 1600 / max(width, height)))
            image = bitmap.to_pil().convert("RGB")
            bitmap.close()
            page.close()
    else:
        with Image.open(path) as original:
            if original.width * original.height > 25000000:
                raise ValueError("Image limit")
            image = ImageOps.exif_transpose(original).convert("RGB")
    image.thumbnail((1600, 1600))
    output = io.BytesIO()
    image.save(output, format="PNG")
    data = output.getvalue()
    if len(data) > 2097152:
        raise ValueError("Render limit")
    return data


if __name__ == "__main__":
    try:
        sys.stdout.buffer.write(render(sys.argv[1], sys.argv[2], int(sys.argv[3])))
    except Exception:
        sys.exit(1)
