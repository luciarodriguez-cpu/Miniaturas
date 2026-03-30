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
    num_tiroirs: int = 0
    num_blocs_coulissants: int = 0
    num_faux_tiroirs_bandeau: int = 0
    num_facades: int = 0
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
    num_tiroirs: int = 0,
    num_blocs_coulissants: int = 0,
    num_faux_tiroirs_bandeau: int = 0,
    num_facades: int = 0,
) -> str:
    ancho_mm = _to_positive_float(ancho_mm, fallback=600.0)
    alto_mm = _to_positive_float(alto_mm, fallback=800.0)
    fondo_mm = _to_positive_float(fondo_mm, fallback=350.0)
    num_baldas = _to_non_negative_int(num_baldas)
    num_puertas = _to_non_negative_int(num_puertas)
    num_cajones = _to_non_negative_int(num_cajones)
    num_tiroirs = _to_non_negative_int(num_tiroirs)
    num_blocs_coulissants = _to_non_negative_int(num_blocs_coulissants)
    num_faux_tiroirs_bandeau = _to_non_negative_int(num_faux_tiroirs_bandeau)
    num_facades = _to_non_negative_int(num_facades)
    num_patas = _to_non_negative_int(num_patas)
    altura_patas = _to_non_negative_float(altura_patas)
    tipo_mueble = _normalizar_tipo(tipo_mueble)

    espesor_mm = ESPESOR_ESTANDAR_MM
    color_relleno = "#FFFFFF"
    color_linea = "#111111"

    # Convención global: x=ancho, y=fondo, z=altura.
    # Isométrica canónica desde arriba, con lateral derecho visible.
    ang = math.radians(30)
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

    def proj(x: float, y: float, z: float) -> tuple[float, float]:
        px = ox + (x - y) * cos30 * escala
        py = oy + (x + y) * sin30 * escala - z * escala
        track(px, py)
        return px, py

    uid = uuid4().hex[:8]
    clase_cara = f"f_{uid}"
    clase_frente = f"fr_{uid}"
    clase_linea = f"s_{uid}"

    caras: list[str] = []
    tapa_svg: list[str] = []
    lateral_derecho_svg: list[str] = []
    patas_svg: list[str] = []
    base_svg: list[str] = []
    interior_svg: list[str] = []
    cajones_svg: list[str] = []
    puertas_svg: list[str] = []
    lineas: list[str] = []

    def add_polygon(target: list[str], pts3d: list[tuple[float, float, float]], clase: str) -> None:
        pts2d = [proj(*p) for p in pts3d]
        points = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts2d)
        target.append(f'<polygon class="{clase}" points="{points}"/>')

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

    legacy_total = num_cajones + num_puertas
    total_frentes = num_facades if num_facades > 0 else legacy_total
    hay_frentes = total_frentes > 0

    # 1) Caras opacas del cuerpo.
    x_panel_interior = max(0.0, w - espesor_mm)
    z_tapa_inf = max(z0, z1 - espesor_mm)
    z_base_sup = min(z1, z0 + espesor_mm)

    tapa = [(0, 0, z1), (w, 0, z1), (w, d, z1), (0, d, z1)]
    canto_frontal_tapa = [(0, d, z_tapa_inf), (w, d, z_tapa_inf), (w, d, z1), (0, d, z1)]
    # El frente visible se coloca en el lateral izquierdo de la vista (y=d).
    frente = [(0, d, z0), (w, d, z0), (w, d, z1), (0, d, z1)]

    base_panel = [
        (espesor_mm, 0.0, z0),
        (max(espesor_mm, x_panel_interior), 0.0, z0),
        (max(espesor_mm, x_panel_interior), d, z0),
        (espesor_mm, d, z0),
    ]

    add_polygon(tapa_svg, tapa, clase_cara)
    add_polygon(tapa_svg, canto_frontal_tapa, clase_cara)
    if not hay_frentes:
        add_polygon(caras, frente, clase_cara)

    add_polygon(base_svg, base_panel, clase_cara)

    # Canto frontal de la base (espesor visible hacia arriba).
    if z_base_sup > z0:
        x_base_ini = espesor_mm
        x_base_fin = max(espesor_mm, x_panel_interior)
        if x_base_fin > x_base_ini:
            canto_frontal_base = [
                (x_base_ini, d, z0),
                (x_base_fin, d, z0),
                (x_base_fin, d, z_base_sup),
                (x_base_ini, d, z_base_sup),
            ]
            add_polygon(base_svg, canto_frontal_base, clase_cara)

    # Lateral derecho como panel con espesor real.
    if w > 0 and d > 0 and espesor_mm > 0:
        lateral_exterior = [(w, 0, z0), (w, d, z0), (w, d, z1), (w, 0, z1)]
        lateral_superior = [(x_panel_interior, 0, z1), (w, 0, z1), (w, d, z1), (x_panel_interior, d, z1)]
        lateral_frontal = [(x_panel_interior, d, z0), (w, d, z0), (w, d, z1), (x_panel_interior, d, z1)]
        add_polygon(lateral_derecho_svg, lateral_exterior, clase_cara)
        add_polygon(lateral_derecho_svg, lateral_superior, clase_cara)
        add_polygon(lateral_derecho_svg, lateral_frontal, clase_cara)

    # 2) Baldas solo si hay al menos una puerta abierta.
    hay_puerta_abierta = num_puertas > 0
    if hay_puerta_abierta and num_baldas > 0:
        xi0 = min(max(espesor_mm, 8.0), x_panel_interior)
        xi1 = max(xi0 + 1.0, x_panel_interior)
        yi1 = max(0.0, d - espesor_mm)
        zi0 = z0 + espesor_mm
        zi1 = z1 - espesor_mm

        if xi1 > xi0 and zi1 - zi0 > 16.0:
            paso = (zi1 - zi0) / (num_baldas + 1)
            esp_balda = max(8.0, espesor_mm * 0.85)
            for i in range(num_baldas):
                z_sup = zi0 + (i + 1) * paso
                z_inf = min(zi1, z_sup + esp_balda)

                add_polygon(interior_svg, [(xi0, 0, z_sup), (xi1, 0, z_sup), (xi1, yi1, z_sup), (xi0, yi1, z_sup)], clase_cara)
                add_polygon(interior_svg, [(xi0, d, z_sup), (xi1, d, z_sup), (xi1, d, z_inf), (xi0, d, z_inf)], clase_cara)

    def _rotar_puerta_izquierda(x: float, y: float, angulo: float) -> tuple[float, float]:
        y_rel = y - d
        xr = x * math.cos(angulo) - y_rel * math.sin(angulo)
        yr = x * math.sin(angulo) + y_rel * math.cos(angulo)
        return xr, d + yr

    def _agregar_prisma_frente(
        target: list[str],
        z_inf: float,
        z_sup: float,
        es_puerta: bool,
        angulo: float,
    ) -> None:
        y_trasera = d
        y_frontal = d + espesor_mm

        base = {
            "bbl": (0.0, y_trasera, z_inf),
            "bbr": (w, y_trasera, z_inf),
            "bfl": (0.0, y_frontal, z_inf),
            "bfr": (w, y_frontal, z_inf),
            "tbl": (0.0, y_trasera, z_sup),
            "tbr": (w, y_trasera, z_sup),
            "tfl": (0.0, y_frontal, z_sup),
            "tfr": (w, y_frontal, z_sup),
        }

        if es_puerta:
            for k, (xv, yv, zv) in list(base.items()):
                xr, yr = _rotar_puerta_izquierda(xv, yv, angulo)
                base[k] = (xr, yr, zv)

        # Cara frontal del frente (y = d + espesor).
        add_polygon(target, [base["bfl"], base["bfr"], base["tfr"], base["tfl"]], clase_frente)
        # Cara lateral derecha visible.
        add_polygon(target, [base["bbr"], base["bfr"], base["tfr"], base["tbr"]], clase_frente)
        # Cara superior visible en esta proyección isométrica.
        add_polygon(target, [base["tbl"], base["tbr"], base["tfr"], base["tfl"]], clase_frente)

    def _draw_front(tipo_frente: str, z_inf: float, z_sup: float) -> None:
        if tipo_frente == "puerta":
            _agregar_prisma_frente(puertas_svg, z_inf, z_sup, es_puerta=True, angulo=math.radians(35.0))
            return
        _agregar_prisma_frente(cajones_svg, z_inf, z_sup, es_puerta=False, angulo=0.0)

    # 3) Patas.
    _draw_leg_prisms(
        target=patas_svg,
        tipo_mueble=tipo_mueble,
        num_patas=num_patas,
        altura_patas_mm=altura_patas_real,
        ancho_mm=w,
        fondo_mm=d,
        add_polygon=add_polygon,
        clase=clase_cara,
        espesor_mm=espesor_mm,
        z0=z0,
        hay_frentes=hay_frentes,
    )

    # 4) Frentes opacos con el nuevo modelo.
    if total_frentes > 0:
        alto_util = max(40.0, h)
        alturas = _parse_dimensions_portes(dimensions_portes, total_frentes, alto_util)

        suma_alturas = sum(alturas)
        if suma_alturas <= 0:
            alturas = [alto_util / total_frentes for _ in range(total_frentes)]
        else:
            factor = alto_util / suma_alturas
            alturas = [a * factor for a in alturas]

        bloques = _build_front_stack(
            total_frentes=total_frentes,
            num_tiroirs=num_tiroirs,
            num_blocs_coulissants=num_blocs_coulissants,
            num_puertas=num_puertas,
            num_faux_tiroirs_bandeau=num_faux_tiroirs_bandeau,
            fallback_cajones=num_cajones,
        )

        z_cursor = z0
        for tipo_bloque, alto_bloque in zip(bloques, alturas):
            z_next = min(z1, z_cursor + alto_bloque)
            if z_next <= z_cursor:
                continue
            _draw_front(tipo_bloque, z_cursor, z_next)
            z_cursor = z_next

    # 5) Solo aristas visibles útiles.
    aristas_visibles = [
        ((w, 0, z1), (w, d, z1)),
        ((x_panel_interior, d, z1), (w, d, z1)),
        ((x_panel_interior, d, z0), (w, d, z0)),
        ((w, d, z0), (w, d, z1)),
        ((w, 0, z0), (w, 0, z1)),
        ((0, d, z1), (0, 0, z1)),
    ]

    for p1, p2 in aristas_visibles:
        add_line(p1, p2)

    if min_x == float("inf"):
        min_x, min_y, max_x, max_y = 0.0, 0.0, 100.0, 100.0

    margen_x = 56.0
    margen_y_arriba = 62.0
    margen_y_abajo = 62.0

    vb_x = min_x - margen_x
    vb_y = min_y - margen_y_arriba
    vb_w = (max_x - min_x) + (2 * margen_x)
    vb_h = (max_y - min_y) + margen_y_arriba + margen_y_abajo

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">',
        "<style>",
        f'.{clase_cara}{{fill:{color_relleno};stroke:{color_linea};stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round;}}',
        f'.{clase_frente}{{fill:#FFFFFF;stroke:#111111;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round;}}',
        f'.{clase_linea}{{fill:none;stroke:{color_linea};stroke-width:2.0;stroke-linejoin:round;stroke-linecap:round;}}',
        "</style>",
        *patas_svg,
        *caras,
        *base_svg,
        *interior_svg,
        *lateral_derecho_svg,
        *cajones_svg,
        *puertas_svg,
        *tapa_svg,
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
        num_tiroirs=row.get("num_tiroirs", 0),
        num_blocs_coulissants=row.get("num_blocs_coulissants", 0),
        num_faux_tiroirs_bandeau=row.get("num_faux_tiroirs_bandeau", 0),
        num_facades=row.get("num_facades", 0),
        dimensions_portes=row.get("dimensions_portes"),
        num_patas=row.get("num_patas", 0),
        altura_patas=row.get("altura_patas", 0),
        tipo_mueble=row.get("tipo_mueble", "S"),
    )


