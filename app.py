import streamlit as st

from svg import generar_svg_mueble


st.set_page_config(page_title="Generador de miniaturas", layout="centered")
st.title("Generador de miniaturas de muebles")

nombre = st.text_input("Nombre", value="miniatura")
ancho_mm = st.number_input("Ancho en mm", min_value=1.0, value=600.0, step=1.0)
alto_mm = st.number_input("Alto en mm", min_value=1.0, value=1200.0, step=1.0)
fondo_mm = st.number_input("Fondo en mm", min_value=1.0, value=300.0, step=1.0)
num_baldas = int(st.number_input("Cantidad de baldas", min_value=0, value=2, step=1))

if st.button("Generar miniatura"):
    svg_generado = generar_svg_mueble(ancho_mm, alto_mm, fondo_mm, num_baldas)

    st.components.v1.html(svg_generado, height=700, scrolling=True)

    nombre_limpio = (nombre or "miniatura").strip() or "miniatura"
    st.download_button(
        label="Descargar SVG",
        data=svg_generado,
        file_name=f"{nombre_limpio}.svg",
        mime="image/svg+xml",
    )
