import pymupdf
import pytest

from gestor_contratos.services.combined_pdf_generator import (
    CombinedPDFGenerationError,
    CombinedPDFGenerator,
)


def make_pdf(*page_texts: str) -> bytes:
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


class FakeRenderer:
    def __init__(self, result: bytes) -> None:
        self.result = result
        self.received_excel: bytes | None = None

    def render(self, excel_bytes: bytes) -> bytes:
        self.received_excel = excel_bytes
        return self.result


def test_appends_generated_acta_after_complete_source_order() -> None:
    order_pdf = make_pdf("ORDEN PAGINA 1", "ORDEN PAGINA 2")
    acta_pdf = make_pdf("ACTA DILIGENCIADA")
    renderer = FakeRenderer(acta_pdf)

    result = CombinedPDFGenerator(renderer=renderer).generate(
        order_pdf, b"excel generado"
    )

    assert renderer.received_excel == b"excel generado"
    assert result.acta_pdf_bytes == acta_pdf
    with pymupdf.open(stream=result.combined_pdf_bytes, filetype="pdf") as document:
        assert document.page_count == 3
        assert "ORDEN PAGINA 1" in document[0].get_text()
        assert "ORDEN PAGINA 2" in document[1].get_text()
        assert "ACTA DILIGENCIADA" in document[2].get_text()


def test_rejects_an_invalid_source_order_pdf() -> None:
    renderer = FakeRenderer(make_pdf("ACTA"))

    with pytest.raises(CombinedPDFGenerationError):
        CombinedPDFGenerator(renderer=renderer).generate(
            b"not a pdf", b"excel generado"
        )
