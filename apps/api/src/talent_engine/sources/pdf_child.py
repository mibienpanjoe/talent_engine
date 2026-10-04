"""Private PDF extraction in a bounded, credential-free child process."""

import hashlib
import json
import resource
import sys


def extract(path, expected):
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    with open(path, "rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected:
        return dict(
            state="unreadable",
            error_code="content_hash_mismatch",
            pages=[],
            ocr_pages=[],
        )
    from pypdf import PdfReader

    reader = PdfReader(path, strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 30:
        raise ValueError("PDF limit")
    pages, ocr, total = [], [], 0
    for number, page in enumerate(reader.pages, 1):
        content = page.get_contents()
        if content and len(content.get_data()) > 10485760:
            raise ValueError("Stream limit")
        text = (
            (page.extract_text() or "")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\x00", "\ufffd")
        )
        text = text.encode("utf-8", errors="replace").decode("utf-8")
        total += len(text)
        if total > 200000:
            raise ValueError("Text limit")
        if text.strip():
            pages.append(dict(page=number, text=text))
        else:
            ocr.append(number)
    return dict(
        state="available" if pages else "unavailable",
        error_code="ocr_required" if ocr else None,
        pages=pages,
        ocr_pages=ocr,
    )


if __name__ == "__main__":
    try:
        result = extract(sys.argv[1], sys.argv[2])
    except Exception:
        result = dict(
            state="unreadable", error_code="pdf_unreadable", pages=[], ocr_pages=[]
        )
    print(json.dumps(result))
