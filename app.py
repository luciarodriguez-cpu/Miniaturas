from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd
import streamlit as st

from svg import generar_svg_mueble


st.set_page_config(page_title="Miniaturas de muebles", layout="wide")
st.title("Miniaturas de muebles")
st.write("Sube un CSV para generar las miniaturas SVG automáticamente")


# Columnas del nuevo CSV (fuente)
CSV_COL_PRODUIT = "Produit"
CSV_COL_DESIGNATION = "Désignation du produit"
CSV_COL_LARGEUR = "Largeur (mm)"
CSV_COL_HAUTEUR_SANS_PIEDS = "Hauteur (mm) sans pieds"
CSV_COL_PROFONDEUR_SANS_FACADE = "Profondeur (mm) sans façade"
CSV_COL_HAUTEUR_PIEDS = "Ht pieds (mm) 100 en standard"
CSV_COL_VIDE_SANITAIRE = "Vide sanitaire (mm)"
CSV_COL_TYPE_MEUBLE = "Meuble posé (P)/ Suspendu (S)"
CSV_COL_NOMBRE_FACADES = "Nombre de façades"
CSV_COL_DIMENSIONS_FACADES = "Dimension façades (de bas en haut) L * H en mm"
CSV_COL_NOMBRE_ETAGERES_INTERIEURES = "Nombre d'étagères intérieures"
CSV_COL_NOMBRE_PIEDS = "Nombre de pieds"
CSV_COL_NOMBRE_POIGNEES = "Nombre de poignées"
CSV_COL_NOMBRE_PORTES = "Nombre de portes"
CSV_COL_NOMBRE_TIROIRS = "Nombre de tiroirs"
CSV_COL_NOMBRE_BLOCS_COULISSANTS = "Nombre de blocs coulissants"
CSV_COL_NOMBRE_FAUX_TIROIRS_BANDEAU = "Nombre de faux tiroirs ou bandeau"

# Nombres internos normalizados
FIELD_PRODUCTO = "producto"
FIELD_DESIGNACION = "designacion"
FIELD_ANCHO_MM = "ancho_mm"
FIELD_ALTO_MM = "alto_mm"
FIELD_FONDO_MM = "fondo_mm"
FIELD_ALTURA_PATAS_MM = "altura_patas_mm"
FIELD_VIDE_SANITAIRE_MM = "vide_sanitaire_mm"
FIELD_TIPO_MUEBLE = "tipo_mueble"
FIELD_NUM_FACADES = "num_facades"
FIELD_FACADES_DIMENSIONES = "facades_dimensiones"
FIELD_NUM_BALDAS_INTERIORES = "num_baldas_interiores"
FIELD_NUM_PATAS = "num_patas"
FIELD_NUM_TIRADORES = "num_tiradores"
FIELD_NUM_PUERTAS = "num_puertas"
FIELD_NUM_TIROIRS = "num_tiroirs"
FIELD_NUM_BLOCS_COULISSANTS = "num_blocs_coulissants"
FIELD_NUM_FAUX_TIROIRS_BANDEAU = "num_faux_tiroirs_bandeau"

# Campos mínimos para poder dibujar con svg.py
REQUIRED_INTERNAL_FIELDS = [
    FIELD_PRODUCTO,
    FIELD_ANCHO_MM,
    FIELD_ALTO_MM,
    FIELD_FONDO_MM,
    FIELD_TIPO_MUEBLE,
]

MISSING_STRINGS = {"", "na", "n/a", "nan", "none", "null", "<na>"}


def _normalize_column_name(name: Any) -> str:
    normalized = str(name).replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip().lower()
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized


