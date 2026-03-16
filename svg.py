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

    # Isométrica técnica real: frente, lateral derecho y tapa visibles.
    ang = math.radians(30.0)
    cos30 = math.cos(ang)
    sin30 = math.sin(ang)
    escala = 0.44

    ox = 240.0
    oy = 150.0

    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    def track(x: float, y: float) -> None:
        nonlocal min_x, max_x, min_y, max_y
        min_x = min(min_x, x)
        max_x = max(max_x, x)
        min_y = min(min_y, y)
        max_y = max(max_y, y)

    def proj(x_mm: float, y_mm: float, z_mm: float) -> tuple[float, float]:
        x = ox + (x_mm - z_mm) * cos30 * escala
        y = oy + (x_mm + z_mm) * sin30 * escala + y_mm * escala
        track(x, y)
        return x, y

    uid = uuid4().hex[:8]
    clase_cara = f"f_{uid}"
    clase_linea = f"s_{uid}"
    clase_frente = f"fr_{uid}"

    caras: list[str] = []
    lineas: list[str] = []
    frentes_svg: list[str] = []
    patas_svg: list[str] = []

    def add_polygon(target: list[str], puntos_3d: list[tuple[float, float, float]], clase: str) -> None:
        pts = [proj(*p) for p in puntos_3d]
        serial = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        target.append(f'<polygon class="{clase}" points="{serial}"/>')

    def add_line(p1: tuple[float, float, float], p2: tuple[float, float, float]) -> None:
        x1, y1 = proj(*p1)
        x2, y2 = proj(*p2)
        lineas.append(f'<line class="{clase_linea}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')

    w = ancho_mm
    h = alto_mm
    d = fondo_mm

    # Caras visibles opacas
    add_polygon(caras, [(0, 0, 0), (w, 0, 0), (w, 0, d), (0, 0, d)], clase_cara)  # tapa
    add_polygon(caras, [(w, 0, 0), (w, h, 0), (w, h, d), (w, 0, d)], clase_cara)  # lateral derecho

    hay_frentes = (num_puertas + num_cajones) > 0
    if not hay_frentes:
        add_polygon(caras, [(0, 0, 0), (w, 0, 0), (w, h, 0), (0, h, 0)], clase_cara)

    # Contorno técnico
    add_line((0, 0, 0), (w, 0, 0))
    add_line((w, 0, 0), (w, h, 0))
    add_line((w, h, 0), (0, h, 0))
    add_line((0, h, 0), (0, 0, 0))

    add_line((0, 0, 0), (0, 0, d))
    add_line((w, 0, 0), (w, 0, d))
    add_line((w, h, 0), (w, h, d))
    add_line((0, h, 0), (0, h, d))

    add_line((0, 0, d), (w, 0, d))
    add_line((w, 0, d), (w, h, d))
    add_line((w, h, d), (0, h, d))
    add_line((0, h, d), (0, 0, d))

    # Apertura frontal si no hay puertas/cajones: baldas visibles en isométrica
    if not hay_frentes:
        x0 = espesor_mm
        x1 = max(x0 + 1.0, w - espesor_mm)
        y0 = espesor_mm
        y1 = max(y0 + 1.0, h - espesor_mm)
        zf = 0.0

        add_polygon(caras, [(x0, y0, zf), (x1, y0, zf), (x1, y1, zf), (x0, y1, zf)], clase_cara)
        add_line((x0, y0, zf), (x1, y0, zf))
        add_line((x1, y0, zf), (x1, y1, zf))
        add_line((x1, y1, zf), (x0, y1, zf))
        add_line((x0, y1, zf), (x0, y0, zf))

        if num_baldas > 0:
            hueco = y1 - y0
            paso = hueco / (num_baldas + 1)
            esp = max(8.0, espesor_mm * 0.8)
            for i in range(num_baldas):
                ys = y0 + (i + 1) * paso
                add_polygon(
                    caras,
                    [(x0, ys, 0), (x1, ys, 0), (x1, ys + esp, d - espesor_mm), (x0, ys + esp, d - espesor_mm)],
                    clase_cara,
                )
                add_line((x0, ys, 0), (x1, ys, 0))

    # Frentes opacos (puertas/cajones)
    alturas_frentes_mm = _resolver_alturas_frentes(
        num_puertas=num_puertas,
        num_cajones=num_cajones,
        dimensions_portes=dimensions_portes,
        alto_mm=alto_mm,
    )

    total_frentes = num_puertas + num_cajones
    if total_frentes > 0:
        y_tapa = espesor_mm
        y_base = h - espesor_mm
        alto_disponible = max(20.0, y_base - y_tapa)

        alturas = alturas_frentes_mm[:total_frentes] if alturas_frentes_mm else [alto_disponible / total_frentes] * total_frentes
        if len(alturas) < total_frentes:
            alturas += [alturas[-1]] * (total_frentes - len(alturas))

        suma = max(1.0, sum(alturas))
        escala_alt = min(1.0, alto_disponible / suma)
        alturas = [hmm * escala_alt for hmm in alturas]

        y_cursor = y_base
        for alto_frente in alturas:
            y_top = max(y_tapa, y_cursor - alto_frente)
            add_polygon(frentes_svg, [(0, y_top, 0), (w, y_top, 0), (w, y_cursor, 0), (0, y_cursor, 0)], clase_frente)
            y_cursor = y_top

    # Patas: prismas pequeños para mantener isométrica y evitar recortes inferiores
    patas = _calcular_patas(
        tipo_mueble=tipo_mueble,
        num_patas=num_patas,
        altura_patas_mm=altura_patas,
        x_left=0.0,
        x_right=w,
        y_base_bottom=h,
        px_por_mm_y=1.0,
    )
    for pata in patas:
        x = pata["x"]
        y_top = pata["y_top"]
        y_bottom = pata["y_bottom"]
        ancho = pata["ancho"]
        fondo_pata = min(max(10.0, d * 0.12), 24.0)

        add_polygon(patas_svg, [(x, y_top, 0), (x + ancho, y_top, 0), (x + ancho, y_bottom, 0), (x, y_bottom, 0)], clase_cara)
        add_polygon(patas_svg, [(x + ancho, y_top, 0), (x + ancho, y_top, fondo_pata), (x + ancho, y_bottom, fondo_pata), (x + ancho, y_bottom, 0)], clase_cara)
        add_line((x, y_top, 0), (x + ancho, y_top, 0))
        add_line((x + ancho, y_top, 0), (x + ancho, y_bottom, 0))
        add_line((x + ancho, y_bottom, 0), (x, y_bottom, 0))
        add_line((x, y_bottom, 0), (x, y_top, 0))

    if min_x == float("inf"):
        min_x, min_y, max_x, max_y = 0.0, 0.0, 100.0, 100.0

    min_x -= 42.0
    max_x += 42.0
    min_y -= 46.0
    max_y += 58.0

    view_w = max_x - min_x
    view_h = max_y - min_y

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:.1f} {min_y:.1f} {view_w:.1f} {view_h:.1f}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">',
        "<style>",
        f'.{clase_cara}{{fill:{color_relleno};stroke:{color_linea};stroke-width:2.2;stroke-linejoin:round;}}',
        f'.{clase_linea}{{stroke:{color_linea};stroke-width:2.0;fill:none;stroke-linecap:round;stroke-linejoin:round;}}',
        f'.{clase_frente}{{fill:#FFFFFF;stroke:#111111;stroke-width:2.2;stroke-linejoin:round;}}',
        "</style>",
        *caras,
        *patas_svg,
        *lineas,
        *frentes_svg,
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
