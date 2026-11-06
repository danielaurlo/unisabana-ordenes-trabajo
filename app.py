import re
from hashlib import sha256
from pathlib import Path

import streamlit as st

from gestor_contratos.models.orden_trabajo import OrdenTrabajoData
from gestor_contratos.services.combined_pdf_generator import (
    CombinedPDFGenerationError,
    CombinedPDFGenerator,
)
from gestor_contratos.services.excel_generator import (
    ExcelGenerationError,
    ExcelGenerator,
)
from gestor_contratos.services.excel_preview import ExcelPreviewError
from gestor_contratos.services.order_extractor import OrdenTrabajoExtractor
from gestor_contratos.services.pdf_extractor import (
    PDFExtractionError,
    PDFExtractor,
)

APP_PANEL_HEIGHT = 600
PREVIEW_HEIGHT = 500
LOGO_PATH = Path(__file__).parent / "assets" / "branding" / "logo-unisabana.svg"
FIELD_LABELS = {
    "fecha_acta": "fecha del acta",
    "fecha_orden": "fecha de la orden",
    "fecha_vencimiento": "fecha de entrega según la orden",
    "numero_orden": "número de la orden",
    "proveedor.nombre": "nombre del proveedor",
    "proveedor.nit": "NIT",
    "proveedor.direccion": "dirección",
    "proveedor.telefono": "teléfono",
}