COLUMN_MAPPING = {
    _normalize_column_name(CSV_COL_PRODUIT): FIELD_PRODUCTO,
    _normalize_column_name(CSV_COL_DESIGNATION): FIELD_DESIGNACION,
    _normalize_column_name(CSV_COL_LARGEUR): FIELD_ANCHO_MM,
    _normalize_column_name(CSV_COL_HAUTEUR_SANS_PIEDS): FIELD_ALTO_MM,
    _normalize_column_name(CSV_COL_PROFONDEUR_SANS_FACADE): FIELD_FONDO_MM,
    _normalize_column_name(CSV_COL_HAUTEUR_PIEDS): FIELD_ALTURA_PATAS_MM,
    _normalize_column_name(CSV_COL_VIDE_SANITAIRE): FIELD_VIDE_SANITAIRE_MM,
    _normalize_column_name(CSV_COL_TYPE_MEUBLE): FIELD_TIPO_MUEBLE,
    _normalize_column_name(CSV_COL_NOMBRE_FACADES): FIELD_NUM_FACADES,
    _normalize_column_name(CSV_COL_DIMENSIONS_FACADES): FIELD_FACADES_DIMENSIONES,
    _normalize_column_name(CSV_COL_NOMBRE_ETAGERES_INTERIEURES): FIELD_NUM_BALDAS_INTERIORES,
    _normalize_column_name(CSV_COL_NOMBRE_PIEDS): FIELD_NUM_PATAS,
    _normalize_column_name(CSV_COL_NOMBRE_POIGNEES): FIELD_NUM_TIRADORES,
    _normalize_column_name(CSV_COL_NOMBRE_PORTES): FIELD_NUM_PUERTAS,
    _normalize_column_name(CSV_COL_NOMBRE_TIROIRS): FIELD_NUM_TIROIRS,
    _normalize_column_name(CSV_COL_NOMBRE_BLOCS_COULISSANTS): FIELD_NUM_BLOCS_COULISSANTS,
    _normalize_column_name(CSV_COL_NOMBRE_FAUX_TIROIRS_BANDEAU): FIELD_NUM_FAUX_TIROIRS_BANDEAU,
}

REQUIRED_SOURCE_COLUMNS = list(COLUMN_MAPPING.keys())


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    return str(value).strip().casefold() in MISSING_STRINGS


