# Gestor de Contratos Universitarios

Sistema universitario de automatización de documentos de contratación.

## Requisitos

- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Instalación

```bash
uv sync
```

## Ejecutar la aplicación

```bash
uv run streamlit run app.py
```

## Verificaciones

```bash
uv run pytest
uv run ruff check .
```

## Documentos y privacidad

La plantilla pública `assets/plantilla/acta_entrega_vacia.xlsx` contiene solo
el formulario vacío. No incluye hojas ocultas, imágenes incrustadas, comentarios
ni datos de proveedores. Las pruebas crean documentos ficticios en memoria.

Los documentos reales y los resultados deben mantenerse fuera del repositorio
(por ejemplo, en `private/`, que está ignorado por Git). No agregues archivos
confidenciales con `git add -f`. Revisa los cambios antes de cada publicación.

La aplicación procesa los documentos en el servidor y LibreOffice utiliza
archivos temporales durante la conversión. Para un despliegue con datos reales,
configura acceso restringido en el alojamiento.
