from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import uuid4


@dataclass
class MuebleSVGInput:
    ancho_mm: float
    alto_mm: float
    fondo_mm: float
    num_baldas: int = 0
    con_puerta: bool = False
    apertura_puerta_px: float = 45.0
    espesor_mm: float = 19.0
    color_hex: str = "#FFFFFF"


def generar_svg_mueble(
    ancho_mm: float,
    alto_mm: float,
    fondo_mm: float,
    num_baldas: int = 0,
    con_puerta: bool = False,
    apertura_puerta_px: float = 45.0,
    espesor_mm: float = 19.0,
    color_hex: str = "#FFFFFF",
) -> str:
    """
    Genera un SVG de mueble abierto paramétrico.
    Si con_puerta=True, superpone una puerta abierta por delante sin
    modificar la estructura base del mueble.

    Reglas:
    - Base geométrica tomada del generador de mueble abierto
    - Espesor tablero por defecto: 19 mm
    - La puerta se superpone por delante
    - La estructura del mueble no se redibuja ni se altera
    """

    _validar_inputs(
        ancho_mm=ancho_mm,
        alto_mm=alto_mm,
        fondo_mm=fondo_mm,
        num_baldas=num_baldas,
        espesor_mm=espesor_mm,
    )

    color_relleno = _normalizar_hex(color_hex)
    color_linea = _color_contraste(color_relleno)

    uid = uuid4().hex[:8]
    clase_relleno = f"f_{uid}"
    clase_linea = f"s_{uid}"

    # =========================================================
    # PROYECCION
    # =========================================================
    x0 = 170.0
    y0 = 110.0

    px_por_mm_x = 0.50
    px_por_mm_y = 0.525

    # Vista ligeramente frontal
    fondo_dx_por_mm = 0.152
    fondo_dy_por_mm = 0.061

    ancho_px = ancho_mm * px_por_mm_x
    alto_px = alto_mm * px_por_mm_y
    dx_fondo = fondo_mm * fondo_dx_por_mm
    dy_fondo = fondo_mm * fondo_dy_por_mm

    espesor_px_y = max(10.0, espesor_mm * px_por_mm_y)
    espesor_px_x = max(10.0, espesor_mm * px_por_mm_x)

    # =========================================================
    # PUNTOS EXTERIORES
    # =========================================================
    x_front_left = x0
    y_front_top = y0

    x_front_right = x_front_left + ancho_px
    x_back_left = x_front_left + dx_fondo
    x_back_right = x_front_right + dx_fondo

    y_back = y_front_top - dy_fondo
    y_suelo = y_front_top + alto_px

    # =========================================================
    # CARAS INTERIORES
    # =========================================================
    x_inner_left_front = x_front_left + espesor_px_x
    x_inner_right_front = x_front_right - espesor_px_x
    x_inner_back_left = x_back_left + espesor_px_x
    x_right_side_outer_back = x_back_right

    # =========================================================
    # TAPA
    # =========================================================
    y_tapa_top_front = y_front_top
    y_tapa_bottom_front = y_tapa_top_front + espesor_px_y

    y_tapa_top_back = y_back
    y_tapa_bottom_back = y_tapa_top_back + espesor_px_y

    # =========================================================
    # BASE
    # =========================================================
    y_base_bottom_front = y_suelo
    y_base_top_front = y_base_bottom_front - espesor_px_y

    y_base_bottom_back = y_base_bottom_front - dy_fondo
    y_base_top_back = y_base_top_front - dy_fondo

    # =========================================================
    # BALDAS EQUIDISTANTES
    # =========================================================
    hueco_libre_front = y_base_top_front - y_tapa_bottom_front
    separacion_front = hueco_libre_front / (num_baldas + 1) if num_baldas > 0 else 0.0

    baldas: list[dict[str, float]] = []
    for i in range(num_baldas):
        y_sup_front = y_tapa_bottom_front + separacion_front * (i + 1)
        y_inf_front = y_sup_front + espesor_px_y

        y_sup_back = y_sup_front - dy_fondo
        y_inf_back = y_inf_front - dy_fondo

        baldas.append(
            {
                "y_sup_front": y_sup_front,
                "y_inf_front": y_inf_front,
                "y_sup_back": y_sup_back,
                "y_inf_back": y_inf_back,
            }
        )

    # =========================================================
    # PIEZA TRASERA
    # =========================================================
    x_trasera_left = x_inner_back_left
    x_trasera_right = x_back_right - espesor_px_x
    y_trasera_top = y_tapa_bottom_back
    y_trasera_bottom = y_base_top_back

    # =========================================================
    # COLECCIONES SVG
    # =========================================================
    rellenos: list[str] = []
    lineas: list[str] = []

    def add_line(x1: float, y1: float, x2: float, y2: float, clase: str | None = None) -> None:
        if clase is None:
            clase = clase_linea
        lineas.append(
            f'<line class="{clase}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
        )

    def add_polygon(puntos: list[tuple[float, float]], clase: str | None = None) -> None:
        if clase is None:
            clase = clase_relleno
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in puntos)
        rellenos.append(f'<polygon class="{clase}" points="{p}"/>')

    # =========================================================
    # RELLENOS - MUEBLE ABIERTO
    # =========================================================
    # Tapa superior
    add_polygon(
        [
            (x_front_left, y_tapa_top_front),
            (x_front_right, y_tapa_top_front),
            (x_back_right, y_tapa_top_back),
            (x_back_left, y_tapa_top_back),
        ]
    )

    # Espesores visibles de la tapa
    add_polygon(
        [
            (x_front_left, y_tapa_top_front),
            (x_inner_left_front, y_tapa_top_front),
            (x_inner_left_front, y_tapa_bottom_front),
            (x_front_left, y_tapa_bottom_front),
        ]
    )
    add_polygon(
        [
            (x_inner_left_front, y_tapa_top_front),
            (x_back_left, y_tapa_top_back),
            (x_inner_back_left, y_tapa_top_back),
            (x_inner_left_front, y_tapa_bottom_front),
        ]
    )
    add_polygon(
        [
            (x_inner_right_front, y_tapa_top_front),
            (x_front_right, y_tapa_top_front),
            (x_front_right, y_tapa_bottom_front),
            (x_inner_right_front, y_tapa_bottom_front),
        ]
    )
    add_polygon(
        [
            (x_inner_right_front, y_tapa_top_front),
            (x_front_right, y_tapa_top_front),
            (x_back_right, y_tapa_top_back),
            (x_back_right - espesor_px_x, y_tapa_top_back),
        ]
    )

    # Laterales frontales
    add_polygon(
        [
            (x_front_left, y_tapa_top_front),
            (x_inner_left_front, y_tapa_top_front),
            (x_inner_left_front, y_suelo),
            (x_front_left, y_suelo),
        ]
    )
    add_polygon(
        [
            (x_inner_right_front, y_tapa_top_front),
            (x_front_right, y_tapa_top_front),
            (x_front_right, y_suelo),
            (x_inner_right_front, y_suelo),
        ]
    )

    # Lateral derecho exterior en perspectiva
    add_polygon(
        [
            (x_front_right, y_tapa_top_front),
            (x_back_right, y_tapa_top_back),
            (x_right_side_outer_back, y_suelo - dy_fondo),
            (x_front_right, y_suelo),
        ]
    )

    # Trasera interior
    add_polygon(
        [
            (x_trasera_left, y_trasera_top),
            (x_trasera_right, y_trasera_top),
            (x_trasera_right, y_trasera_bottom),
            (x_trasera_left, y_trasera_bottom),
        ]
    )

    # Lateral izquierdo interior
    add_polygon(
        [
            (x_inner_left_front, y_tapa_bottom_front),
            (x_inner_back_left, y_tapa_bottom_back),
            (x_inner_back_left, y_base_top_back),
            (x_inner_left_front, y_base_top_front),
        ]
    )

    # Base
    add_polygon(
        [
            (x_inner_left_front, y_base_top_front),
            (x_inner_right_front, y_base_top_front),
            (x_inner_right_front, y_base_top_back),
            (x_inner_back_left, y_base_top_back),
        ]
    )
    add_polygon(
        [
            (x_inner_left_front, y_base_top_front),
            (x_inner_right_front, y_base_top_front),
            (x_inner_right_front, y_base_bottom_front),
            (x_inner_left_front, y_base_bottom_front),
        ]
    )

    # Baldas
    for balda in baldas:
        add_polygon(
            [
                (x_inner_left_front, balda["y_sup_front"]),
                (x_inner_right_front, balda["y_sup_front"]),
                (x_inner_right_front, balda["y_sup_back"]),
                (x_inner_back_left, balda["y_sup_back"]),
            ]
        )
        add_polygon(
            [
                (x_inner_left_front, balda["y_sup_front"]),
                (x_inner_right_front, balda["y_sup_front"]),
                (x_inner_right_front, balda["y_inf_front"]),
                (x_inner_left_front, balda["y_inf_front"]),
            ]
        )

    # =========================================================
    # LINEAS - MUEBLE ABIERTO
    # =========================================================
    # Tapa
    add_line(x_front_left, y_tapa_top_front, x_front_right, y_tapa_top_front)
    add_line(x_front_right, y_tapa_top_front, x_back_right, y_tapa_top_back)
    add_line(x_front_left, y_tapa_top_front, x_back_left, y_tapa_top_back)
    add_line(x_back_left, y_tapa_top_back, x_back_right, y_tapa_top_back)

    add_line(x_inner_left_front, y_tapa_bottom_front, x_inner_right_front, y_tapa_bottom_front)
    add_line(x_inner_left_front, y_tapa_top_front, x_inner_left_front, y_tapa_bottom_front)
    add_line(x_inner_right_front, y_tapa_top_front, x_inner_right_front, y_tapa_bottom_front)

    # Lateral izquierdo
    add_line(x_front_left, y_tapa_top_front, x_front_left, y_suelo)
    add_line(x_inner_left_front, y_tapa_top_front, x_inner_left_front, y_suelo)
    add_line(x_front_left, y_suelo, x_inner_left_front, y_suelo)

    add_line(x_front_left, y_tapa_top_front, x_inner_left_front, y_tapa_top_front)
    add_line(x_inner_left_front, y_tapa_top_front, x_inner_back_left, y_tapa_top_back)
    add_line(x_back_left, y_tapa_top_back, x_inner_back_left, y_tapa_top_back)

    # Arista trasera derecha del lateral izquierdo, cortada por baldas
    inicio = y_tapa_bottom_front + 1.0

    if num_baldas > 0:
        fin = baldas[0]["y_sup_back"]
        if fin > inicio:
            add_line(x_inner_back_left, inicio, x_inner_back_left, fin)

        for i in range(num_baldas - 1):
            inicio_i = baldas[i]["y_inf_front"] + 1.0
            fin_i = baldas[i + 1]["y_sup_back"]
            if fin_i > inicio_i:
                add_line(x_inner_back_left, inicio_i, x_inner_back_left, fin_i)

        inicio_last = baldas[-1]["y_inf_front"] + 1.0
        fin_last = y_base_top_back
        if fin_last > inicio_last:
            add_line(x_inner_back_left, inicio_last, x_inner_back_left, fin_last)
    else:
        fin = y_base_top_back
        if fin > inicio:
            add_line(x_inner_back_left, inicio, x_inner_back_left, fin)

    # Lateral derecho
    add_line(x_front_right, y_tapa_top_front, x_front_right, y_suelo)
    add_line(x_inner_right_front, y_tapa_top_front, x_inner_right_front, y_suelo)
    add_line(x_inner_right_front, y_suelo, x_front_right, y_suelo)

    add_line(x_inner_right_front, y_tapa_top_front, x_front_right, y_tapa_top_front)
    add_line(x_inner_right_front, y_tapa_top_front, x_back_right - espesor_px_x, y_tapa_top_back)
    add_line(x_back_right - espesor_px_x, y_tapa_top_back, x_back_right, y_tapa_top_back)
    add_line(x_front_right, y_tapa_top_front, x_back_right, y_tapa_top_back)

    add_line(x_right_side_outer_back, y_tapa_top_back, x_right_side_outer_back, y_suelo - dy_fondo)
    add_line(x_front_right, y_suelo, x_right_side_outer_back, y_suelo - dy_fondo)

    # Baldas
    for balda in baldas:
        add_line(x_inner_left_front, balda["y_sup_front"], x_inner_right_front, balda["y_sup_front"])
        add_line(x_inner_left_front, balda["y_sup_front"], x_inner_back_left, balda["y_sup_back"])
        add_line(x_inner_back_left, balda["y_sup_back"], x_inner_right_front, balda["y_sup_back"])

        add_line(x_inner_left_front, balda["y_inf_front"], x_inner_right_front, balda["y_inf_front"])
        add_line(x_inner_left_front, balda["y_sup_front"], x_inner_left_front, balda["y_inf_front"])
        add_line(x_inner_right_front, balda["y_sup_front"], x_inner_right_front, balda["y_inf_front"])

    # Base
    add_line(x_inner_left_front, y_base_top_front, x_inner_right_front, y_base_top_front)
    add_line(x_inner_left_front, y_base_top_front, x_inner_back_left, y_base_top_back)
    add_line(x_inner_back_left, y_base_top_back, x_inner_right_front, y_base_top_back)

    add_line(x_inner_left_front, y_base_bottom_front, x_inner_right_front, y_base_bottom_front)
    add_line(x_inner_left_front, y_base_top_front, x_inner_left_front, y_base_bottom_front)
    add_line(x_inner_right_front, y_base_top_front, x_inner_right_front, y_base_bottom_front)

    # =========================================================
    # PUERTA SUPERPUESTA OPCIONAL
    # =========================================================
    if con_puerta:
        # Apertura visual: cuanto más pequeño el valor final, más abierta
        x_puerta_dcha_sup = x_front_right - apertura_puerta_px
        x_puerta_dcha_inf = x_front_right - apertura_puerta_px

        # Cara frontal de la puerta
        add_polygon(
            [
                (x_front_left, y_front_top),
                (x_puerta_dcha_sup, y_front_top + 30.0),
                (x_puerta_dcha_inf, y_suelo + 30.0),
                (x_front_left, y_suelo),
            ]
        )

        add_line(x_front_left, y_front_top, x_puerta_dcha_sup, y_front_top + 30.0)
        add_line(x_puerta_dcha_sup, y_front_top + 30.0, x_puerta_dcha_inf, y_suelo + 30.0)
        add_line(x_puerta_dcha_inf, y_suelo + 30.0, x_front_left, y_suelo)
        add_line(x_front_left, y_suelo, x_front_left, y_front_top)

        # Espesor puerta hacia delante, visible por el lado derecho
        # Se proyecta con la misma lógica de profundidad.
        # Ajuste visual leve para que el canto no quede demasiado fino.
        dx_puerta = max(espesor_mm * fondo_dx_por_mm, 4.2)
        dy_puerta = max(espesor_mm * fondo_dy_por_mm, 1.8)

        add_line(
            x_puerta_dcha_sup,
            y_front_top + 30.0,
            x_puerta_dcha_sup + dx_puerta,
            y_front_top + 30.0 - dy_puerta,
        )
        add_line(
            x_puerta_dcha_inf,
            y_suelo + 30.0,
            x_puerta_dcha_inf + dx_puerta,
            y_suelo + 30.0 - dy_puerta,
        )
        add_line(
            x_puerta_dcha_sup + dx_puerta,
            y_front_top + 30.0 - dy_puerta,
            x_puerta_dcha_inf + dx_puerta,
            y_suelo + 30.0 - dy_puerta,
        )

        # Canto superior visible
        add_line(
            x_front_left,
            y_front_top,
            x_front_left + dx_puerta,
            y_front_top - dy_puerta,
        )
        add_line(
            x_front_left + dx_puerta,
            y_front_top - dy_puerta,
            x_puerta_dcha_sup + dx_puerta,
            y_front_top + 30.0 - dy_puerta,
        )

    # =========================================================
    # VIEWBOX
    # =========================================================
    min_x = min(0.0, x_front_left - 110.0)
    min_y = min(0.0, y_back - 40.0)
    max_x = max(x_back_right + 120.0, x_front_right + 140.0)
    max_y = max(y_suelo + 120.0, y_base_bottom_front + 150.0)

    if con_puerta:
        max_x = max(max_x, x_front_right + 120.0)
        max_y = max(max_y, y_suelo + 140.0)

    view_w = max_x - min_x
    view_h = max_y - min_y

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:.1f} {min_y:.1f} {view_w:.1f} {view_h:.1f}">',
        "<style>",
        f'.{clase_relleno}{{fill:{color_relleno};stroke:none;}}',
        f'.{clase_linea}{{stroke:{color_linea};stroke-width:2.2;fill:none;stroke-linecap:round;stroke-linejoin:round;}}',
        "</style>",
        *rellenos,
        *lineas,
        "</svg>",
    ]
    return "\n".join(svg)


