from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st

from svg import generar_svg_mueble


st.set_page_config(page_title="Miniaturas de muebles", layout="wide")
st.title("Miniaturas de muebles")
st.write("Sube un CSV para generar las miniaturas SVG automáticamente")


COLUMN_PRODUCTO = "producto"
COLUMN_ANCHO = "ancho_mm"
COLUMN_ALTO = "alto_mm"
COLUMN_FONDO = "fondo_mm"
COLUMN_ALTURA_PATAS = "altura_patas_mm"
COLUMN_TIPO = "tipo_mueble"
COLUMN_NUM_PUERTAS = "num_puertas"
COLUMN_DIMENSIONES = "dimensions_portes"
COLUMN_NUM_BALDAS = "num_baldas"
COLUMN_NUM_PATAS = "num_patas"
COLUMN_NUM_CAJONES = "num_cajones"

COLUMN_MAPPING = {
    "Produit (nom de l'article)": COLUMN_PRODUCTO,
    "Largeur (mm)": COLUMN_ANCHO,
    "hauteur (mm) sans pieds": COLUMN_ALTO,
    "Profondeur (mm) sans façade": COLUMN_FONDO,
    "Ht pieds (mm) 100 en standard": COLUMN_ALTURA_PATAS,
    "Meuble posé (P)/ Suspendu (S)": COLUMN_TIPO,
    "Nombre de portes": COLUMN_NUM_PUERTAS,
    "Dimensions portes (de bas en haut) L * H en mm": COLUMN_DIMENSIONES,
    "Nombre d'étagères": COLUMN_NUM_BALDAS,
    "Nombre de pieds": COLUMN_NUM_PATAS,
    "Nombre de tiroirs": COLUMN_NUM_CAJONES,
}

REQUIRED_COLUMNS = [COLUMN_PRODUCTO, COLUMN_ANCHO, COLUMN_ALTO, COLUMN_FONDO]


def _normalize_column_name(name: Any) -> str:
    normalized = str(name).replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _to_non_negative_int(value: Any, default: int = 0) -> int:
    if value is None or pd.isna(value):
        return default
    try:
        return max(0, int(float(str(value).strip().replace(",", "."))))
    except (TypeError, ValueError):
        return default


def _to_positive_float(value: Any, default: float) -> float:
    if value is None or pd.isna(value):
        return default
    try:
        parsed = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _parse_tipo_mueble(value: Any) -> str:
    tipo = str(value or "").strip().upper()
    return "P" if tipo == "P" else "S"


def _parse_dimensions_portes(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""

    text = str(value).strip()
    if not text:
        return ""

    parts = [p.strip() for p in re.split(r"[\n;,]+", text) if p.strip()]
    normalized: list[str] = []

    for item in parts:
        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*[xX*]\s*(\d+(?:[\.,]\d+)?)", item)
        if match:
            width = float(match.group(1).replace(",", "."))
            height = float(match.group(2).replace(",", "."))
        else:
            nums = re.findall(r"\d+(?:[\.,]\d+)?", item)
            if len(nums) < 2:
                continue
            width = float(nums[0].replace(",", "."))
            height = float(nums[-1].replace(",", "."))

        height_rounded = int(((height + 5) // 10) * 10)
        normalized.append(f"{int(round(width))} * {height_rounded}")

    return "\n".join(normalized)


def _row_to_svg_params(row: pd.Series) -> dict[str, Any]:
    return {
        "ancho_mm": _to_positive_float(row.get(COLUMN_ANCHO), default=600.0),
        "alto_mm": _to_positive_float(row.get(COLUMN_ALTO), default=800.0),
        "fondo_mm": _to_positive_float(row.get(COLUMN_FONDO), default=350.0),
        "num_baldas": _to_non_negative_int(row.get(COLUMN_NUM_BALDAS), default=0),
        "num_puertas": _to_non_negative_int(row.get(COLUMN_NUM_PUERTAS), default=0),
        "num_cajones": _to_non_negative_int(row.get(COLUMN_NUM_CAJONES), default=0),
        "dimensions_portes": _parse_dimensions_portes(row.get(COLUMN_DIMENSIONES)),
        "num_patas": _to_non_negative_int(row.get(COLUMN_NUM_PATAS), default=0),
        "altura_patas": _to_positive_float(row.get(COLUMN_ALTURA_PATAS), default=0.0),
        "tipo_mueble": _parse_tipo_mueble(row.get(COLUMN_TIPO, "S")),
    }


uploaded_file = st.file_uploader("CSV de productos", type=["csv"])

if uploaded_file is None:
    st.stop()

try:
    df = pd.read_csv(uploaded_file)
except Exception as exc:
    st.error(f"No se pudo leer el CSV: {exc}")
    st.stop()

df = df.rename(columns=lambda col: _normalize_column_name(col))

missing_original_columns = [col for col in COLUMN_MAPPING if col not in df.columns]
if missing_original_columns:
    st.error(
        "Faltan columnas obligatorias en el CSV tras normalizar encabezados: "
        + ", ".join(missing_original_columns)
    )
    st.stop()

df = df.rename(columns=COLUMN_MAPPING)

missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
if missing_columns:
    st.error(
        "Faltan columnas obligatorias en el CSV tras mapear encabezados: "
        + ", ".join(missing_columns)
    )
    st.stop()

if df.empty:
    st.info("El CSV no contiene productos.")
    st.stop()

st.success(f"Productos leídos: {len(df)}")

generated_cards: list[dict[str, str]] = []
cards_per_row = 3
card_height_px = 390

for start in range(0, len(df), cards_per_row):
    cols = st.columns(cards_per_row)
    batch = df.iloc[start : start + cards_per_row]

    for col, (_, row) in zip(cols, batch.iterrows()):
        with col:
            nombre_producto = str(row.get(COLUMN_PRODUCTO, "Producto sin nombre")).strip() or "Producto sin nombre"
            try:
                svg_markup = generar_svg_mueble(**_row_to_svg_params(row))
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
