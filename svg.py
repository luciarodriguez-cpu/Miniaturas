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
    color_relleno = "#FFFFFF"
    color_linea = "#111111"

    # Ejes canónicos: x=ancho, y=fondo, z=altura.
    # Isometría técnica con la misma escala en X/Y/Z.
    ang = math.radians(30.0)
    cos30 = math.cos(ang)
    sin30 = math.sin(ang)
    escala = 0.44

    ox = 240.0
    oy = 420.0

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    def track(px: float, py: float) -> None:
        nonlocal min_x, max_x, min_y, max_y
        min_x = min(min_x, px)
        max_x = max(max_x, px)
        min_y = min(min_y, py)
        max_y = max(max_y, py)

    def proj(x_mm: float, y_mm: float, z_mm: float) -> tuple[float, float]:
        px = ox + (x_mm - y_mm) * cos30 * escala
        py = oy + (x_mm + y_mm) * sin30 * escala - z_mm * escala
        track(px, py)
        return px, py

    uid = uuid4().hex[:8]
    clase_cara = f"f_{uid}"
    clase_linea = f"s_{uid}"
    clase_frente = f"fr_{uid}"

    caras: list[str] = []
    patas_svg: list[str] = []
    frentes_svg: list[str] = []
    lineas: list[str] = []

    def add_polygon(target: list[str], pts3d: list[tuple[float, float, float]], clase: str) -> None:
        pts2d = [proj(*p) for p in pts3d]
        pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts2d)
        target.append(f'<polygon class="{clase}" points="{pts}"/>')

    def add_line(p1: tuple[float, float, float], p2: tuple[float, float, float]) -> None:
        x1, y1 = proj(*p1)
        x2, y2 = proj(*p2)
        lineas.append(
            f'<line class="{clase_linea}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
        )

    w = ancho_mm
    d = fondo_mm
    h = alto_mm

    altura_patas_real = altura_patas if tipo_mueble == "P" else 0.0
    z0 = altura_patas_real
    z1 = z0 + h

    hay_frentes = (num_puertas + num_cajones) > 0

    # Caras opacas del mueble (sin wireframe de caras ocultas)
    # Tapa
    add_polygon(caras, [(0, 0, z1), (w, 0, z1), (w, d, z1), (0, d, z1)], clase_cara)
    # Lateral derecho visible
    add_polygon(caras, [(w, 0, z0), (w, d, z0), (w, d, z1), (w, 0, z1)], clase_cara)
    # Frente cerrado solo si no hay puertas/cajones
    if not hay_frentes:
        add_polygon(caras, [(0, 0, z0), (w, 0, z0), (w, 0, z1), (0, 0, z1)], clase_cara)

    # Interior y baldas: visibles solo cuando no hay frentes
    if not hay_frentes:
        xi0 = espesor_mm
        xi1 = max(xi0 + 1.0, w - espesor_mm)
        yi1 = max(espesor_mm, d - espesor_mm)
        zi0 = z0 + espesor_mm
        zi1 = max(zi0 + 1.0, z1 - espesor_mm)

        if num_baldas > 0 and zi1 > zi0 + 8.0:
            paso = (zi1 - zi0) / (num_baldas + 1)
            esp_balda = max(8.0, espesor_mm * 0.85)
            for idx in range(num_baldas):
                z_sup = zi0 + (idx + 1) * paso
                z_inf = min(zi1, z_sup + esp_balda)
                # cara superior de balda
                add_polygon(caras, [(xi0, 0, z_sup), (xi1, 0, z_sup), (xi1, yi1, z_sup), (xi0, yi1, z_sup)], clase_cara)
                # canto frontal de balda
                add_polygon(caras, [(xi0, 0, z_sup), (xi1, 0, z_sup), (xi1, 0, z_inf), (xi0, 0, z_inf)], clase_cara)

    # Patas opacas
    patas = _calcular_patas(tipo_mueble=tipo_mueble, num_patas=num_patas, altura_patas_mm=altura_patas_real, x_left=0.0, x_right=w)
    for pata in patas:
        x0 = pata["x"]
        x1 = x0 + pata["ancho"]
        y0 = 0.0
        y1 = min(max(10.0, d * 0.14), 24.0)
        pz0 = 0.0
        pz1 = altura_patas_real

        # frente de pata
        add_polygon(patas_svg, [(x0, y0, pz0), (x1, y0, pz0), (x1, y0, pz1), (x0, y0, pz1)], clase_cara)
        # lateral derecho de pata
        add_polygon(patas_svg, [(x1, y0, pz0), (x1, y1, pz0), (x1, y1, pz1), (x1, y0, pz1)], clase_cara)

    # Frentes opacos delante del mueble (cajones abajo, puertas arriba)
    total_frentes = num_cajones + num_puertas
    if total_frentes > 0:
        alto_util = max(40.0, h - 2 * espesor_mm)
        alturas = _resolver_alturas_frentes(
            num_puertas=num_puertas,
            num_cajones=num_cajones,
            dimensions_portes=dimensions_portes,
            alto_mm=alto_util,
        )
        if len(alturas) < total_frentes:
            faltan = total_frentes - len(alturas)
            alturas.extend([max(80.0, alto_util / total_frentes)] * faltan)

        alturas = alturas[:total_frentes]
        suma_alturas = max(1.0, sum(alturas))
        factor = alto_util / suma_alturas
        alturas = [a * factor for a in alturas]

        bloques = (["cajon"] * num_cajones) + (["puerta"] * num_puertas)
        z_cursor = z0 + espesor_mm
        for tipo_bloque, alto_bloque in zip(bloques, alturas):
            z_next = min(z1 - espesor_mm, z_cursor + alto_bloque)
            if z_next <= z_cursor:
                continue
            add_polygon(frentes_svg, [(0, 0, z_cursor), (w, 0, z_cursor), (w, 0, z_next), (0, 0, z_next)], clase_frente)
            z_cursor = z_next

    # Aristas visibles únicamente
    visible_edges = [
        # Frente
        ((0, 0, z0), (w, 0, z0)),
        ((w, 0, z0), (w, 0, z1)),
        ((w, 0, z1), (0, 0, z1)),
        ((0, 0, z1), (0, 0, z0)),
        # Tapa
        ((0, 0, z1), (0, d, z1)),
        ((0, d, z1), (w, d, z1)),
        ((w, d, z1), (w, 0, z1)),
        # Lateral derecho
        ((w, 0, z0), (w, d, z0)),
        ((w, d, z0), (w, d, z1)),
    ]

    # Línea base frontal solo cuando hay patas (se ve z0 elevado)
    if altura_patas_real > 0:
        visible_edges.append(((0, 0, z0), (0, d * 0.18, z0)))

    for p1, p2 in visible_edges:
        add_line(p1, p2)

    if min_x == float("inf"):
        min_x, min_y, max_x, max_y = 0.0, 0.0, 100.0, 100.0

    margen_x = 52.0
    margen_y_arriba = 56.0
    margen_y_abajo = 72.0

    vb_x = min_x - margen_x
    vb_y = min_y - margen_y_arriba
    vb_w = (max_x - min_x) + 2 * margen_x
    vb_h = (max_y - min_y) + margen_y_arriba + margen_y_abajo

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">',
        "<style>",
        f'.{clase_cara}{{fill:{color_relleno};stroke:{color_linea};stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round;}}',
        f'.{clase_frente}{{fill:#FFFFFF;stroke:#111111;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round;}}',
        f'.{clase_linea}{{fill:none;stroke:{color_linea};stroke-width:2.0;stroke-linejoin:round;stroke-linecap:round;}}',
        "</style>",
        *caras,
        *patas_svg,
        *frentes_svg,
        *lineas,
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


