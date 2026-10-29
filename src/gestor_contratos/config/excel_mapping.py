"""Configurable mapping from extracted data to the institutional workbook."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE_PATH = PROJECT_ROOT / "assets" / "plantilla" / "3A GROUP SAS-1.xlsx"


@dataclass(frozen=True)
class ExcelCellTarget:
    """Destination cell for a field from the normalized order model."""

    sheet: str
    cell: str


EXCEL_FIELD_MAP: dict[str, tuple[ExcelCellTarget, ...]] = {
    "fecha_acta.day": (
        ExcelCellTarget("Acta de Entrega Final de Manten", "J7"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "F21"),
    ),
    "fecha_acta.month": (
        ExcelCellTarget("Acta de Entrega Final de Manten", "L7"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "N21"),
    ),
    "fecha_acta.year": (
        ExcelCellTarget("Acta de Entrega Final de Manten", "N7"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "Y21"),
    ),
    "fecha_orden.day": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "L7"),
    ),
    "fecha_orden.month": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "N7"),
    ),
    "fecha_orden.year": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "P7"),
    ),
    "tipo_orden": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AO7"),
    ),
    "numero_orden": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AS7"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "M14"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "AJ22"),
    ),
    "objeto": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "O10"),
    ),
    "sede": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "K12"),
    ),
    "proveedor.nombre": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "H17"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "N11"),
    ),
    "proveedor.nit": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AP17"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "G12"),
    ),
    "proveedor.direccion": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "I18"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "N13"),
    ),
    "proveedor.persona_contacto": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AM18"),
    ),
    "proveedor.ciudad": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "H19"),
    ),
    "proveedor.telefono": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AB19"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "AR12"),
    ),
    "proveedor.celular": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AR19"),
    ),
    "proveedor.correo": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "L20"),
    ),
    "fecha_orden": (
        ExcelCellTarget("Acta de Entrega Final de Manten", "AQ14"),
    ),
    "fecha_vencimiento": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "AL30"),
        ExcelCellTarget("Acta de Entrega Final de Manten", "Y15"),
    ),
    "fecha_real_entrega": (
        ExcelCellTarget("Acta de Entrega Final de Manten", "N16"),
    ),
    "fecha_inicio": (
        ExcelCellTarget("Orden de Trabajo-Servicio", "K30"),
    ),
}

DETAIL_TABLE_SHEET = "Orden de Trabajo-Servicio"
DETAIL_TABLE_START_ROW = 66
DETAIL_TABLE_END_ROW = 89
DETAIL_FIELD_COLUMNS = {
    "descripcion": "D",
    "unidad": "AE",
    "cantidad": "AK",
    "valor_unitario": "AP",
}
