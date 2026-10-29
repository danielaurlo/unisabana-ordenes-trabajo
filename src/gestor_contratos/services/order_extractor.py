"""Extract normalized work-order data from SIGA PDFs."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

import pymupdf

from gestor_contratos.config import extraction_patterns as patterns
from gestor_contratos.models.orden_trabajo import (
    DetalleOrden,
    OrdenTrabajoData,
    ProveedorData,
)
from gestor_contratos.services.pdf_extractor import PDFExtractor


class OrdenTrabajoExtractor:
    """Extract fields from the order pages of a SIGA PDF."""

    def __init__(self, pdf_extractor: PDFExtractor | None = None) -> None:
        self.pdf_extractor = pdf_extractor or PDFExtractor()

    def extract(self, pdf_bytes: bytes) -> OrdenTrabajoData:
        """Extract order data while preserving missing and ambiguous fields."""
        self.pdf_extractor.extract(pdf_bytes)

        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            pages = [page.get_text("text") for page in document]
            detail_words = (
                document[2].get_text("words") if document.page_count >= 3 else []
            )
            acta_words = (
                document[-1].get_text("words") if document.page_count >= 1 else []
            )

        order_text = pages[0] if pages else ""
        acta_text = pages[-1] if len(pages) > 1 else ""
        missing: list[str] = []
        ambiguous: list[str] = []

        fecha_orden = self._date_field(
            order_text,
            patterns.ORDER_DATE,
            "fecha_orden",
            missing,
            ambiguous,
        ) or self._date_field(
            acta_text,
            patterns.ACTA_ORDER_DATE,
            "fecha_orden",
            missing,
            ambiguous,
        )
        numero_original = self._field(
            order_text,
            patterns.ORDER_NUMBER,
            "numero_orden",
            missing,
            ambiguous,
        ) or self._field(
            acta_text,
            patterns.ACTA_ORDER_NUMBER,
            "numero_orden",
            missing,
            ambiguous,
        )
        numero_orden = self._normalize_order_number(numero_original)
        fecha_acta = self._extract_acta_date(acta_words, missing, ambiguous)

        proveedor = ProveedorData(
            nombre=self._field(
                order_text,
                patterns.PROVIDER_NAME,
                "proveedor.nombre",
                missing,
                ambiguous,
            )
            or self._field(
                acta_text,
                patterns.PROVIDER_NAME,
                "proveedor.nombre",
                missing,
                ambiguous,
            ),
            nit=self._normalize_nit(
                self._field(
                    order_text,
                    patterns.PROVIDER_NIT,
                    "proveedor.nit",
                    missing,
                    ambiguous,
                )
                or self._field(
                    acta_text,
                    patterns.PROVIDER_NIT,
                    "proveedor.nit",
                    missing,
                    ambiguous,
                )
            ),
            direccion=self._field(
                order_text,
                patterns.PROVIDER_ADDRESS,
                "proveedor.direccion",
                missing,
                ambiguous,
            ),
            persona_contacto=self._field(
                order_text,
                patterns.CONTACT,
                "proveedor.persona_contacto",
                missing,
                ambiguous,
            ),
            ciudad=self._field(
                order_text, patterns.CITY, "proveedor.ciudad", missing, ambiguous
            ),
            telefono=self._field(
                order_text, patterns.PHONE, "proveedor.telefono", missing, ambiguous
            ),
            celular=self._optional_field(order_text, patterns.MOBILE),
            correo=self._field(
                order_text, patterns.EMAIL, "proveedor.correo", missing, ambiguous
            ),
        )

        result = OrdenTrabajoData(
            fecha_orden=fecha_orden,
            fecha_acta=fecha_acta,
            numero_orden=numero_orden,
            numero_orden_original=numero_original,
            tipo_orden=self._optional_field(order_text, patterns.ORDER_TYPE),
            objeto=self._field(
                order_text, patterns.OBJECT, "objeto", missing, ambiguous
            ),
            sede=self._field(order_text, patterns.LOCATION, "sede", missing, ambiguous),
            fecha_inicio=self._date_field(
                order_text,
                patterns.START_DATE,
                "fecha_inicio",
                missing,
                ambiguous,
            ),
            fecha_vencimiento=self._date_field(
                order_text,
                patterns.END_DATE,
                "fecha_vencimiento",
                missing,
                ambiguous,
            ),
            proveedor=proveedor,
            detalles=self._extract_details(detail_words),
            valor_total_letras=self._optional_field(
                pages[2] if len(pages) >= 3 else "", patterns.TOTAL_LETTERS
            ),
            total=self._parse_decimal(
                self._optional_field(
                    pages[2] if len(pages) >= 3 else "", patterns.TOTAL
                )
            ),
            campos_faltantes=missing,
            campos_ambiguos=ambiguous,
        )
        return result

    @staticmethod
    def _field(
        text: str,
        pattern: str,
        field_name: str,
        missing: list[str],
        ambiguous: list[str],
    ) -> str | None:
        matches = [
            OrdenTrabajoExtractor._normalize_text(match.group("value"))
            for match in re.finditer(pattern, text)
            if OrdenTrabajoExtractor._normalize_text(match.group("value"))
        ]
        unique_matches = list(dict.fromkeys(matches))
        if not unique_matches:
            missing.append(field_name)
            return None
        if len(unique_matches) > 1:
            ambiguous.append(field_name)
            return None
        return unique_matches[0]

    @staticmethod
    def _optional_field(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        if match is None:
            return None
        value = OrdenTrabajoExtractor._normalize_text(match.group("value"))
        return value or None

    @classmethod
    def _date_field(
        cls,
        text: str,
        pattern: str,
        field_name: str,
        missing: list[str],
        ambiguous: list[str],
    ) -> date | None:
        value = cls._field(text, pattern, field_name, missing, ambiguous)
        if value is None:
            return None
        try:
            return cls._parse_date(value)
        except ValueError:
            ambiguous.append(field_name)
            return None

    @staticmethod
    def _parse_date(value: str) -> date:
        parts = [int(part) for part in re.findall(r"\d+", value)]
        if len(parts) != 3:
            raise ValueError("Formato de fecha no reconocido")
        first, second, year = parts
        if first > 12:
            day, month = first, second
        elif second > 12:
            month, day = first, second
        else:
            day, month = first, second
        return date(year, month, day)

    @classmethod
    def _extract_acta_date(
        cls,
        words: list[tuple],
        missing: list[str],
        ambiguous: list[str],
    ) -> date | None:
        """Extract the date printed below the DD/MM/AAAA markers on the acta."""
        date_marker = next(
            (
                word
                for word in words
                if word[4].strip().upper() == "DD" and 50 <= word[1] <= 120
            ),
            None,
        )
        if date_marker is None:
            missing.append("fecha_acta")
            return None

        candidate_numbers = sorted(
            (
                word
                for word in words
                if date_marker[1] < word[1] <= date_marker[1] + 30
                and date_marker[0] - 20 <= word[0] <= date_marker[0] + 110
                and re.fullmatch(r"\d{1,4}", word[4].strip())
            ),
            key=lambda word: word[0],
        )
        values = [int(word[4]) for word in candidate_numbers[:3]]
        if len(values) != 3:
            missing.append("fecha_acta")
            return None
        try:
            return date(values[2], values[1], values[0])
        except ValueError:
            ambiguous.append("fecha_acta")
            return None

    @staticmethod
    def _normalize_order_number(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lstrip("0")
        return normalized or "0"

    @staticmethod
    def _normalize_nit(value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(r"\D", "", value) or None

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _extract_details(cls, words: list[tuple]) -> list[DetalleOrden]:
        if not words:
            return []

        numeric_rows = [
            word
            for word in words
            if 290 <= word[1] <= 330 and word[0] >= 260
        ]
        if not numeric_rows:
            return []

        row_positions = sorted({round(word[1], 1) for word in numeric_rows})
        details = []
        for row_y in row_positions:
            row_words = [word for word in words if abs(word[1] - row_y) <= 1.5]
            item_word = next((word for word in row_words if word[0] < 100), None)
            if item_word is None:
                continue
            description_words = [
                word
                for word in words
                if 100 <= word[0] < 260 and row_y - 20 <= word[1] <= row_y + 20
            ]
            description = cls._normalize_text(
                " ".join(word[4] for word in description_words)
            )
            unit = next((word[4] for word in row_words if 260 <= word[0] < 320), None)
            quantity = next(
                (word[4] for word in row_words if 320 <= word[0] < 400), None
            )
            unit_value = next(
                (word[4] for word in row_words if 400 <= word[0] < 500), None
            )
            total = next((word[4] for word in row_words if word[0] >= 500), None)
            details.append(
                DetalleOrden(
                    numero=int(item_word[4]),
                    descripcion=description or None,
                    unidad=cls._normalize_text(unit) if unit else None,
                    cantidad=cls._parse_decimal(quantity),
                    valor_unitario=cls._parse_decimal(unit_value),
                    valor_total=cls._parse_decimal(total),
                )
            )
        return details

    @staticmethod
    def _parse_decimal(value: str | None) -> Decimal | None:
        if value is None:
            return None
        normalized = value.replace(".", "").replace(",", ".").strip()
        try:
            return Decimal(normalized)
        except InvalidOperation:
            return None
