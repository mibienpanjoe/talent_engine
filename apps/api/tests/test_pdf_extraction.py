import hashlib
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from talent_engine.sources.extraction import extract_pdf


def text_pdf(
    pages=(
        "Projet personnel : verification du resultat.",
        "Apprentissage : essai et ajustement.",
    ),
):
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        stream = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(
            ("BT /F1 12 Tf 50 700 Td (" + escaped + ") Tj ET").encode("latin1")
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_isolated_pdf_preserves_text_pages_and_hashes(tmp_path):
    content = text_pdf()
    path = tmp_path / "private.pdf"
    path.write_bytes(content)
    result = extract_pdf(path, hashlib.sha256(content).hexdigest())
    assert result["state"] == "available"
    assert [p["page"] for p in result["pages"]] == [1, 2]
    assert result["pages"][0]["text"] == "Projet personnel : verification du resultat."
    assert result["ocr_pages"] == []
    assert extract_pdf(path, "0" * 64)["error_code"] == "content_hash_mismatch"


def test_scan_and_corrupt_are_explicit(tmp_path):
    path = tmp_path / "private.pdf"
    data = text_pdf(("",))
    path.write_bytes(data)
    result = extract_pdf(path, hashlib.sha256(data).hexdigest())
    assert result["state"] == "unavailable" and result["ocr_pages"] == [1]
    assert result["error_code"] == "ocr_required"
    path.write_bytes(b"%PDF-corrupt")
    assert (
        extract_pdf(path, hashlib.sha256(path.read_bytes()).hexdigest())["state"]
        == "unreadable"
    )
