import streamlit as st

from svg import generar_svg_mueble


st.set_page_config(page_title="Generador de miniaturas de muebles", layout="centered")

st.title("Generador de miniaturas de muebles")

nombre_mueble = st.text_input("Nombre del mueble", value="miniatura_mueble")
ancho_mm = st.number_input("Ancho (mm)", min_value=1.0, value=600.0, step=1.0)
alto_mm = st.number_input("Alto (mm)", min_value=1.0, value=1200.0, step=1.0)
fondo_mm = st.number_input("Fondo (mm)", min_value=1.0, value=300.0, step=1.0)
num_baldas = int(st.number_input("Cantidad de baldas", min_value=0, value=2, step=1))

if st.button("Generar miniatura"):
    svg_mueble = generar_svg_mueble(
        ancho_mm=ancho_mm,
        alto_mm=alto_mm,
        fondo_mm=fondo_mm,
        num_baldas=num_baldas,
    )

    st.components.v1.html(svg_mueble, height=700, scrolling=True)

    nombre_archivo = f"{(nombre_mueble or 'miniatura_mueble').strip() or 'miniatura_mueble'}.svg"
    st.download_button(
        label="Descargar SVG",
        data=svg_mueble,
        file_name=nombre_archivo,
        mime="image/svg+xml",
    )