def _build_front_stack(
    total_frentes: int,
    num_tiroirs: int,
    num_blocs_coulissants: int,
    num_puertas: int,
    num_faux_tiroirs_bandeau: int,
    fallback_cajones: int,
) -> list[str]:
    if total_frentes <= 0:
        return []

    stack = (
        ["tiroir"] * _to_non_negative_int(num_tiroirs)
        + ["bloc_coulissant"] * _to_non_negative_int(num_blocs_coulissants)
        + ["puerta"] * _to_non_negative_int(num_puertas)
        + ["faux_tiroir"] * _to_non_negative_int(num_faux_tiroirs_bandeau)
    )

    if not stack:
        stack = ["tiroir"] * _to_non_negative_int(fallback_cajones) + ["puerta"] * _to_non_negative_int(num_puertas)

    if len(stack) < total_frentes:
        faltan = total_frentes - len(stack)
        stack.extend(["puerta"] * min(faltan, _to_non_negative_int(num_puertas)))
        faltan = total_frentes - len(stack)
        if faltan > 0:
            stack.extend(["tiroir"] * faltan)

    return stack[:total_frentes]


def _parse_dimensions_portes(
    dimensions_portes: str | list[str] | None,
    total_frentes: int,
    alto_mm: float,
) -> list[float]:
    if total_frentes <= 0:
        return []

    alturas = _parse_alturas_portes(dimensions_portes)
    if not alturas:
        base = max(80.0, alto_mm / total_frentes)
        return [_redondear_decena(base) for _ in range(total_frentes)]

    if len(alturas) > total_frentes:
        alturas = alturas[:total_frentes]

    if len(alturas) < total_frentes:
        faltan = total_frentes - len(alturas)
        base = max(40.0, (alto_mm - sum(alturas)) / max(1, faltan))
        alturas.extend([_redondear_decena(base) for _ in range(faltan)])

    return [max(40.0, _redondear_decena(h)) for h in alturas[:total_frentes]]


