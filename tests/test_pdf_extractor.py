from io import BytesIO

import pymupdf
import pytest

from gestor_contratos.services.pdf_extractor import (
    InvalidPDFError,
    PDFEmptyError,
    PDFExtractor,
    PDFTooLargeError,
    PDFWithoutTextError,
    ProtectedPDFError,
)


def create_pdf(*page_texts: str) -> bytes:
    document = pymupdf.open()
    for page_text in page_texts:
        page = document.new_page()
        page.insert_text((72, 72), page_text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def create_protected_pdf() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Contenido protegido ficticio")
    output = BytesIO()
    document.save(
        output,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    document.close()
    return output.getvalue()


def test_extracts_text_from_all_pages() -> None:
    result = PDFExtractor().extract(create_pdf("Página uno", "Página dos"))

    assert result.page_count == 2
    assert "Página uno" in result.text
    assert "Página dos" in result.text


def test_rejects_empty_pdf_bytes() -> None:
    with pytest.raises(PDFEmptyError, match="No se recibió"):
        PDFExtractor().extract(b"")


def test_rejects_non_pdf_content() -> None:
    with pytest.raises(InvalidPDFError, match="no es un PDF"):
        PDFExtractor().extract(b"contenido ficticio")


def test_rejects_pdf_above_configured_limit() -> None:
    with pytest.raises(PDFTooLargeError, match="tamaño máximo"):
        PDFExtractor(max_size_bytes=10).extract(create_pdf("Contenido"))


def test_reports_pdf_without_extractable_text() -> None:
    document = pymupdf.open()
    document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    with pytest.raises(PDFWithoutTextError, match="no contiene texto"):
        PDFExtractor().extract(pdf_bytes)


def test_reports_protected_pdf() -> None:
    with pytest.raises(ProtectedPDFError, match="protegido con contraseña"):
        PDFExtractor().extract(create_protected_pdf())