def _validar_inputs(
    ancho_mm: float,
    alto_mm: float,
    fondo_mm: float,
    num_baldas: int,
    espesor_mm: float,
) -> None:
    if ancho_mm <= 0:
        raise ValueError("ancho_mm debe ser mayor que 0.")
    if alto_mm <= 0:
        raise ValueError("alto_mm debe ser mayor que 0.")
    if fondo_mm <= 0:
        raise ValueError("fondo_mm debe ser mayor que 0.")
    if num_baldas < 0:
        raise ValueError("num_baldas no puede ser negativo.")
    if espesor_mm <= 0:
        raise ValueError("espesor_mm debe ser mayor que 0.")


def _normalizar_hex(color_hex: str) -> str:
    valor = str(color_hex).strip()
    if re.fullmatch(r"#([0-9a-fA-F]{6})", valor):
        return valor.upper()
    return "#FFFFFF"


def _color_contraste(hex_color: str) -> str:
    color = _normalizar_hex(hex_color)
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    luminancia = (0.299 * r) + (0.587 * g) + (0.114 * b)
    return "#111111" if luminancia >= 150 else "#F5F5F5"


if __name__ == "__main__":
    svg = generar_svg_mueble(
        ancho_mm=600,
        alto_mm=800,
        fondo_mm=375,
        num_baldas=2,
        con_puerta=True,
        apertura_puerta_px=45.0,
        espesor_mm=19.0,
        color_hex="#FFFFFF",
    )
    with open("mueble.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("SVG generado en mueble.svg")