def _draw_leg_prisms(
    target: list[str],
    tipo_mueble: str,
    num_patas: int,
    altura_patas_mm: float,
    ancho_mm: float,
    fondo_mm: float,
    add_polygon: Any,
    clase: str,
    espesor_mm: float,
    z0: float,
    hay_frentes: bool,
) -> None:
    if tipo_mueble != "P" or num_patas <= 0 or altura_patas_mm <= 0:
        return

    margen = min(80.0, max(24.0, min(ancho_mm, fondo_mm) * 0.2))
    size = max(10.0, min(espesor_mm * 0.8, 24.0))

    y_del = margen
    y_tras = max(margen, fondo_mm - margen - size)

    if num_patas <= 4:
        xs = [margen, max(margen, ancho_mm - margen - size)]
        posiciones = [(xs[0], y_del), (xs[1], y_del), (xs[0], y_tras), (xs[1], y_tras)][:num_patas]
    else:
        per_row = max(2, math.ceil(num_patas / 2))
        x_min = margen
        x_max = max(x_min, ancho_mm - margen - size)
        if per_row == 1:
            xs = [x_min]
        else:
            paso = (x_max - x_min) / (per_row - 1) if per_row > 1 else 0.0
            xs = [x_min + i * paso for i in range(per_row)]
        posiciones = [(x, y_del) for x in xs] + [(x, y_tras) for x in xs]
        posiciones = posiciones[:num_patas]

    z_inf = 0.0
    z_sup = min(altura_patas_mm, z0)
    if z_sup <= z_inf:
        return

    # Dibujar primero patas traseras para mejorar la oclusión visual.
    posiciones.sort(key=lambda p: p[1])

    for x, y in posiciones:
        x2 = min(ancho_mm, x + size)
        y2 = min(fondo_mm, y + size)

        # Ocultación por frentes: la cara frontal queda detrás de paneles frontales.
        ocultar_frente = hay_frentes and y2 > (fondo_mm - espesor_mm)

        if not ocultar_frente:
            add_polygon(target, [(x, y2, z_inf), (x2, y2, z_inf), (x2, y2, z_sup), (x, y2, z_sup)], clase)

        # Solo cara lateral exterior visible, evitando caras internas.
        centro_x = x + (x2 - x) * 0.5
        if centro_x >= (ancho_mm * 0.5):
            add_polygon(target, [(x2, y, z_inf), (x2, y2, z_inf), (x2, y2, z_sup), (x2, y, z_sup)], clase)
        else:
            add_polygon(target, [(x, y, z_inf), (x, y2, z_inf), (x, y2, z_sup), (x, y, z_sup)], clase)


def _parse_alturas_portes(dimensions_portes: str | list[str] | None) -> list[float]:
    if not dimensions_portes:
        return []

    if isinstance(dimensions_portes, list):
        partes = [str(v) for v in dimensions_portes]
    else:
        partes = [p.strip() for p in re.split(r"[\n;,]+", str(dimensions_portes)) if p.strip()]

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
    return "P" if str(tipo_mueble or "S").strip().upper() == "P" else "S"


if __name__ == "__main__":
    svg = generar_svg_mueble(
        ancho_mm=600,
        alto_mm=800,
        fondo_mm=375,
        num_baldas=2,
        num_puertas=1,
        num_tiroirs=1,
        num_blocs_coulissants=1,
        num_faux_tiroirs_bandeau=0,
        num_facades=3,
        dimensions_portes="450 * 200\n450 * 300\n450 * 280",
        num_patas=4,
        altura_patas=100,
        tipo_mueble="P",
    )
    with open("mueble.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("SVG generado en mueble.svg")