st.set_page_config(
    page_title="Gestor de contratos · Universidad de La Sabana",
    page_icon=":material/description:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def initialize_session_state() -> None:
    """Initialize values that must persist between Streamlit reruns."""
    st.session_state.setdefault("uploaded_document_name", None)
    st.session_state.setdefault("uploaded_document_bytes", None)
    st.session_state.setdefault("uploaded_document_fingerprint", None)
    st.session_state.setdefault("extracted_text", None)
    st.session_state.setdefault("extracted_page_count", None)
    st.session_state.setdefault("processing_status", "idle")
    st.session_state.setdefault("processing_error", None)
    st.session_state.setdefault("extracted_order_data", None)
    st.session_state.setdefault("generated_excel_bytes", None)
    st.session_state.setdefault("generated_acta_pdf_bytes", None)
    st.session_state.setdefault("generated_combined_pdf_bytes", None)
    st.session_state.setdefault("pdf_generation_error", None)

    stored_order = st.session_state.extracted_order_data
    if stored_order is not None and not hasattr(
        stored_order, "requiere_certificado"
    ):
        stored_values = stored_order.model_dump()
        stored_values.setdefault("requiere_certificado", False)
        stored_values.setdefault("tipo_certificado", None)
        st.session_state.extracted_order_data = (
            OrdenTrabajoData.model_validate(stored_values)
        )


def reset_generated_documents() -> None:
    """Clear generated files when the source document changes."""
    st.session_state.generated_excel_bytes = None
    st.session_state.generated_acta_pdf_bytes = None
    st.session_state.generated_combined_pdf_bytes = None
    st.session_state.pdf_generation_error = None


def generate_pdf_documents(excel_bytes: bytes) -> None:
    """Convert the generated Excel and append its acta to the source PDF."""
    st.session_state.generated_acta_pdf_bytes = None
    st.session_state.generated_combined_pdf_bytes = None
    st.session_state.pdf_generation_error = None
    source_pdf = st.session_state.uploaded_document_bytes
    if source_pdf is None:
        st.session_state.pdf_generation_error = (
            "No se encontró el PDF de la orden para generar el documento final."
        )
        return

    try:
        result = CombinedPDFGenerator().generate(source_pdf, excel_bytes)
    except (ExcelPreviewError, CombinedPDFGenerationError) as error:
        st.session_state.pdf_generation_error = str(error)
    else:
        st.session_state.generated_acta_pdf_bytes = result.acta_pdf_bytes
        st.session_state.generated_combined_pdf_bytes = result.combined_pdf_bytes


def render_page_header() -> None:
    """Render the institutional application header."""
    with st.container(horizontal=True, vertical_alignment="center"):
        st.image(str(LOGO_PATH), width=202, alt="Universidad de La Sabana")
    st.caption(
        "Universidad de La Sabana · Procesamiento de órdenes de trabajo SIGA"
    )


def render_document_upload(*, compact: bool = False) -> bool:
    """Render the SIGA document upload section."""
    if not compact:
        st.subheader("Documento fuente", icon=":material/upload_file:")
        st.caption("Selecciona una orden de trabajo en formato PDF para iniciar.")
    else:
        st.caption(
            "Puedes reemplazar el archivo actual seleccionando otra orden en PDF."
        )

    uploaded_file = st.file_uploader(
        "Orden de trabajo" if compact else "Archivo PDF",
        type=["pdf"],
        key="siga_document",
        help="Selecciona una orden diferente para reemplazar el archivo actual."
        if compact
        else "Solo se permiten archivos PDF.",
    )

    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        fingerprint = sha256(uploaded_bytes).hexdigest()
        if fingerprint != st.session_state.uploaded_document_fingerprint:
            st.session_state.extracted_text = None
            st.session_state.extracted_page_count = None
            st.session_state.extracted_order_data = None
            reset_generated_documents()
            st.session_state.processing_status = "idle"
            st.session_state.processing_error = None
        st.session_state.uploaded_document_name = uploaded_file.name
        st.session_state.uploaded_document_bytes = uploaded_bytes
        st.session_state.uploaded_document_fingerprint = fingerprint
    else:
        # Cloud uploads can briefly report None while replacing a file. Keep
        # the current document until the replacement has arrived completely.
        if compact and st.session_state.uploaded_document_bytes is not None:
            return True
        st.session_state.uploaded_document_name = None
        st.session_state.uploaded_document_bytes = None
        st.session_state.uploaded_document_fingerprint = None
        st.session_state.extracted_text = None
        st.session_state.extracted_page_count = None
        st.session_state.extracted_order_data = None
        reset_generated_documents()
        st.session_state.processing_status = "idle"
        st.session_state.processing_error = None
    return uploaded_file is not None


def render_processing_action() -> None:
    """Render the processing action without duplicate manual fields."""
    st.markdown("**Procesar documento**")
    render_document_upload(compact=True)
    submitted = st.button(
        "Procesar documento",
        type="primary",
        icon=":material/play_arrow:",
        disabled=st.session_state.uploaded_document_bytes is None,
        width="stretch",
    )

    if submitted:
        pdf_bytes = st.session_state.uploaded_document_bytes
        if pdf_bytes is None:
            st.session_state.processing_status = "error"
            st.session_state.processing_error = (
                "Cargue un documento SIGA antes de procesarlo."
            )
            st.warning(
                "Cargue un documento SIGA antes de procesarlo.",
                icon=":material/upload_file:",
            )
        else:
            try:
                result = PDFExtractor().extract(pdf_bytes)
                order_data = OrdenTrabajoExtractor().extract(pdf_bytes)
            except (PDFExtractionError, ExcelGenerationError) as error:
                st.session_state.extracted_text = None
                st.session_state.extracted_page_count = None
                st.session_state.extracted_order_data = None
                reset_generated_documents()
                st.session_state.processing_status = "error"
                st.session_state.processing_error = str(error)
                st.toast(
                    f"No fue posible procesar el documento: {error}",
                    icon=":material/error:",
                    duration="long",
                )
            else:
                st.session_state.extracted_text = result.text
                st.session_state.extracted_page_count = result.page_count
                st.session_state.extracted_order_data = order_data
                reset_generated_documents()
                if not order_data.campos_ambiguos:
                    try:
                        st.session_state.generated_excel_bytes = (
                            ExcelGenerator().generate(order_data)
                        )
                    except ExcelGenerationError as error:
                        st.session_state.processing_error = str(error)
                st.session_state.processing_status = "success"
                if st.session_state.generated_excel_bytes is not None:
                    generate_pdf_documents(
                        st.session_state.generated_excel_bytes
                    )
                    st.session_state.processing_error = None
                st.toast(
                    "Documento procesado",
                    icon=":material/check_circle:",
                )

    if st.session_state.processing_status == "error":
        st.error(
            st.session_state.processing_error,
            icon=":material/error:",
        )
    if st.session_state.pdf_generation_error:
        st.warning(
            st.session_state.pdf_generation_error,
            icon=":material/picture_as_pdf:",
        )


def render_extracted_editor() -> None:
    """Render extracted values as editable fields."""
    order_data = st.session_state.extracted_order_data
    if order_data is None:
        st.info(
            "Procesa un PDF para revisar y corregir sus datos.",
            icon=":material/edit_document:",
        )
        return

    st.caption("Corrige cualquier valor y guarda los cambios para actualizar el acta.")
    if order_data.campos_faltantes:
        st.warning(
            "No se encontraron: "
            + _friendly_field_list(order_data.campos_faltantes)
            + ". Puedes completarlos o continuar con esos campos vacíos.",
            title="Faltan algunos datos",
            icon=":material/warning:",
        )
    if order_data.campos_ambiguos:
        st.warning(
            "Revisa: " + _friendly_field_list(order_data.campos_ambiguos) + ".",
            title="Hay datos por confirmar",
            icon=":material/priority_high:",
        )
    form_key = f"edit_order_{st.session_state.uploaded_document_name}"
    provider = order_data.proveedor

    with st.form(form_key, border=False):
        st.markdown("**Proveedor**")
        row = st.columns(2)
        nombre = row[0].text_input("Nombre", value=provider.nombre or "")
        nit = row[1].text_input("NIT", value=provider.nit or "")
        row = st.columns(2)
        direccion = row[0].text_input("Dirección", value=provider.direccion or "")
        telefono = row[1].text_input("Teléfono", value=provider.telefono or "")

        st.markdown("**Orden de trabajo**")
        row = st.columns(2)
        numero_orden = row[0].text_input(
            "Número de orden", value=order_data.numero_orden or ""
        )
        fecha_orden = row[1].date_input(
            "Fecha de orden", value=order_data.fecha_orden
        )
        row = st.columns(2)
        fecha_vencimiento = row[0].date_input(
            "Fecha de entrega según la orden",
            value=order_data.fecha_vencimiento,
        )
        fecha_acta = row[1].date_input(
            "Fecha del acta", value=order_data.fecha_acta
        )

        save = st.form_submit_button(
            "Guardar cambios y actualizar acta",
            type="primary",
            icon=":material/save:",
            width="stretch",
        )

    if save:
        try:
            updated_data = _build_edited_order_data(
                order_data,
                nombre=nombre,
                nit=nit,
                direccion=direccion,
                telefono=telefono,
                numero_orden=numero_orden,
                fecha_orden=fecha_orden,
                fecha_acta=fecha_acta,
                fecha_vencimiento=fecha_vencimiento,
            )
            excel_bytes = ExcelGenerator().generate(updated_data)
        except (ValueError, ExcelGenerationError) as error:
            st.toast(
                f"No se pudieron guardar los cambios: {error}",
                icon=":material/error:",
                duration="long",
            )
        else:
            st.session_state.extracted_order_data = updated_data
            st.session_state.generated_excel_bytes = excel_bytes
            generate_pdf_documents(excel_bytes)
            st.session_state.processing_status = "success"
            if updated_data.campos_faltantes:
                st.toast(
                    "Guardado con campos vacíos: "
                    + _friendly_field_list(updated_data.campos_faltantes),
                    icon=":material/warning:",
                    duration="long",
                )
            else:
                st.toast("Cambios guardados", icon=":material/check_circle:")


def _build_edited_order_data(
    order_data: OrdenTrabajoData, **values
) -> OrdenTrabajoData:
    """Build a validated order model from the editor values."""
    provider = order_data.proveedor.model_copy(
        update={
            "nombre": values.pop("nombre").strip() or None,
            "nit": values.pop("nit").strip() or None,
            "direccion": values.pop("direccion").strip() or None,
            "telefono": values.pop("telefono").strip() or None,
        }
    )
    values["proveedor"] = provider
    required_fields = {
        "proveedor.nombre": provider.nombre,
        "proveedor.nit": provider.nit,
        "proveedor.direccion": provider.direccion,
        "proveedor.telefono": provider.telefono,
        "numero_orden": values["numero_orden"],
        "fecha_orden": values["fecha_orden"],
        "fecha_vencimiento": values["fecha_vencimiento"],
        "fecha_acta": values["fecha_acta"],
    }
    missing_fields = [
        field for field, value in required_fields.items() if not value
    ]
    values["requiere_certificado"] = False
    values["tipo_certificado"] = None
    if (
        values["fecha_acta"] is not None
        and values["fecha_orden"] is not None
        and values["fecha_acta"] < values["fecha_orden"]
    ):
        raise ValueError(
            "La fecha del acta no puede ser anterior a la fecha de la orden."
        )
    values["campos_faltantes"] = missing_fields
    values["campos_ambiguos"] = []
    return OrdenTrabajoData.model_validate(order_data.model_dump() | values)


def _friendly_field_list(fields: list[str]) -> str:
    """Return unique field names written for application users."""
    labels = list(
        dict.fromkeys(FIELD_LABELS.get(field, field) for field in fields)
    )
    if len(labels) < 2:
        return "".join(labels)
    return ", ".join(labels[:-1]) + " y " + labels[-1]


def render_previews() -> None:
    """Render one focused preview at a time in a compact workspace."""
    st.subheader("Área de trabajo", icon=":material/preview:")
    view = st.segmented_control(
        "Vista",
        options=["Documento", "Revisar datos", "Excel"],
        default="Documento",
        key="preview_view",
        label_visibility="collapsed",
        width="stretch",
    )

    if view == "Documento":
        pdf_bytes = st.session_state.uploaded_document_bytes
        if pdf_bytes is None:
            st.info(
                "La previsualización aparecerá cuando cargues un PDF.",
                icon=":material/picture_as_pdf:",
            )
        else:
            st.pdf(
                pdf_bytes,
                height=PREVIEW_HEIGHT,
                alt="Documento PDF SIGA cargado",
            )

    elif view == "Revisar datos":
        render_extracted_editor()

    elif view == "Excel":
        excel_bytes = st.session_state.generated_excel_bytes
        if excel_bytes is None:
            if st.session_state.extracted_order_data is None:
                st.info(
                    "Procesa el PDF para generar y previsualizar el Excel.",
                    icon=":material/table_view:",
                )
            else:
                st.info(
                    "Corrige los datos extraídos y guárdalos para generar el Excel.",
                    icon=":material/edit_document:",
                )
        else:
            with st.container(horizontal=True, vertical_alignment="center"):
                combined_pdf = st.session_state.generated_combined_pdf_bytes
                st.download_button(
                    "Descargar orden y acta",
                    data=combined_pdf or b"",
                    file_name=_pdf_download_name(),
                    mime="application/pdf",
                    icon=":material/picture_as_pdf:",
                    type="primary",
                    disabled=combined_pdf is None,
                    on_click="ignore",
                    width="content",
                )
                st.download_button(
                    "Descargar Excel",
                    data=excel_bytes,
                    file_name=_excel_download_name(),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    icon=":material/download:",
                    on_click="ignore",
                    width="content",
                )
            if st.session_state.pdf_generation_error:
                st.warning(
                    st.session_state.pdf_generation_error,
                    icon=":material/picture_as_pdf:",
                )
            render_excel_preview(st.session_state.generated_acta_pdf_bytes)


def render_excel_preview(acta_pdf_bytes: bytes | None) -> None:
    """Render the acta PDF already generated from the workbook."""
    if acta_pdf_bytes is None:
        return
    st.pdf(
        acta_pdf_bytes,
        height=PREVIEW_HEIGHT,
        alt="Vista previa del acta diligenciada",
    )


def _excel_download_name() -> str:
    """Build a useful institutional filename for the generated workbook."""
    order_data = st.session_state.extracted_order_data
    order_number = order_data.numero_orden if order_data else None
    safe_number = re.sub(r"[^A-Za-z0-9_-]", "", order_number or "")
    prefix = f"OT_{safe_number}" if safe_number else "OT"
    return f"{prefix}_Acta_Entrega.xlsx"


def _pdf_download_name() -> str:
    """Build a useful filename for the combined order and acta PDF."""
    order_data = st.session_state.extracted_order_data
    order_number = order_data.numero_orden if order_data else None
    safe_number = re.sub(r"[^A-Za-z0-9_-]", "", order_number or "")
    prefix = f"OT_{safe_number}" if safe_number else "OT"
    return f"{prefix}_Orden_y_Acta.pdf"


initialize_session_state()
render_page_header()

if st.session_state.uploaded_document_bytes is None:
    with st.container(border=True):
        document_uploaded = render_document_upload()
    if document_uploaded:
        st.rerun()
    st.stop()

left_column, right_column = st.columns(
    [0.85, 1.15], gap="large", vertical_alignment="top"
)

with left_column:
    with st.container(height=APP_PANEL_HEIGHT, border=True):
        render_processing_action()

with right_column:
    with st.container(height=APP_PANEL_HEIGHT, border=True):
        render_previews()
