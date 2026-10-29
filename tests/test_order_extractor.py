from datetime import date
from pathlib import Path

import pymupdf

from gestor_contratos.services.order_extractor import OrdenTrabajoExtractor

EXAMPLE_PDF = Path(
    "assets/ejemplos/230. TALA ARBOL PUENTE MADERA - LA MANA_OT27012-1.pdf"
)


def test_extracts_work_order_example() -> None:
    data = OrdenTrabajoExtractor().extract(EXAMPLE_PDF.read_bytes())

    assert data.fecha_orden is not None
    assert data.fecha_orden.isoformat() == "2026-09-15"
    assert data.fecha_acta is not None
    assert data.fecha_acta.isoformat() == "2026-09-15"
    assert data.numero_orden == "27012"
    assert data.numero_orden_original == "0000027012"
    assert data.proveedor.nombre == "ARBOLES Y PLANTAS LA MANA SAS"
    assert data.proveedor.nit == "900983709"
    assert data.proveedor.direccion == "VDA FONQUETA LT 3 UN VILLA CONCHA"
    assert data.sede == "PARQUEADEROS"
    assert data.detalles[0].cantidad == 1
    assert data.detalles[0].valor_total == 650000
    assert data.total == 650000
    assert not data.campos_faltantes
    assert not data.campos_ambiguos


def test_extracts_missing_fields_without_inventing_values(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "1. FECHA DE LA ORDEN\n15\n09\n2026")
    path = tmp_path / "incompleto.pdf"
    document.save(path)
    document.close()

    data = OrdenTrabajoExtractor().extract(path.read_bytes())

    assert data.fecha_orden is not None
    assert data.fecha_acta == date.today()
    assert "fecha_acta" not in data.campos_faltantes
    assert data.numero_orden is None
    assert data.proveedor.nombre is None
    assert "numero_orden" in data.campos_faltantes
    assert "proveedor.nombre" in data.campos_faltantes
