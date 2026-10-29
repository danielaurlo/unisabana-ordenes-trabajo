"""Render generated Excel workbooks for visual preview."""

import shutil
import subprocess
import tempfile
from pathlib import Path


class ExcelPreviewError(Exception):
    """Raised when an Excel workbook cannot be rendered for preview."""


class ExcelPreviewRenderer:
    """Convert an in-memory workbook to a temporary PDF using LibreOffice."""

    def __init__(self, office_command: str | None = None) -> None:
        self.office_command = office_command or self._find_office_command()

    @staticmethod
    def _find_office_command() -> str | None:
        candidates = (
            shutil.which("soffice"),
            shutil.which("libreoffice"),
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        )
        return next((candidate for candidate in candidates if candidate), None)

    def render(self, excel_bytes: bytes) -> bytes:
        """Return a PDF preview without persisting files in the project."""
        if self.office_command is None:
            raise ExcelPreviewError(
                "No se encontró LibreOffice. Instálelo para previsualizar el Excel."
            )

        with tempfile.TemporaryDirectory(
            prefix="gestor_contratos_preview_"
        ) as directory:
            temporary_dir = Path(directory)
            source = temporary_dir / "acta_entrega_preview.xlsx"
            source.write_bytes(excel_bytes)
            try:
                subprocess.run(
                    [
                        self.office_command,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(temporary_dir),
                        str(source),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ExcelPreviewError(
                    "No fue posible convertir el Excel para previsualización."
                ) from exc

            pdf_path = source.with_suffix(".pdf")
            if not pdf_path.is_file():
                raise ExcelPreviewError(
                    "LibreOffice no generó el PDF de previsualización."
                )
            return pdf_path.read_bytes()
