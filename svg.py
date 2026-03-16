from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any
from uuid import uuid4


ESPESOR_ESTANDAR_MM = 19.0


@dataclass
class MuebleSVGInput:
    ancho_mm: float
    alto_mm: float
    fondo_mm: float
    num_baldas: int = 0
    num_puertas: int = 0
    num_cajones: int = 0
    dimensions_portes: str | list[str] | None = None
    num_patas: int = 0
    altura_patas: float = 0.0
    tipo_mueble: str = "S"
    espesor_mm: float = ESPESOR_ESTANDAR_MM
    color_hex: str = "#FFFFFF"


def generar_svg_mueble(
    ancho_mm: float,
    alto_mm: float,
    fondo_mm: float,
    num_baldas: int = 0,
    num_puertas: int = 0,
    num_cajones: int = 0,
    dimensions_portes: str | list[str] | None = None,
    num_patas: int = 0,
    altura_patas: float = 0,
    tipo_mueble: str = "S",
) -> str:
    ancho_mm = _to_positive_float(ancho_mm, fallback=600.0)
    alto_mm = _to_positive_float(alto_mm, fallback=800.0)
    fondo_mm = _to_positive_float(fondo_mm, fallback=350.0)
    num_baldas = _to_non_negative_int(num_baldas)
    num_puertas = _to_non_negative_int(num_puertas)
    num_cajones = _to_non_negative_int(num_cajones)
    num_patas = _to_non_negative_int(num_patas)
    altura_patas = _to_non_negative_float(altura_patas)
    tipo_mueble = _normalizar_tipo(tipo_mueble)

    espesor_mm = ESPESOR_ESTANDAR_MM
    color_relleno = _normalizar_hex("#FFFFFF")
    color_linea = "#111111"

    uid = uuid4().hex[:8]
    clase_relleno = f"f_{uid}"
    clase_linea = f"s_{uid}"
    clase_frente = f"fr_{uid}"

    x0 = 170.0
    y0 = 110.0

    # Proyección isométrica real: los 3 ejes comparten escala,
    # con profundidad a 30° respecto al eje horizontal.
    escala_isometrica = 0.50
    px_por_mm_x = escala_isometrica
    px_por_mm_y = escala_isometrica
    fondo_dx_por_mm = escala_isometrica * math.cos(math.radians(30.0))
    fondo_dy_por_mm = escala_isometrica * math.sin(math.radians(30.0))

    ancho_px = ancho_mm * px_por_mm_x
    alto_px = alto_mm * px_por_mm_y
    dx_fondo = fondo_mm * fondo_dx_por_mm
    dy_fondo = fondo_mm * fondo_dy_por_mm

    espesor_px_y = max(10.0, espesor_mm * px_por_mm_y)
    espesor_px_x = max(10.0, espesor_mm * px_por_mm_x)

    x_front_left = x0
    y_front_top = y0
    x_front_right = x_front_left + ancho_px
    x_back_left = x_front_left + dx_fondo
    x_back_right = x_front_right + dx_fondo
    y_back = y_front_top - dy_fondo
    y_suelo = y_front_top + alto_px

    x_inner_left_front = x_front_left + espesor_px_x
    x_inner_right_front = x_front_right - espesor_px_x
    x_inner_back_left = x_back_left + espesor_px_x
    x_right_side_outer_back = x_back_right

    y_tapa_top_front = y_front_top
    y_tapa_bottom_front = y_tapa_top_front + espesor_px_y
    y_tapa_top_back = y_back
    y_tapa_bottom_back = y_tapa_top_back + espesor_px_y

    y_base_bottom_front = y_suelo
    y_base_top_front = y_base_bottom_front - espesor_px_y
    y_base_top_back = y_base_top_front - dy_fondo

    x_trasera_left = x_inner_back_left
    x_trasera_right = x_back_right - espesor_px_x
    y_trasera_top = y_tapa_bottom_back
    y_trasera_bottom = y_base_top_back

    baldas = _calcular_baldas(
        num_baldas=num_baldas,
        y_tapa_bottom_front=y_tapa_bottom_front,
        y_base_top_front=y_base_top_front,
        espesor_px_y=espesor_px_y,
        dy_fondo=dy_fondo,
    )

    alturas_frentes_mm = _resolver_alturas_frentes(
        num_puertas=num_puertas,
        num_cajones=num_cajones,
        dimensions_portes=dimensions_portes,
        alto_mm=alto_mm,
    )
    frentes = _calcular_frentes(
        alturas_frentes_mm=alturas_frentes_mm,
        num_cajones=num_cajones,
        num_puertas=num_puertas,
        y_base_top_front=y_base_top_front,
        y_tapa_bottom_front=y_tapa_bottom_front,
        px_por_mm_y=px_por_mm_y,
    )

    patas = _calcular_patas(
        tipo_mueble=tipo_mueble,
        num_patas=num_patas,
        altura_patas_mm=altura_patas,
        x_left=x_front_left,
        x_right=x_front_right,
        y_base_bottom=y_base_bottom_front,
        px_por_mm_y=px_por_mm_y,
    )

    rellenos_base: list[str] = []
    lineas_base: list[tuple[float, float, str]] = []
    rellenos_frente: list[str] = []
    rellenos_patas: list[str] = []
    lineas_patas: list[tuple[float, float, str]] = []

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    def _track(x: float, y: float) -> None:
        nonlocal min_x, max_x, min_y, max_y
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)

    def add_line(
        target: list[tuple[float, float, str]],
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        clase: str | None = None,
    ) -> None:
        cls = clase or clase_linea
        _track(x1, y1)
        _track(x2, y2)
        linea = f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
        target.append((((x1 + x2) / 2.0), ((y1 + y2) / 2.0), linea))

    def add_polygon(target: list[str], puntos: list[tuple[float, float]], clase: str | None = None) -> None:
        cls = clase or clase_relleno
        for x, y in puntos:
            _track(x, y)
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in puntos)
        target.append(f'<polygon class="{cls}" points="{p}"/>')

    # Estructura abierta + líneas interiores
    add_polygon(rellenos_base, [(x_front_left, y_tapa_top_front), (x_front_right, y_tapa_top_front), (x_back_right, y_tapa_top_back), (x_back_left, y_tapa_top_back)])
    add_polygon(rellenos_base, [(x_front_left, y_tapa_top_front), (x_inner_left_front, y_tapa_top_front), (x_inner_left_front, y_tapa_bottom_front), (x_front_left, y_tapa_bottom_front)])
    add_polygon(rellenos_base, [(x_inner_left_front, y_tapa_top_front), (x_back_left, y_tapa_top_back), (x_inner_back_left, y_tapa_top_back), (x_inner_left_front, y_tapa_bottom_front)])
    add_polygon(rellenos_base, [(x_inner_right_front, y_tapa_top_front), (x_front_right, y_tapa_top_front), (x_front_right, y_tapa_bottom_front), (x_inner_right_front, y_tapa_bottom_front)])
    add_polygon(rellenos_base, [(x_inner_right_front, y_tapa_top_front), (x_front_right, y_tapa_top_front), (x_back_right, y_tapa_top_back), (x_back_right - espesor_px_x, y_tapa_top_back)])
    add_polygon(rellenos_base, [(x_front_left, y_tapa_top_front), (x_inner_left_front, y_tapa_top_front), (x_inner_left_front, y_suelo), (x_front_left, y_suelo)])
    add_polygon(rellenos_base, [(x_inner_right_front, y_tapa_top_front), (x_front_right, y_tapa_top_front), (x_front_right, y_suelo), (x_inner_right_front, y_suelo)])
    add_polygon(rellenos_base, [(x_front_right, y_tapa_top_front), (x_back_right, y_tapa_top_back), (x_right_side_outer_back, y_suelo - dy_fondo), (x_front_right, y_suelo)])
    add_polygon(rellenos_base, [(x_trasera_left, y_trasera_top), (x_trasera_right, y_trasera_top), (x_trasera_right, y_trasera_bottom), (x_trasera_left, y_trasera_bottom)])
    add_polygon(rellenos_base, [(x_inner_left_front, y_tapa_bottom_front), (x_inner_back_left, y_tapa_bottom_back), (x_inner_back_left, y_base_top_back), (x_inner_left_front, y_base_top_front)])
    add_polygon(rellenos_base, [(x_inner_left_front, y_base_top_front), (x_inner_right_front, y_base_top_front), (x_inner_right_front, y_base_top_back), (x_inner_back_left, y_base_top_back)])
    add_polygon(rellenos_base, [(x_inner_left_front, y_base_top_front), (x_inner_right_front, y_base_top_front), (x_inner_right_front, y_base_bottom_front), (x_inner_left_front, y_base_bottom_front)])

    add_line(lineas_base, x_front_left, y_tapa_top_front, x_front_right, y_tapa_top_front)
    add_line(lineas_base, x_front_right, y_tapa_top_front, x_back_right, y_tapa_top_back)
    add_line(lineas_base, x_front_left, y_tapa_top_front, x_back_left, y_tapa_top_back)
    add_line(lineas_base, x_back_left, y_tapa_top_back, x_back_right, y_tapa_top_back)
    add_line(lineas_base, x_inner_left_front, y_tapa_bottom_front, x_inner_right_front, y_tapa_bottom_front)
    add_line(lineas_base, x_inner_left_front, y_tapa_top_front, x_inner_left_front, y_tapa_bottom_front)
    add_line(lineas_base, x_inner_right_front, y_tapa_top_front, x_inner_right_front, y_tapa_bottom_front)
    add_line(lineas_base, x_front_left, y_tapa_top_front, x_front_left, y_suelo)
    add_line(lineas_base, x_inner_left_front, y_tapa_top_front, x_inner_left_front, y_suelo)
    add_line(lineas_base, x_front_left, y_suelo, x_inner_left_front, y_suelo)
    add_line(lineas_base, x_front_left, y_tapa_top_front, x_inner_left_front, y_tapa_top_front)
    add_line(lineas_base, x_inner_left_front, y_tapa_top_front, x_inner_back_left, y_tapa_top_back)
    add_line(lineas_base, x_back_left, y_tapa_top_back, x_inner_back_left, y_tapa_top_back)

    inicio = y_tapa_bottom_front + 1.0
    if baldas:
        fin = baldas[0]["y_sup_back"]
        if fin > inicio:
            add_line(lineas_base, x_inner_back_left, inicio, x_inner_back_left, fin)
        for i in range(len(baldas) - 1):
            inicio_i = baldas[i]["y_inf_front"] + 1.0
            fin_i = baldas[i + 1]["y_sup_back"]
            if fin_i > inicio_i:
                add_line(lineas_base, x_inner_back_left, inicio_i, x_inner_back_left, fin_i)
        inicio_last = baldas[-1]["y_inf_front"] + 1.0
        if y_base_top_back > inicio_last:
            add_line(lineas_base, x_inner_back_left, inicio_last, x_inner_back_left, y_base_top_back)
    elif y_base_top_back > inicio:
        add_line(lineas_base, x_inner_back_left, inicio, x_inner_back_left, y_base_top_back)

    add_line(lineas_base, x_front_right, y_tapa_top_front, x_front_right, y_suelo)
    add_line(lineas_base, x_inner_right_front, y_tapa_top_front, x_inner_right_front, y_suelo)
    add_line(lineas_base, x_inner_right_front, y_suelo, x_front_right, y_suelo)
    add_line(lineas_base, x_inner_right_front, y_tapa_top_front, x_front_right, y_tapa_top_front)
    add_line(lineas_base, x_inner_right_front, y_tapa_top_front, x_back_right - espesor_px_x, y_tapa_top_back)
    add_line(lineas_base, x_back_right - espesor_px_x, y_tapa_top_back, x_back_right, y_tapa_top_back)
    add_line(lineas_base, x_front_right, y_tapa_top_front, x_back_right, y_tapa_top_back)
    add_line(lineas_base, x_right_side_outer_back, y_tapa_top_back, x_right_side_outer_back, y_suelo - dy_fondo)
    add_line(lineas_base, x_front_right, y_suelo, x_right_side_outer_back, y_suelo - dy_fondo)
    add_line(lineas_base, x_inner_left_front, y_base_top_front, x_inner_right_front, y_base_top_front)
    add_line(lineas_base, x_inner_left_front, y_base_top_front, x_inner_back_left, y_base_top_back)
    add_line(lineas_base, x_inner_back_left, y_base_top_back, x_inner_right_front, y_base_top_back)
    add_line(lineas_base, x_inner_left_front, y_base_bottom_front, x_inner_right_front, y_base_bottom_front)
    add_line(lineas_base, x_inner_left_front, y_base_top_front, x_inner_left_front, y_base_bottom_front)
    add_line(lineas_base, x_inner_right_front, y_base_top_front, x_inner_right_front, y_base_bottom_front)

    for balda in baldas:
        add_polygon(rellenos_base, [(x_inner_left_front, balda["y_sup_front"]), (x_inner_right_front, balda["y_sup_front"]), (x_inner_right_front, balda["y_sup_back"]), (x_inner_back_left, balda["y_sup_back"])])
        add_polygon(rellenos_base, [(x_inner_left_front, balda["y_sup_front"]), (x_inner_right_front, balda["y_sup_front"]), (x_inner_right_front, balda["y_inf_front"]), (x_inner_left_front, balda["y_inf_front"])])

        add_line(lineas_base, x_inner_left_front, balda["y_sup_front"], x_inner_right_front, balda["y_sup_front"])
        add_line(lineas_base, x_inner_left_front, balda["y_sup_front"], x_inner_back_left, balda["y_sup_back"])
        add_line(lineas_base, x_inner_back_left, balda["y_sup_back"], x_inner_right_front, balda["y_sup_back"])
        add_line(lineas_base, x_inner_left_front, balda["y_inf_front"], x_inner_right_front, balda["y_inf_front"])
        add_line(lineas_base, x_inner_left_front, balda["y_sup_front"], x_inner_left_front, balda["y_inf_front"])
        add_line(lineas_base, x_inner_right_front, balda["y_sup_front"], x_inner_right_front, balda["y_inf_front"])

    # Frentes opacos: el relleno se dibuja al final para ocultar interior.
    for frente in frentes:
        y_top = frente["y_top"]
        y_bottom = frente["y_bottom"]
        add_polygon(
            rellenos_frente,
            [(x_front_left, y_top), (x_front_right, y_top), (x_front_right, y_bottom), (x_front_left, y_bottom)],
            clase=clase_frente,
        )

    for pata in patas:
        x = pata["x"]
        y_top = pata["y_top"]
        y_bottom = pata["y_bottom"]
        ancho_pata = pata["ancho"]

        add_polygon(rellenos_patas, [(x, y_top), (x + ancho_pata, y_top), (x + ancho_pata, y_bottom), (x, y_bottom)])
        add_line(lineas_patas, x, y_top, x + ancho_pata, y_top)
        add_line(lineas_patas, x + ancho_pata, y_top, x + ancho_pata, y_bottom)
        add_line(lineas_patas, x + ancho_pata, y_bottom, x, y_bottom)
        add_line(lineas_patas, x, y_bottom, x, y_top)

    if min_x == float("inf"):
        min_x = 0.0
        max_x = 100.0
        min_y = 0.0
        max_y = 100.0

    # Margen extra para evitar recortes, especialmente en patas/base y zona superior.
    margen_x = 30.0
    margen_y_superior = 42.0
    margen_y_inferior = 52.0
    min_x -= margen_x
    min_y -= margen_y_superior
    max_x += margen_x
    max_y += margen_y_inferior

    view_w = max_x - min_x
    view_h = max_y - min_y

    lineas_ordenadas = [linea for _, _, linea in sorted([*lineas_base, *lineas_patas], key=lambda item: (item[1], item[0]))]

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:.1f} {min_y:.1f} {view_w:.1f} {view_h:.1f}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">',
        "<style>",
        f'.{clase_relleno}{{fill:{color_relleno};stroke:none;}}',
        f'.{clase_linea}{{stroke:{color_linea};stroke-width:2.2;fill:none;stroke-linecap:round;stroke-linejoin:round;}}',
        f'.{clase_frente}{{fill:#FFFFFF;stroke:#111111;stroke-width:2.2;stroke-linejoin:round;}}',
        "</style>",
        *rellenos_base,
        *lineas_ordenadas,
        *rellenos_frente,
        *rellenos_patas,
        "</svg>",
    ]
    return "\n".join(svg)


