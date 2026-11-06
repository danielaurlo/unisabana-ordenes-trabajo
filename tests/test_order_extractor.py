from datetime import date
from pathlib import Path

import pymupdf

from gestor_contratos.services.order_extractor import OrdenTrabajoExtractor


def test_extracts_work_order_example() -> None:
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "1. FECHA DE LA ORDEN\n15\n09\n2026\n"
            "2. CONSECUTIVO DE LA ORDEN\nOrden de Trabajo\n0000012345\n"
            "4.1. Nombre: PROVEEDOR FICTICIO SAS\n"
            "4.2. Nit: 000000000\n"
            "4.3. Direccion: DIRECCION FICTICIA 123\n"
            "4.4. Persona contacto: PERSONA DE PRUEBA\n"
            "4.6. Telefono: 000-0000\n"
            "3.4. Fecha de Entrega / Fecha de Vencimiento: 30/09/2026",
        )
        data = OrdenTrabajoExtractor().extract(document.tobytes())

    assert data.fecha_orden is not None
    assert data.fecha_orden.isoformat() == "2026-09-15"
    assert data.fecha_acta is not None
    assert data.fecha_acta == date.today()
    assert data.numero_orden == "12345"
    assert data.numero_orden_original == "0000012345"
    assert data.proveedor.nombre == "PROVEEDOR FICTICIO SAS"
    assert data.proveedor.nit == "000000000"
    assert data.proveedor.direccion == "DIRECCION FICTICIA 123"
    assert data.proveedor.telefono == "000-0000"
    assert data.fecha_vencimiento is not None
    assert data.fecha_vencimiento.isoformat() == "2026-09-30"
    assert data.objeto is None
    assert data.sede is None
    assert data.detalles == []
    assert data.total is None
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
    assert data.campos_faltantes.count("proveedor.nit") == 1


def test_does_not_use_the_mobile_label_as_an_empty_phone(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "1. FECHA DE LA ORDEN\n15\n09\n2026\n"
        "4.6. Teléfono:\n4.7. Celular: 3001234567",
    )
    path = tmp_path / "telefono_vacio.pdf"
    document.save(path)
    document.close()

    data = OrdenTrabajoExtractor().extract(path.read_bytes())

    assert data.proveedor.telefono is None
    assert "proveedor.telefono" in data.campos_faltantes