def _to_non_negative_int(value: Any, default: int = 0) -> int:
    if _is_missing(value):
        return default
    try:
        parsed = int(float(str(value).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _to_non_negative_float(value: Any, default: float = 0.0) -> float:
    if _is_missing(value):
        return default
    try:
        parsed = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default
    return max(0.0, parsed)


def _parse_tipo_mueble(value: Any) -> str:
    if _is_missing(value):
        return "S"
    parsed = str(value).strip().upper()
    return "P" if parsed == "P" else "S"


def _parse_facade_dimensions(value: Any) -> list[dict[str, int]]:
    if _is_missing(value):
        return []

    text = str(value)
    lines = [line.strip() for line in re.split(r"[\n;]+", text) if line.strip()]
    parsed_dimensions: list[dict[str, int]] = []

    for line in lines:
        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*[xX*]\s*(\d+(?:[\.,]\d+)?)", line)
        if not match:
            continue

        try:
            width = int(round(float(match.group(1).replace(",", "."))))
            height = int(round(float(match.group(2).replace(",", "."))))
        except ValueError:
            continue

        if width <= 0 or height <= 0:
            continue

        parsed_dimensions.append({"width_mm": width, "height_mm": height})

    return parsed_dimensions


def _parse_row_to_internal(row: pd.Series) -> dict[str, Any]:
    return {
        FIELD_PRODUCTO: str(row.get(FIELD_PRODUCTO, "")).strip() or "Producto sin nombre",
        FIELD_DESIGNACION: None if _is_missing(row.get(FIELD_DESIGNACION)) else str(row.get(FIELD_DESIGNACION)).strip(),
        FIELD_ANCHO_MM: _to_non_negative_float(row.get(FIELD_ANCHO_MM), default=600.0),
        FIELD_ALTO_MM: _to_non_negative_float(row.get(FIELD_ALTO_MM), default=800.0),
        FIELD_FONDO_MM: _to_non_negative_float(row.get(FIELD_FONDO_MM), default=350.0),
        FIELD_ALTURA_PATAS_MM: _to_non_negative_float(row.get(FIELD_ALTURA_PATAS_MM), default=0.0),
        FIELD_VIDE_SANITAIRE_MM: _to_non_negative_float(row.get(FIELD_VIDE_SANITAIRE_MM), default=0.0),
        FIELD_TIPO_MUEBLE: _parse_tipo_mueble(row.get(FIELD_TIPO_MUEBLE)),
        FIELD_NUM_FACADES: _to_non_negative_int(row.get(FIELD_NUM_FACADES), default=0),
        FIELD_FACADES_DIMENSIONES: _parse_facade_dimensions(row.get(FIELD_FACADES_DIMENSIONES)),
        FIELD_NUM_BALDAS_INTERIORES: _to_non_negative_int(row.get(FIELD_NUM_BALDAS_INTERIORES), default=0),
        FIELD_NUM_PATAS: _to_non_negative_int(row.get(FIELD_NUM_PATAS), default=0),
        FIELD_NUM_TIRADORES: _to_non_negative_int(row.get(FIELD_NUM_TIRADORES), default=0),
        FIELD_NUM_PUERTAS: _to_non_negative_int(row.get(FIELD_NUM_PUERTAS), default=0),
        FIELD_NUM_TIROIRS: _to_non_negative_int(row.get(FIELD_NUM_TIROIRS), default=0),
        FIELD_NUM_BLOCS_COULISSANTS: _to_non_negative_int(row.get(FIELD_NUM_BLOCS_COULISSANTS), default=0),
        FIELD_NUM_FAUX_TIROIRS_BANDEAU: _to_non_negative_int(row.get(FIELD_NUM_FAUX_TIROIRS_BANDEAU), default=0),
    }


def _internal_to_svg_params(mueble: dict[str, Any]) -> dict[str, Any]:
    facade_dimensions_lines = [
        f"{item['width_mm']} * {item['height_mm']}" for item in mueble[FIELD_FACADES_DIMENSIONES]
    ]

    num_cajones_total = mueble[FIELD_NUM_TIROIRS] + mueble[FIELD_NUM_BLOCS_COULISSANTS]

    return {
        "ancho_mm": mueble[FIELD_ANCHO_MM],
        "alto_mm": mueble[FIELD_ALTO_MM],
        "fondo_mm": mueble[FIELD_FONDO_MM],
        "num_baldas": mueble[FIELD_NUM_BALDAS_INTERIORES],
        "num_puertas": mueble[FIELD_NUM_PUERTAS],
        "num_cajones": num_cajones_total,
        "dimensions_portes": "\n".join(facade_dimensions_lines),
        "num_patas": mueble[FIELD_NUM_PATAS],
        "altura_patas": mueble[FIELD_ALTURA_PATAS_MM],
        "tipo_mueble": mueble[FIELD_TIPO_MUEBLE],
    }


uploaded_file = st.file_uploader("CSV de productos", type=["csv"])

if uploaded_file is None:
    st.stop()

try:
    df = pd.read_csv(uploaded_file)
except Exception as exc:
    st.error(f"No se pudo leer el CSV: {exc}")
    st.stop()

normalized_columns = {_normalize_column_name(col): col for col in df.columns}
missing_source_columns = [col for col in REQUIRED_SOURCE_COLUMNS if col not in normalized_columns]
if missing_source_columns:
    missing_labels = [k for k, v in COLUMN_MAPPING.items() if k in missing_source_columns]
    st.error(
        "Faltan columnas obligatorias del nuevo CSV: "
        + ", ".join(missing_labels)
    )
    st.stop()

renamed_columns = {
    normalized_columns[source_name]: internal_name
    for source_name, internal_name in COLUMN_MAPPING.items()
    if source_name in normalized_columns
}
df = df.rename(columns=renamed_columns)

missing_internal_fields = [field for field in REQUIRED_INTERNAL_FIELDS if field not in df.columns]
if missing_internal_fields:
    st.error(
        "No se pudieron mapear columnas obligatorias a campos internos: "
        + ", ".join(missing_internal_fields)
    )
    st.stop()

if df.empty:
    st.info("El CSV no contiene productos.")
    st.stop()

parsed_products = [_parse_row_to_internal(row) for _, row in df.iterrows()]

st.success(f"Productos leídos: {len(parsed_products)}")

generated_cards: list[dict[str, str]] = []
cards_per_row = 3
card_height_px = 390

for start in range(0, len(parsed_products), cards_per_row):
    cols = st.columns(cards_per_row)
    batch = parsed_products[start : start + cards_per_row]

    for col, mueble in zip(cols, batch):
        with col:
            nombre_producto = mueble[FIELD_PRODUCTO]
            try:
                svg_markup = generar_svg_mueble(**_internal_to_svg_params(mueble))
                generated_cards.append({"name": nombre_producto, "svg": svg_markup})

                svg_card_html = f"""
                <div style="
                    height:{card_height_px}px;
                    width:100%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    padding:12px;
                    box-sizing:border-box;
                    overflow:visible;
                ">
                    <div style="
                        width:100%;
                        height:100%;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                    ">
                        {svg_markup}
                    </div>
                </div>
                """
                st.components.v1.html(svg_card_html, height=card_height_px, scrolling=False)
                st.caption(nombre_producto)
            except Exception as exc:
                st.warning(f"No se pudo procesar '{nombre_producto}': {exc}")

if not generated_cards:
    st.error("No se pudo generar ninguna miniatura SVG válida.")
    st.stop()

selected_default = len(generated_cards) - 1
selected_idx = st.selectbox(
    "Mueble para descargar",
    options=range(len(generated_cards)),
    index=selected_default,
    format_func=lambda i: generated_cards[i]["name"],
)
selected_card = generated_cards[selected_idx]
safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", selected_card["name"]).strip("_") or "miniatura"
st.download_button(
    "Descargar SVG",
    data=selected_card["svg"],
    file_name=f"{safe_name}.svg",
    mime="image/svg+xml",
    key="download_single_svg",
)
