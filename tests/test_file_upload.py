from pathlib import Path

import pytest

from file_upload import (
    MAX_EXTRACTED_TEXT,
    MAX_FILE_SIZE,
    process_uploaded_file,
)


def test_txt_file_is_extracted():
    file_data = b"Python developer with FastAPI experience."

    result = process_uploaded_file(
        "resume.txt",
        file_data,
    )

    assert result == (
        "Python developer with FastAPI experience."
    )


def test_extension_is_case_insensitive():
    file_data = b"Python developer."

    result = process_uploaded_file(
        "resume.TXT",
        file_data,
    )

    assert result == "Python developer."


def test_unsupported_extension_is_rejected():
    with pytest.raises(ValueError, match="Unsupported file type"):
        process_uploaded_file(
            "resume.exe",
            b"malicious content",
        )


def test_file_size_limit_is_enforced():
    oversized_file = b"x" * (MAX_FILE_SIZE + 1)

    with pytest.raises(
        ValueError,
        match="File is too large",
    ):
        process_uploaded_file(
            "resume.txt",
            oversized_file,
        )


def test_invalid_pdf_signature_is_rejected():
    with pytest.raises(
        ValueError,
        match="valid PDF",
    ):
        process_uploaded_file(
            "resume.pdf",
            b"not actually a PDF",
        )


def test_invalid_docx_signature_is_rejected():
    with pytest.raises(
        ValueError,
        match="valid DOCX",
    ):
        process_uploaded_file(
            "resume.docx",
            b"not actually a DOCX",
        )


def test_invalid_utf8_txt_is_rejected():
    invalid_utf8 = b"\xff\xfe\xfa"

    with pytest.raises(UnicodeDecodeError):
        process_uploaded_file(
            "resume.txt",
            invalid_utf8,
        )


def test_extracted_text_limit_is_enforced():
    oversized_text = (
        "Python developer. "
        * (MAX_EXTRACTED_TEXT // 18 + 1)
    ).encode("utf-8")

    with pytest.raises(
        ValueError,
        match="Extracted text is too large",
    ):
        process_uploaded_file(
            "resume.txt",
            oversized_text,
        )

def _make_docx_with_xml(xml_bytes):
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", xml_bytes)
    return buffer.getvalue()


def test_docx_archive_that_expands_hugely_is_rejected_before_parsing():
    bomb = _make_docx_with_xml(b"<w:p/>" * (6 * 1024 * 1024 // 6 + 10))

    assert len(bomb) < 100_000

    with pytest.raises(ValueError, match="too large when opened"):
        process_uploaded_file("resume.docx", bomb)


def test_pdf_with_too_many_pages_is_rejected():
    import io

    from pypdf import PdfWriter

    from file_upload import MAX_PDF_PAGES

    writer = PdfWriter()
    for _ in range(MAX_PDF_PAGES + 1):
        writer.add_blank_page(612, 792)
    buffer = io.BytesIO()
    writer.write(buffer)

    with pytest.raises(ValueError, match="too many pages"):
        process_uploaded_file("resume.pdf", buffer.getvalue())
