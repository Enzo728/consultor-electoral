"""Consultor Electoral España — interfaz Streamlit (PC/móvil)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
ENCUESTAS_PATH = BASE_DIR / "data" / "encuestas_limpias.json"
INFORME_PATH = BASE_DIR / "data" / "informe_ia.json"

PARTIDOS_KPI = ["PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF"]

st.set_page_config(
    page_title="Consultor Electoral España",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      div[data-testid="stMetric"] {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 12px; padding: 12px 14px;
      }
      div[data-testid="stMetricDelta"] > div { font-size: 0.95rem !important; }
      .kpi-title { font-size: 0.85rem; color: #64748b; margin-bottom: 2px; }
      @media (max-width: 768px) {
        .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
        h1 { font-size: 1.6rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
      }
      .chat-bubble-user {
        background: #1e4b8f; color: white; padding: 8px 12px;
        border-radius: 12px 12px 2px 12px; margin: 4px 0 4px 15%;
        max-width: 85%;
      }
      .chat-bubble-ia {
        background: #f1f5f9; color: #0f172a; padding: 8px 12px;
        border-radius: 12px 12px 12px 2px; margin: 4px 15% 4px 0;
        max-width: 85%;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False, ttl=60)
def cargar_encuestas() -> dict | None:
    if not ENCUESTAS_PATH.exists():
        return None
    return json.loads(ENCUESTAS_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False, ttl=60)
def cargar_informe() -> dict | None:
    if not INFORME_PATH.exists():
        return None
    return json.loads(INFORME_PATH.read_text(encoding="utf-8"))


def dataframe_evolucion(datos: dict) -> pd.DataFrame:
    ev = datos.get("evolucion", [])
    if not ev:
        return pd.DataFrame()
    df = pd.DataFrame(ev)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha")


def suavizar(df: pd.DataFrame, partidos: list[str], span: int = 12) -> pd.DataFrame:
    """Media móvil exponencial por partido (línea de tendencia)."""
    if df.empty:
        return df
    out = []
    for p in partidos:
        sub = df[df["partido"] == p][["fecha", "valor"]].dropna().sort_values("fecha")
        if sub.empty:
            continue
        s = sub.set_index("fecha")["valor"].ewm(span=span, adjust=False).mean()
        tmp = s.rename("tendencia").reset_index()
        tmp["partido"] = p
        out.append(tmp)
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True)


def color_de(datos: dict, partido: str) -> str:
    return (datos.get("colores") or {}).get(partido, "#64748B")


def ejecutar_actualizacion() -> tuple[bool, str]:
    """Ejecuta scraper.py y analizador_ia.py en vivo."""
    pasos = []
    for script in ("scraper.py", "analizador_ia.py"):
        ruta = BASE_DIR / script
        if not ruta.exists():
            return False, f"No se encuentra {script}"
        try:
            proc = subprocess.run(
                [sys.executable, str(ruta)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(BASE_DIR),
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return False, f"Timeout ejecutando {script}"
        if proc.returncode != 0:
            detalle = (proc.stderr or proc.stdout or "").strip()[-800:]
            return False, f"Error en {script}:\n{detalle}"
        pasos.append(f"✅ {script}")
    return True, "\n".join(pasos)


# ─────────────────────────── Sidebar ───────────────────────────
with st.sidebar:
    st.title("🗳️ Consultor Electoral")
    st.caption("Encuestas generales España · datos Wikipedia + Gemini")

    if st.button("🔄 Actualizar datos ahora", type="primary", use_container_width=True):
        with st.status("Actualizando datos…", expanded=True) as status:
            st.write("1/2 Extrayendo y filtrando encuestas (scraper)…")
            ok, msg = ejecutar_actualizacion()
            if ok:
                st.write("2/2 Generando informe con Gemini…")
                status.update(label="¡Datos actualizados!", state="complete")
                st.success(msg)
                cargar_encuestas.clear()
                cargar_informe.clear()
            else:
                status.update(label="Error en la actualización", state="error")
                st.error(msg)

    st.divider()
    datos_side = cargar_encuestas()
    if datos_side:
        st.caption(f"Datos: {datos_side.get('actualizado', '—')}")
        f = datos_side.get("filtros", {})
        st.caption(
            f"Incluidas: {f.get('total_incluidas', '?')} · "
            f"Excluidas: {f.get('total_excluidas', '?')} (CIS/muestra)"
        )
    informe_side = cargar_informe()
    if informe_side:
        st.caption(f"Informe IA: {informe_side.get('generado_en', '—')}")

    st.divider()
    st.caption(
        "Filtros anti-sesgo: sin CIS, muestra ≥ 800, "
        "media ponderada exp(−λt)·√n."
    )

# ─────────────────────────── Cabecera ───────────────────────────
st.title("Consultor Electoral España")
st.caption(
    "Estimaciones de intención de voto · Congreso · "
    f"actualizado {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)

datos = cargar_encuestas()
if datos is None:
    st.warning(
        "Aún no hay datos. Pulsa **«Actualizar datos ahora»** en la barra lateral "
        "o ejecuta `python scraper.py && python analizador_ia.py`."
    )
    st.stop()

# ─────────────────────────── KPIs ───────────────────────────
act = datos.get("medias_actual_14d") or datos.get("medias") or {}
ant = datos.get("medias_sem_anterior_14_28d") or {}

kpi_partidos = [p for p in PARTIDOS_KPI if p in act] or sorted(act, key=act.get, reverse=True)[:6]
cols = st.columns(min(len(kpi_partidos), 7))
for i, p in enumerate(kpi_partidos[:7]):
    with cols[i]:
        delta = None
        if p in ant:
            delta = round(act[p] - ant[p], 2)
        st.metric(
            label=p,
            value=f"{act[p]:.1f}%",
            delta=f"{delta:+.1f} pp vs sem. ant." if delta is not None else None,
            delta_color="normal",
        )

st.caption(
    "Media actual: últimos 14 días · Referencia: días 14–28 · "
    "ponderada por recencia y √muestra."
)

# ─────────────────────────── Gráfico ───────────────────────────
st.subheader("📈 Evolución temporal y tendencia")

df = dataframe_evolucion(datos)
partidos_disp = sorted(
    df["partido"].unique().tolist(),
    key=lambda p: (p not in PARTIDOS_KPI, PARTIDOS_KPI.index(p) if p in PARTIDOS_KPI else 99, p),
) if not df.empty else []

seleccion = st.multiselect(
    "Partidos",
    options=partidos_disp,
    default=[p for p in PARTIDOS_KPI if p in partidos_disp] or partidos_disp[:5],
)

if df.empty or not seleccion:
    st.info("Sin series temporales para mostrar.")
else:
    df_sel = df[df["partido"].isin(seleccion)]
    tend = suavizar(df_sel, seleccion)

    fig = go.Figure()
    for p in seleccion:
        color = color_de(datos, p)
        sub = df_sel[df_sel["partido"] == p]
        fig.add_trace(
            go.Scatter(
                x=sub["fecha"],
                y=sub["valor"],
                mode="markers",
                name=p,
                marker=dict(color=color, size=6, opacity=0.35),
                legendgroup=p,
                showlegend=False,
                hovertemplate=f"{p}: %{{y:.1f}}%<extra>{sub['encuestadora'].iloc[0] if len(sub) else ''}</extra>",
            )
        )
        tsub = tend[tend["partido"] == p] if not tend.empty else pd.DataFrame()
        if not tsub.empty:
            fig.add_trace(
                go.Scatter(
                    x=tsub["fecha"],
                    y=tsub["tendencia"],
                    mode="lines",
                    name=p,
                    line=dict(color=color, width=3),
                    legendgroup=p,
                    hovertemplate=f"{p} tendencia: %{{y:.1f}}%<extra></extra>",
                )
            )

    fig.update_layout(
        height=480,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="% intención de voto",
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#e2e8f0"),
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────── Informe IA ───────────────────────────
st.subheader("🧠 Informe del Consultor IA")
informe = cargar_informe()

if informe is None:
    st.info("Sin informe todavía. Ejecuta `python analizador_ia.py` o actualiza desde la barra lateral.")
else:
    resumen = informe.get("resumen_ejecutivo", "")
    if resumen:
        st.info(resumen)

    tab1, tab2, tab3 = st.tabs(["⚡ Puntos de inflexión", "🔬 Auditoría de dispersión", "📄 Informe completo"])

    with tab1:
        infs = informe.get("puntos_inflexion") or []
        if not infs:
            st.caption("No se detectaron cambios bruscos de tendencia entre semanas.")
        for it in infs:
            mag = it.get("magnitud_pp")
            titulo = f"{it.get('partido', '—')} · {it.get('semana_o_fecha', '')}"
            if isinstance(mag, (int, float)):
                titulo += f" · {mag:+.1f} pp"
            with st.expander(titulo):
                st.write(it.get("descripcion", ""))

        pc = informe.get("progreso_campana") or {}
        if pc:
            st.markdown(f"**Progreso de campaña:** {pc.get('situacion', '')}")
            bloques = pc.get("tendencia_bloques") or {}
            if bloques:
                bcols = st.columns(min(len(bloques), 3))
                for i, (k, v) in enumerate(bloques.items()):
                    with bcols[i % len(bcols)]:
                        st.markdown(f"**{k.replace('_', ' ')}**")
                        st.caption(v)
            if pc.get("momento_clave"):
                st.caption(f"⏱️ {pc['momento_clave']}")

    with tab2:
        aud = informe.get("auditoria_dispersion") or {}
        mas = aud.get("encuestadora_mas_desviada")
        if mas:
            st.warning(f"Encuestadora con mayor desviación del consenso: **{mas}**")
        he = aud.get("house_effects") or []
        if he:
            st.dataframe(pd.DataFrame(he), use_container_width=True, hide_index=True)
        alertas = aud.get("alertas") or []
        for a in alertas:
            st.error(f"🚨 {a}")
        if aud.get("nota_metodologica"):
            st.caption(aud["nota_metodologica"])

        # House effects precalculados por el scraper
        he_scraper = datos.get("house_effects") or []
        if he_scraper:
            with st.expander("Desviaciones precalculadas (scraper, ventana 45 días)"):
                filas = [
                    {
                        "Encuestadora": h["encuestadora"],
                        "n": h["n_encuestas"],
                        "Partido": h["desviacion_max"]["partido"],
                        "Desv. (pp)": h["desviacion_max"]["pp"],
                    }
                    for h in he_scraper
                ]
                st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    with tab3:
        md = informe.get("markdown")
        if md:
            st.markdown(md)
        else:
            st.json(informe)

# ─────────────────────────── Chat IA ───────────────────────────
st.subheader("💬 Pregúntale al Consultor")

if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

pregunta = st.chat_input("Ej.: ¿Quién lidera en las últimas dos semanas? ¿Qué casa se desvía más?")
if pregunta:
    st.session_state.chat.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Pensando…"):
            try:
                from analizador_ia import cargar_encuestas as _load, preguntar as _preguntar

                respuesta = _preguntar(
                    pregunta,
                    historial=st.session_state.chat[:-1],
                    datos=_load(),
                )
            except Exception as exc:  # noqa: BLE001
                respuesta = f"No se pudo consultar Gemini: {exc}"
        st.markdown(respuesta)
    st.session_state.chat.append({"role": "assistant", "content": respuesta})
