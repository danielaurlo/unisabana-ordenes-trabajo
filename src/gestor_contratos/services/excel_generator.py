"""Generate a completed institutional Excel workbook in memory."""

from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from gestor_contratos.config.excel_mapping import (
    ACTUAL_DELIVERY_DATE_CELL,
    CERTIFICATE_NO_CELL,
    CERTIFICATE_SHEET,
    CERTIFICATE_TYPE_CELL,
    CERTIFICATE_YES_CELL,
    DEFAULT_TEMPLATE_PATH,
    DELIVERY_SECTION_DATE_CELLS,
    EXCEL_FIELD_MAP,
    ExcelCellTarget,
)
from gestor_contratos.models.orden_trabajo import OrdenTrabajoData


class ExcelGenerationError(Exception):
    """Raised when the workbook cannot be generated safely."""


class ExcelGenerator:
    """Fill the institutional workbook without modifying its source file."""

    def __init__(
        self,
        template_path: Path | str = DEFAULT_TEMPLATE_PATH,
        field_map: dict[str, tuple[ExcelCellTarget, ...]] = EXCEL_FIELD_MAP,
    ) -> None:
        self.template_path = Path(template_path)
        self.field_map = field_map

    def generate(self, data: OrdenTrabajoData) -> bytes:
        """Return a completed workbook as bytes."""
        if data.campos_ambiguos:
            raise ExcelGenerationError(
                "No se puede generar el Excel: hay campos ambiguos por revisar."
            )
        if not self.template_path.is_file():
            raise ExcelGenerationError(
                f"No se encontró la plantilla Excel: {self.template_path}"
            )

        try:
            workbook = load_workbook(self.template_path, data_only=False)
            self._clear_mapped_cells(workbook)
            for field_path, targets in self.field_map.items():
                value = self._resolve_field(data, field_path)
                for target in targets:
                    self._write_value(workbook, target, value)
            self._clear_certificate_requirement(workbook)
            workbook[CERTIFICATE_SHEET][ACTUAL_DELIVERY_DATE_CELL] = None
            for cell in DELIVERY_SECTION_DATE_CELLS:
                workbook[CERTIFICATE_SHEET][cell] = None

            output = BytesIO()
            workbook.save(output)
            return output.getvalue()
        except ExcelGenerationError:
            raise
        except (KeyError, OSError, ValueError) as exc:
            raise ExcelGenerationError(
                "No fue posible completar la plantilla Excel."
            ) from exc

    @staticmethod
    def _resolve_field(data: OrdenTrabajoData, field_path: str) -> Any:
        value: Any = data
        for part in field_path.split("."):
            if value is None:
                return None
            value = getattr(value, part)
        return value

    def _clear_mapped_cells(self, workbook: Any) -> None:
        """Clear template values before writing current acta data."""
        for targets in self.field_map.values():
            for target in targets:
                if target.sheet not in workbook.sheetnames:
                    raise ExcelGenerationError(
                        f"No existe la hoja configurada: {target.sheet}"
                    )
                workbook[target.sheet][target.cell] = None

    @staticmethod
    def _write_value(workbook: Any, target: ExcelCellTarget, value: Any) -> None:
        if value is None:
            return
        if target.sheet not in workbook.sheetnames:
            raise ExcelGenerationError(
                f"No existe la hoja configurada: {target.sheet}"
            )
        cell = workbook[target.sheet][target.cell]
        cell.value = value
        if isinstance(value, str):
            cell.data_type = "s"

    @staticmethod
    def _clear_certificate_requirement(workbook: Any) -> None:
        """Leave all certificate fields blank on the generated acta."""
        if CERTIFICATE_SHEET not in workbook.sheetnames:
            raise ExcelGenerationError(
                f"No existe la hoja configurada: {CERTIFICATE_SHEET}"
            )

        sheet = workbook[CERTIFICATE_SHEET]
        sheet[CERTIFICATE_NO_CELL] = None
        sheet[CERTIFICATE_YES_CELL] = None
        sheet[CERTIFICATE_TYPE_CELL] = None