def generar_svg_mueble_desde_csv_row(row: dict[str, Any]) -> str:
    return generar_svg_mueble(
        ancho_mm=row.get("ancho_mm"),
        alto_mm=row.get("alto_mm"),
        fondo_mm=row.get("fondo_mm"),
        num_baldas=row.get("num_baldas", 0),
        num_puertas=row.get("num_puertas", 0),
        num_cajones=row.get("num_cajones", 0),
        dimensions_portes=row.get("dimensions_portes"),
        num_patas=row.get("num_patas", 0),
        altura_patas=row.get("altura_patas", 0),
        tipo_mueble=row.get("tipo_mueble", "S"),
    )


def _calcular_baldas(
    num_baldas: int,
    y_tapa_bottom_front: float,
    y_base_top_front: float,
    espesor_px_y: float,
    dy_fondo: float,
) -> list[dict[str, float]]:
    if num_baldas <= 0:
        return []

    hueco_libre = y_base_top_front - y_tapa_bottom_front
    separacion = hueco_libre / (num_baldas + 1)
    baldas: list[dict[str, float]] = []

    for i in range(num_baldas):
        y_sup_front = y_tapa_bottom_front + separacion * (i + 1)
        y_inf_front = y_sup_front + espesor_px_y
        baldas.append(
            {
                "y_sup_front": y_sup_front,
                "y_inf_front": y_inf_front,
                "y_sup_back": y_sup_front - dy_fondo,
                "y_inf_back": y_inf_front - dy_fondo,
            }
        )
    return baldas


