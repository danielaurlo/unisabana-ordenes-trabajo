from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook

from gestor_contratos.models.orden_trabajo import OrdenTrabajoData, ProveedorData
from gestor_contratos.services.excel_generator import ExcelGenerator

TEMPLATE = Path("assets/plantilla/acta_entrega_vacia.xlsx")
SHEET = "Acta de Entrega Final de Manten"


@pytest.mark.parametrize("value", ['=1+1', '=HYPERLINK("https://example.invalid")'])
def test_untrusted_values_are_stored_as_text(value: str) -> None:
    data = sample_data()
    data.proveedor.nombre = value
    workbook = load_workbook(BytesIO(ExcelGenerator().generate(data)))
    cell = workbook[SHEET]["N11"]
    assert cell.value == value
    assert cell.data_type == "s"


def sample_data() -> OrdenTrabajoData:
    return OrdenTrabajoData(
        fecha_orden=date(2026, 9, 15),
        fecha_acta=date(2026, 9, 15),
        fecha_vencimiento=date(2026, 9, 30),
        fecha_inicio=date(2026, 9, 15),
        numero_orden="12345",
        numero_orden_original="0000012345",
        tipo_orden="Orden de Trabajo",
        objeto="Servicio ficticio de mantenimiento",
        sede="SEDE DE PRUEBA",
        proveedor=ProveedorData(
            nombre="PROVEEDOR FICTICIO SAS",
            nit="000000000",
            direccion="DIRECCION FICTICIA 123",
            persona_contacto="PERSONA DE PRUEBA",
            ciudad="CIUDAD DE PRUEBA",
            telefono="000-0000",
            correo="proveedor@example.invalid",
        ),
    )


def test_fills_institutional_template_without_changing_source() -> None:
    original_bytes = TEMPLATE.read_bytes()
    original_hash = sha256(original_bytes).hexdigest()
    original_workbook = load_workbook(TEMPLATE, data_only=False)
    original_sheet = original_workbook[SHEET]
    original_merged = set(str(item) for item in original_sheet.merged_cells.ranges)
    original_style = original_sheet["AQ14"]._style

    generated = ExcelGenerator().generate(sample_data())

    result_workbook = load_workbook(BytesIO(generated))
    result_sheet = result_workbook[SHEET]
    assert result_sheet["N11"].value == "PROVEEDOR FICTICIO SAS"
    assert result_sheet["G12"].value == "000000000"
    assert result_sheet["AR12"].value == "000-0000"
    assert result_sheet["N13"].value == "DIRECCION FICTICIA 123"
    assert result_sheet["M14"].value == "12345"
    assert result_sheet["AJ22"].value == "12345"
    assert result_sheet["AQ14"].value.date() == date(2026, 9, 15)
    assert result_sheet["N28"].value is None
    assert result_sheet["S28"].value is None
    assert result_sheet["X28"].value is None
    assert result_sheet["Y15"].value.date() == date(2026, 9, 30)
    assert result_sheet["N16"].value is None
    assert result_sheet["J7"].value == 15
    assert result_sheet["L7"].value == 9
    assert result_sheet["N7"].value == 2026
    assert result_sheet["F21"].value is None
    assert result_sheet["N21"].value is None
    assert result_sheet["Y21"].value is None
    assert (
        set(str(item) for item in result_sheet.merged_cells.ranges) == original_merged
    )
    assert result_sheet["AQ14"]._style == original_style
    allowed_acta_cells = {
        "J7",
        "L7",
        "N7",
        "N11",
        "G12",
        "AR12",
        "N13",
        "M14",
        "AQ14",
        "Y15",
        "N16",
        "F21",
        "N21",
        "Y21",
        "AJ22",
        "N28",
        "S28",
        "X28",
    }
    for row in original_sheet.iter_rows():
        for source_cell in row:
            if source_cell.coordinate not in allowed_acta_cells:
                assert (
                    result_sheet[source_cell.coordinate].value
                    == source_cell.value
                )

    assert result_workbook.sheetnames == [SHEET]
    assert sha256(TEMPLATE.read_bytes()).hexdigest() == original_hash


def test_leaves_certificate_fields_blank_for_legacy_data() -> None:
    data = sample_data().model_copy(
        update={
            "requiere_certificado": True,
            "tipo_certificado": "Certificado de disposición final",
        }
    )

    generated = ExcelGenerator().generate(data)

    workbook = load_workbook(BytesIO(generated))
    sheet = workbook[SHEET]
    assert sheet["N28"].value is None
    assert sheet["S28"].value is None
    assert sheet["X28"].value is None


def test_allows_missing_fields_and_clears_old_template_values(
    tmp_path: Path,
) -> None:
    custom_template = tmp_path / "template_with_old_phone.xlsx"
    workbook = load_workbook(TEMPLATE, data_only=False)
    workbook[SHEET]["AR12"] = "TELÉFONO ANTERIOR"
    workbook.save(custom_template)

    data = sample_data()
    data.proveedor.telefono = None
    data.campos_faltantes = ["proveedor.telefono"]

    generated = ExcelGenerator(custom_template).generate(data)

    result = load_workbook(BytesIO(generated))
    assert result[SHEET]["AR12"].value is None
