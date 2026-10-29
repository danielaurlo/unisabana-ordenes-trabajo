from pathlib import Path
from subprocess import CompletedProcess

from gestor_contratos.services.excel_preview import ExcelPreviewRenderer


def test_uses_an_isolated_libreoffice_profile(monkeypatch) -> None:
    captured_command: list[str] = []

    def fake_run(command, **kwargs):
        captured_command.extend(command)
        source = Path(command[-1])
        source.with_suffix(".pdf").write_bytes(b"generated pdf")
        return CompletedProcess(command, 0)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = ExcelPreviewRenderer(office_command="soffice").render(b"excel")

    assert result == b"generated pdf"
    assert captured_command[1].startswith(
        "-env:UserInstallation=file://"
    )