def _resolver_alturas_frentes(
    num_puertas: int,
    num_cajones: int,
    dimensions_portes: str | list[str] | None,
    alto_mm: float,
) -> list[float]:
    total_frentes = num_puertas + num_cajones
    if total_frentes <= 0:
        return []

    alturas = _parse_alturas_portes(dimensions_portes)
    if not alturas:
        igual = max(80.0, alto_mm / total_frentes)
        return [igual for _ in range(total_frentes)]

    if len(alturas) < total_frentes:
        alturas.extend([alturas[-1]] * (total_frentes - len(alturas)))

    return alturas[:total_frentes]


def _calcular_frentes(
    alturas_frentes_mm: list[float],
    num_cajones: int,
    num_puertas: int,
    y_base_top_front: float,
    y_tapa_bottom_front: float,
    px_por_mm_y: float,
) -> list[dict[str, float | str]]:
    total = num_cajones + num_puertas
    if total == 0:
        return []

    alturas_px = [max(12.0, h * px_por_mm_y) for h in alturas_frentes_mm]

    alto_disponible = max(0.0, y_base_top_front - y_tapa_bottom_front)
    suma = sum(alturas_px)
    escala = 1.0 if suma <= 0 else min(1.0, alto_disponible / suma)
    alturas_px = [h * escala for h in alturas_px]

    frentes: list[dict[str, float | str]] = []
    y_cursor = y_base_top_front

    for i in range(num_cajones):
        alto = alturas_px[i] if i < len(alturas_px) else (alto_disponible / total)
        y_top = max(y_tapa_bottom_front, y_cursor - alto)
        frentes.append({"tipo": "cajon", "y_top": y_top, "y_bottom": y_cursor})
        y_cursor = y_top

    for j in range(num_puertas):
        idx = num_cajones + j
        alto = alturas_px[idx] if idx < len(alturas_px) else (alto_disponible / total)
        y_top = max(y_tapa_bottom_front, y_cursor - alto)
        frentes.append({"tipo": "puerta", "y_top": y_top, "y_bottom": y_cursor})
        y_cursor = y_top

    return frentes


