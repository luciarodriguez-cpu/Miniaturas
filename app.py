from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st

from svg import generar_svg_mueble


st.set_page_config(page_title="Miniaturas de muebles", layout="wide")
st.title("Miniaturas de muebles")
st.write("Sube un CSV para generar las miniaturas SVG automáticamente")


# Columnas por índice (fuente)
COL_PRODUCTO = 0
COL_DESIGNACION = 1
COL_ANCHO = 2
COL_ALTO = 3
COL_FONDO = 4
COL_ALTURA_PATAS = 5
COL_VIDE_SANITAIRE = 6
COL_TIPO = 7
COL_NUM_FACADES = 8
COL_DIM_FACADES = 9
COL_NUM_BALDAS = 10
COL_NUM_PATAS = 11
COL_NUM_TIRADORES = 12
COL_NUM_PUERTAS = 13
COL_NUM_TIROIRS = 14
COL_NUM_BLOCS = 15
COL_NUM_FAUX = 16

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


def _value_at(row: pd.Series, idx: int, default: Any = None) -> Any:
    try:
        return row.iloc[idx]
    except IndexError:
        return default


def _parse_row_to_internal(row: pd.Series) -> dict[str, Any]:
    producto = _value_at(row, COL_PRODUCTO, default="")
    designacion = _value_at(row, COL_DESIGNACION)

    return {
        FIELD_PRODUCTO: str(producto).strip() or "Producto sin nombre",
        FIELD_DESIGNACION: None if _is_missing(designacion) else str(designacion).strip(),
        FIELD_ANCHO_MM: _to_non_negative_float(_value_at(row, COL_ANCHO), default=600.0),
        FIELD_ALTO_MM: _to_non_negative_float(_value_at(row, COL_ALTO), default=800.0),
        FIELD_FONDO_MM: _to_non_negative_float(_value_at(row, COL_FONDO), default=350.0),
        FIELD_ALTURA_PATAS_MM: _to_non_negative_float(_value_at(row, COL_ALTURA_PATAS), default=0.0),
        FIELD_VIDE_SANITAIRE_MM: _to_non_negative_float(_value_at(row, COL_VIDE_SANITAIRE), default=0.0),
        FIELD_TIPO_MUEBLE: _parse_tipo_mueble(_value_at(row, COL_TIPO)),
        FIELD_NUM_FACADES: _to_non_negative_int(_value_at(row, COL_NUM_FACADES), default=0),
        FIELD_FACADES_DIMENSIONES: _parse_facade_dimensions(_value_at(row, COL_DIM_FACADES)),
        FIELD_NUM_BALDAS_INTERIORES: _to_non_negative_int(_value_at(row, COL_NUM_BALDAS), default=0),
        FIELD_NUM_PATAS: _to_non_negative_int(_value_at(row, COL_NUM_PATAS), default=0),
        FIELD_NUM_TIRADORES: _to_non_negative_int(_value_at(row, COL_NUM_TIRADORES), default=0),
        FIELD_NUM_PUERTAS: _to_non_negative_int(_value_at(row, COL_NUM_PUERTAS), default=0),
        FIELD_NUM_TIROIRS: _to_non_negative_int(_value_at(row, COL_NUM_TIROIRS), default=0),
        FIELD_NUM_BLOCS_COULISSANTS: _to_non_negative_int(_value_at(row, COL_NUM_BLOCS), default=0),
        FIELD_NUM_FAUX_TIROIRS_BANDEAU: _to_non_negative_int(_value_at(row, COL_NUM_FAUX), default=0),
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
    df = pd.read_csv(uploaded_file, header=None, skiprows=1, sep=None, engine="python")
except Exception as exc:
    st.error(f"No se pudo leer el CSV: {exc}")
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
