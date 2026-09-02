"""
Keynes Agent — interfaz web con Streamlit.

Ejecutar desde la carpeta del proyecto:
    streamlit run app.py
"""

from pathlib import Path
import os
import altair as alt
import pandas as pd
import pycountry
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from vega_datasets import data
from Keynes_agent import process_response
from basic_memory import BasicMemory

load_dotenv()

st.set_page_config(
    page_title="Keynes Agente",
    page_icon="static/mark.svg",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- Hoja de estilo ---
# La ruta se ancla al archivo, no al directorio de ejecucion.
CSS = Path(__file__).parent / "static" / "keynes.css"
if CSS.exists():
    st.html(f"<style>{CSS.read_text()}</style>")


def eyebrow(texto: str) -> None:
    """Etiqueta de seccion en mayusculas pequenas."""
    st.html(f'<div class="k-eyebrow">{texto}</div>')

def dibujar_grafico(datos: dict) -> None:
    """Renderiza un resultado de graficar_bm como grafico interactivo."""
    df = pd.DataFrame(datos["serie"])
    df.columns = ["Año", "Valor"]

    etiqueta = datos.get("indicador_nombre", datos.get("indicador", ""))

    with st.container(border=True):
        st.markdown(f"**{etiqueta}**")
        st.html(
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:10.5px;'
            f'color:#9ca3af">{datos["pais"]} · {datos["periodo"]}</span>'
        )

        chart = (
            alt.Chart(df)
            .mark_line(strokeWidth=2, point=True)
            .encode(
                x=alt.X("Año:O", axis=alt.Axis(title=None, labelAngle=0,
                                               domainColor="#e6e6e2", ticks=False)),
                y=alt.Y("Valor:Q", axis=alt.Axis(title=None, grid=True,
                                                 gridColor="#f0f0ec", domain=False)),
                tooltip=["Año", alt.Tooltip("Valor:Q", format=",.2f")],
            )
            .properties(height=260)
            .configure_mark(color="#111827")
            .configure_view(stroke=None)
            .configure_axis(labelFont="Archivo", labelColor="#9ca3af", labelFontSize=11)
        )
        st.altair_chart(chart, use_container_width=True)

        st.download_button(
            "Descargar CSV",
            df.to_csv(index=False).encode(),
            file_name=f"{datos['indicador']}_{datos['pais']}.csv",
            mime="text/csv",
        )
def dibujar_comparacion(datos: dict) -> None:
    """Renderiza un resultado de comparar_paises como grafico multilinea."""
    df = pd.DataFrame(datos["serie"])
    df.columns = ["País", "Año", "Valor"]

    etiqueta = datos.get("indicador_nombre", datos.get("indicador", ""))

    with st.container(border=True):
        st.markdown(f"**{etiqueta}**")
        st.html(
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:10.5px;'
            f'color:#9ca3af">{" · ".join(datos["paises"])}</span>'
        )

        chart = (
            alt.Chart(df)
            .mark_line(strokeWidth=2, point=True)
            .encode(
                x=alt.X("Año:O", axis=alt.Axis(title=None, labelAngle=0,
                                               domainColor="#e6e6e2", ticks=False)),
                y=alt.Y("Valor:Q", axis=alt.Axis(title=None, grid=True,
                                                 gridColor="#f0f0ec", domain=False)),
                color=alt.Color("País:N", legend=alt.Legend(title=None, orient="top")),
                tooltip=["País", "Año", alt.Tooltip("Valor:Q", format=",.2f")],
            )
            .properties(height=280)
            .configure_view(stroke=None)
            .configure_axis(labelFont="Archivo", labelColor="#9ca3af", labelFontSize=11)
        )
        st.altair_chart(chart, use_container_width=True)

        st.download_button(
            "Descargar CSV",
            df.to_csv(index=False).encode(),
            file_name=f"{datos['indicador']}_comparacion.csv",
            mime="text/csv",
            key=f"csv_{datos['indicador']}_{len(st.session_state.historial)}",
        )
def dibujar_ficha(datos: dict) -> None:
    """Renderiza un resultado de ficha_pais como grilla de metricas."""
    with st.container(border=True):
        num = codigo_numerico(datos.get("codigo", ""))

        col_mapa, col_txt = st.columns([1, 12], vertical_alignment="center")

        with col_mapa:
            if num is not None:
                paises = alt.topo_feature(data.world_110m.url, "countries")
                mapa = (
                    alt.Chart(paises)
                    .mark_geoshape(fill="#111827", stroke="#111827", strokeWidth=1.5)
                    .transform_filter(alt.datum.id == num)
                    .project("mercator")
                    .properties(width=54, height=76)
                    .configure_view(stroke=None)
                )
                st.altair_chart(mapa, use_container_width=False)

        with col_txt:
            st.html(
                f'<div style="font-family:\'Source Serif 4\',Georgia,serif;'
                f'font-size:24px;font-weight:600;line-height:1.2;margin-bottom:4px">'
                f'{datos["pais"]}</div>'
            )
            st.html(
                '<span style="font-family:\'JetBrains Mono\',monospace;font-size:13px;'
                'color:#9ca3af">PERFIL MACROECONÓMICO</span>'
            )

        st.write("")

        metricas = datos["metricas"]
        for i in range(0, len(metricas), 4):
            fila = metricas[i:i + 4]
            cols = st.columns(4)
            for col, m in zip(cols, fila):
                with col:
                    valor = formatear(m["valor"], m["indicador"])

                    delta = None
                    if m["valor_previo"] is not None:
                        cambio = m["valor"] - m["valor_previo"]
                        signo = "+" if cambio >= 0 else "−"
                        delta = f"{signo}{formatear(abs(cambio), m['indicador'])}"

                    st.metric(
                        label=f"{m['nombre']} · {m['anio']}",
                        value=valor,
                        delta=delta,
                        delta_color="inverse" if m["inverso"] else "normal",
                    )

        st.html('<div class="k-source">Fuente: Banco Mundial · WDI</div>')
def formatear(valor: float, indicador: str) -> str:
    """Da formato legible segun la magnitud del indicador."""
    if abs(valor) >= 1e9:
        return f"{valor / 1e9:,.1f} mil M"  # miles de millones
    if abs(valor) >= 1e6:
        return f"{valor / 1e6:,.1f} M"
    if abs(valor) >= 1000:
        return f"{valor:,.0f}"
    return f"{valor:,.2f}"
def dibujar_visual(v: dict) -> None:
    """Despacha al render correcto segun el tipo de resultado."""
    tipo = v.get("tipo")
    if tipo == "comparacion":
        dibujar_comparacion(v)
    elif tipo == "ficha":
        dibujar_ficha(v)
    elif tipo == "sectores":
        dibujar_sectores(v)
    elif tipo == "mapa":
        dibujar_mapa(v)
    else:
        dibujar_grafico(v)

def codigo_numerico(iso3: str):
    """Convierte ISO3 alfabetico al numerico que usa world-atlas."""
    try:
        return int(pycountry.countries.get(alpha_3=iso3.upper()).numeric)
    except (AttributeError, ValueError, TypeError):
        return None
def dibujar_sectores(datos: dict) -> None:
    """Renderiza la composicion sectorial del PIB como barras horizontales."""
    df = pd.DataFrame(datos["sectores"])
    df.columns = ["Sector", "Porcentaje", "Año"]

    with st.container(border=True):
        st.markdown(f"**Composición del PIB · {datos['pais']}**")
        st.html(
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:10.5px;'
            f'color:#9ca3af">{datos["anio"]} · % DEL PIB</span>'
        )

        chart = (
            alt.Chart(df)
            .mark_bar(color="#111827", cornerRadiusEnd=2)
            .encode(
                x=alt.X("Porcentaje:Q", axis=alt.Axis(title=None, grid=True,
                                                      gridColor="#f0f0ec", domain=False)),
                y=alt.Y("Sector:N", sort="-x", axis=alt.Axis(title=None, domain=False,
                                                             ticks=False)),
                tooltip=["Sector", alt.Tooltip("Porcentaje:Q", format=",.1f")],
            )
            .properties(height=140)
            .configure_view(stroke=None)
            .configure_axis(labelFont="Archivo", labelColor="#9ca3af", labelFontSize=11)
        )
        st.altair_chart(chart, use_container_width=True)
def dibujar_mapa(datos: dict) -> None:
    """Renderiza un indicador como mapa coropletico."""
    filas = []
    for v in datos["valores"]:
        num = codigo_numerico(v["codigo"])
        if num is not None:
            filas.append({"id": num, "País": v["pais"], "Valor": v["valor"]})

    if not filas:
        st.warning("No se pudo ubicar geográficamente ningún país.")
        return

    df = pd.DataFrame(filas)
    etiqueta = datos.get("indicador_nombre", datos.get("indicador", ""))
    anio = datos["valores"][0]["anio"]

    paises = alt.topo_feature(data.world_110m.url, "countries")

    with st.container(border=True):
        st.markdown(f"**{etiqueta}**")
        st.html(
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:10.5px;'
            f'color:#9ca3af">{anio} · {len(filas)} PAÍSES</span>'
        )

        mapa = (
            alt.Chart(paises)
            .mark_geoshape(stroke="#ffffff", strokeWidth=0.6)
            .transform_lookup(
                lookup="id",
                from_=alt.LookupData(df, "id", ["País", "Valor"])
            )
            .transform_filter("isValid(datum.Valor)")
            .encode(
                color=alt.Color("Valor:Q",
                                scale=alt.Scale(scheme="blues"),
                                legend=alt.Legend(title=None, orient="right")),
                tooltip=["País:N", alt.Tooltip("Valor:Q", format=",.2f")],
            )
            .project("naturalEarth1")
            .properties(height=340)
            .configure_view(stroke=None)
        )
        st.altair_chart(mapa, use_container_width=True)
# --- Barra lateral ---
with st.sidebar:
    logo = Path(__file__).parent / "static" / "logo.svg"

    if logo.exists():
        with st.container(key="sidebar_logo"):
            st.image(str(logo), width=190)

    eyebrow("Fuentes")

    st.markdown(
        "Banco Mundial · WDI  \n"
        "exchangerate-api.com \n"
    )

    st.divider()

    eyebrow("Ejemplos")

    EJEMPLOS = [
        "Dame el panorama económico de Guatemala",
        "PIB per cápita de Guatemala en quetzales",
        "Compara la inflación de Guatemala, México y Costa Rica",
        "Muéstrame el PIB per cápita de Centroamérica en un mapa",
        "¿De qué vive la economía de Guatemala?",
    ]

    with st.container(key="chips"):
        for i, ej in enumerate(EJEMPLOS):
            if st.button(ej, key=f"ej_{i}", use_container_width=True):
                st.session_state.pregunta_pendiente = ej

    st.divider()

    st.caption(
        "Creado por [Carlos Lahoud](https://www.linkedin.com/in/carlos-lahoud/) y Streamlit."
    )

# Espacio superior del chat
st.html('<div style="height: 28px;"></div>')

# --- Estado que sobrevive entre interacciones ---
if "client" not in st.session_state:
    st.session_state.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
if "memory" not in st.session_state:
    st.session_state.memory = BasicMemory(max_messages=10)
if "historial" not in st.session_state:
    st.session_state.historial = []

# --- Repintar la conversación previa ---
for msg in st.session_state.historial:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["texto"])
        for v in msg.get("graficos", []):
            dibujar_visual(v)


# --- Entrada nueva ---
pregunta = st.chat_input("Pregunta algo...")
if st.session_state.get("pregunta_pendiente"):
    pregunta = st.session_state.pop("pregunta_pendiente")

if pregunta:
    # Guardar mensaje del usuario
    st.session_state.historial.append({
        "rol": "user",
        "texto": pregunta
    })

    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando fuentes..."):
            respuesta, resultados = process_response(
                st.session_state.client,
                st.session_state.memory.messages(),
                pregunta,
            )

        st.markdown(respuesta)

        visuales = [r["resultado"] for r in resultados
                    if r["resultado"].get("tipo") in ("grafico", "comparacion", "ficha", "sectores", "mapa")]
        for v in visuales:
            dibujar_visual(v)

    st.session_state.historial.append({
        "rol": "assistant",
        "texto": respuesta,
        "graficos": visuales
    })

    st.session_state.memory.add("user", pregunta)
    st.session_state.memory.add("assistant", respuesta)