def _resolver_alturas_frentes(
    num_puertas: int,
    num_cajones: int,
    dimensions_portes: str | list[str] | None,
    alto_mm: float,
) -> list[float]:
    total = num_puertas + num_cajones
    if total <= 0:
        return []

    alturas = _parse_alturas_portes(dimensions_portes)
    if not alturas:
        altura_base = max(80.0, alto_mm / total)
        return [altura_base for _ in range(total)]

    if len(alturas) < total:
        faltan = total - len(alturas)
        altura_relleno = max(80.0, (alto_mm - sum(alturas)) / max(1, faltan))
        alturas.extend([altura_relleno for _ in range(faltan)])

    return [max(40.0, h) for h in alturas[:total]]


def _calcular_patas(
    tipo_mueble: str,
    num_patas: int,
    altura_patas_mm: float,
    x_left: float,
    x_right: float,
) -> list[dict[str, float]]:
    if tipo_mueble != "P" or num_patas <= 0 or altura_patas_mm <= 0:
        return []

    ancho = 14.0
    margen = 18.0
    span = max(1.0, x_right - x_left)

    candidatas = [
        x_left + margen,
        x_right - margen - ancho,
        x_left + span * 0.34,
        x_left + span * 0.66,
    ]
    posiciones = candidatas[: min(num_patas, len(candidatas))]

    return [{"x": x, "ancho": ancho} for x in posiciones]


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
        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*[xX*]\s*(\d+(?:[\.,]\d+)?)", item)
        if match:
            altura = _to_non_negative_float(match.group(2).replace(",", "."))
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