def _calcular_patas(
    tipo_mueble: str,
    num_patas: int,
    altura_patas_mm: float,
    x_left: float,
    x_right: float,
    y_base_bottom: float,
    px_por_mm_y: float,
) -> list[dict[str, float]]:
    if tipo_mueble != "P" or num_patas <= 0 or altura_patas_mm <= 0:
        return []

    altura_px = altura_patas_mm * px_por_mm_y
    ancho_pata = 14.0
    margen = 18.0

    pos_candidatas = [
        x_left + margen,
        x_right - margen - ancho_pata,
        x_left + (x_right - x_left) * 0.33,
        x_left + (x_right - x_left) * 0.66,
    ]
    posiciones = pos_candidatas[: min(num_patas, len(pos_candidatas))]

    return [
        {
            "x": x,
            "y_top": y_base_bottom,
            "y_bottom": y_base_bottom + altura_px,
            "ancho": ancho_pata,
        }
        for x in posiciones
    ]


def _parse_alturas_portes(dimensions_portes: str | list[str] | None) -> list[float]:
    if not dimensions_portes:
        return []

    if isinstance(dimensions_portes, list):
        partes = [str(v) for v in dimensions_portes]
    else:
        texto = str(dimensions_portes)
        partes = [p.strip() for p in re.split(r"[\n;,]+", texto) if p.strip()]

    alturas: list[float] = []
    for item in partes:
        m = re.search(r"(\d+(?:[\.,]\d+)?)\s*[xX*]\s*(\d+(?:[\.,]\d+)?)", item)
        if m:
            altura = _to_non_negative_float(m.group(2).replace(",", "."))
        else:
            nums = re.findall(r"\d+(?:[\.,]\d+)?", item)
            if not nums:
                continue
            altura = _to_non_negative_float(nums[-1].replace(",", "."))

        if altura > 0:
            alturas.append(_redondear_decena(altura))

    return alturas


def _redondear_decena(valor: float) -> float:
    return float(int(math.floor((valor + 5.0) / 10.0) * 10))


def _to_non_negative_int(value: Any, fallback: int = 0) -> int:
    try:
        if value in (None, ""):
            return fallback
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return fallback


def _to_positive_float(value: Any, fallback: float) -> float:
    try:
        if value in (None, ""):
            return fallback
        parsed = float(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _to_non_negative_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return fallback
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return fallback


def _normalizar_tipo(tipo_mueble: Any) -> str:
    tipo = str(tipo_mueble or "S").strip().upper()
    return "P" if tipo == "P" else "S"


def _normalizar_hex(color_hex: str) -> str:
    valor = str(color_hex).strip()
    if re.fullmatch(r"#([0-9a-fA-F]{6})", valor):
        return valor.upper()
    return "#FFFFFF"


if __name__ == "__main__":
    svg = generar_svg_mueble(
        ancho_mm=600,
        alto_mm=800,
        fondo_mm=375,
        num_baldas=2,
        num_puertas=1,
        num_cajones=2,
        dimensions_portes="450 * 200\n450 * 300\n450 * 280",
        num_patas=4,
        altura_patas=100,
        tipo_mueble="P",
    )
    with open("mueble.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("SVG generado en mueble.svg")
