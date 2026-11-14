"""Consultor Electoral España — interfaz editorial estilo FiveThirtyEight / FT."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import pactometro as pm
import tracker_historico as th

BASE_DIR = Path(__file__).resolve().parent
ENCUESTAS_PATH = BASE_DIR / "data" / "encuestas_limpias.json"
INFORME_PATH = BASE_DIR / "data" / "informe_ia.json"
HIST_PATH = BASE_DIR / "data" / "historico_diario.json"

PARTIDOS_KPI = ["PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF"]

st.set_page_config(
    page_title="Consultor Electoral España",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────── CSS editorial ─────────────────
st.markdown(
    """
    <style>
      :root {
        --cobalto: #1E40AF;
        --fondo: #0E1117;
        --panel: #161B22;
        --borde: #30363D;
        --texto: #E6EDF3;
        --suave: #8B949E;
      }
      html, body, [class*="css"] { font-family: "Inter", "Segoe UI", system-ui, sans-serif; }
      .stApp {
        background: linear-gradient(180deg, #0E1117 0%, #0E1117 100%);
        color: var(--texto);
      }
      #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
      .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }

      .hero {
        background: linear-gradient(135deg, #0B1220 0%, #111827 55%, #1E3A5F 100%);
        border: 1px solid var(--borde);
        border-radius: 16px;
        padding: 1.4rem 1.6rem 1.1rem;
        margin-bottom: 1rem;
      }
      .hero h1 { margin: 0; font-size: 1.75rem; letter-spacing: -0.02em; color: #F8FAFC; }
      .hero .kicker {
        display: inline-block; font-size: 0.72rem; font-weight: 700;
        letter-spacing: 0.14em; text-transform: uppercase;
        color: #93C5FD; background: rgba(30,64,175,0.35);
        border: 1px solid #1E40AF; border-radius: 999px;
        padding: 0.2rem 0.7rem; margin-bottom: 0.55rem;
      }
      .hero .sub { color: var(--suave); font-size: 0.92rem; margin-top: 0.35rem; }

      .verdict {
        display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1rem;
      }
      .verdict-card {
        flex: 1 1 200px; background: rgba(14,17,23,0.75);
        border: 1px solid var(--borde); border-radius: 12px;
        padding: 0.75rem 0.9rem; min-width: 180px;
      }
      .verdict-card .label {
        font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
        color: var(--suave); margin-bottom: 0.25rem;
      }
      .verdict-card .value { font-size: 1.15rem; font-weight: 700; color: #F8FAFC; }
      .verdict-card .meta { font-size: 0.8rem; color: #93C5FD; margin-top: 0.15rem; }
      .verdict-card.ok { border-color: #16A34A; }
      .verdict-card.warn { border-color: #D97706; }
      .verdict-card.bad { border-color: #6B7280; }

      .bar-wrap { margin-top: 0.9rem; }
      .bar-labels {
        display: flex; justify-content: space-between;
        font-size: 0.75rem; color: var(--suave); margin-bottom: 0.3rem;
      }
      .bar-labels .maj { color: #FBBF24; font-weight: 700; }

      div[data-testid="stMetric"] {
        background: var(--panel); border: 1px solid var(--borde);
        border-radius: 12px; padding: 12px 14px;
      }
      div[data-testid="stMetricValue"] { color: #F8FAFC; font-size: 1.55rem !important; }
      div[data-testid="stMetricLabel"] { color: var(--suave); }
      div[data-testid="stMetricDelta"] > div { font-size: 0.9rem !important; }

      .section-title {
        font-size: 1.05rem; font-weight: 700; color: #F8FAFC;
        border-left: 4px solid var(--cobalto); padding-left: 0.6rem;
        margin: 1.4rem 0 0.6rem;
      }
      .pact-row label { font-size: 0.88rem !important; }
      .seat-pill {
        display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
        font-size: 0.78rem; font-weight: 700; margin-right: 0.35rem;
      }

      @media (max-width: 768px) {
        .block-container { padding-left: 0.75rem; padding-right: 0.75rem; }
        .hero h1 { font-size: 1.3rem; }
        div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
        .verdict-card { flex: 1 1 100%; }
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


@st.cache_data(show_spinner=False, ttl=120)
def cargar_simulacion() -> dict:
    return pm.simular_desde_medias()


@st.cache_data(show_spinner=False, ttl=60)
def cargar_historico_ui() -> dict:
    if not HIST_PATH.exists():
        return {"actualizado": None, "dias": {}}
    try:
        return json.loads(HIST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"actualizado": None, "dias": {}}


def dataframe_evolucion(datos: dict) -> pd.DataFrame:
    ev = datos.get("evolucion", [])
    if not ev:
        return pd.DataFrame()
    df = pd.DataFrame(ev)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha")


def suavizar(df: pd.DataFrame, partidos: list[str], span: int = 12) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
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


def color_partido_local(p: str) -> str:
    if p in ("SUMAR", "FA"):
        return pm.COLORES_HEMICICLO["FA"]
    return pm.COLORES_HEMICICLO.get(p, pm.COLORES_HEMICICLO["OTROS"])


def ejecutar_actualizacion() -> tuple[bool, str]:
    pasos = []
    for script in ("scraper.py", "analizador_ia.py", "tracker_historico.py"):
        ruta = BASE_DIR / script
        if not ruta.exists():
            if script == "tracker_historico.py":
                continue
            return False, f"No se encuentra {script}"
        # analizador_ia requiere red/API; si falla, seguimos con tracker
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
            if script == "analizador_ia.py":
                pasos.append("AVISO analizador_ia timeout")
                continue
            return False, f"Timeout ejecutando {script}"
        if proc.returncode != 0:
            detalle = (proc.stderr or proc.stdout or "").strip()[-800:]
            if script == "analizador_ia.py":
                pasos.append("AVISO analizador_ia fallo (API)")
                continue
            if script == "tracker_historico.py":
                pasos.append("AVISO tracker fallo")
                continue
            return False, f"Error en {script}:\n{detalle}"
        pasos.append(f"OK {script}")
    return True, " | ".join(pasos)


def construir_barra_escaños(escaños: dict[str, int]) -> str:
    """Barra HTML horizontal de 350 escaños con marca en 176."""
    orden = [p for p in pm.ORDEN_HEMICICLO if escaños.get(p)]
    # Incluir no listados al final
    for p in sorted(escaños, key=lambda x: -escaños[x]):
        if p not in orden and escaños[p] > 0:
            orden.append(p)
    partes = []
    for p in orden:
        n = escaños[p]
        color = color_partido_local(p)
        pct = 100.0 * n / pm.TOTAL_ESCANOS
        partes.append(
            f'<div style="width:{pct:.3f}%;background:{color};height:34px;" '
            f'title="{p}: {n} escaños"></div>'
        )
    maj_pct = 100.0 * pm.MAYORIA_ABSOLUTA / pm.TOTAL_ESCANOS
    barra = (
        '<div class="bar-wrap">'
        '<div class="bar-labels"><span>0</span>'
        f'<span class="maj">176 · Mayoría absoluta</span>'
        f"<span>{pm.TOTAL_ESCANOS}</span></div>"
        '<div style="position:relative;">'
        '<div style="display:flex;width:100%;border-radius:8px;overflow:hidden;'
        'border:1px solid #30363D;">'
        + "".join(partes)
        + "</div>"
        f'<div style="position:absolute;top:-4px;bottom:-4px;left:{maj_pct:.3f}%;'
        'width:0;border-left:2px dashed #FBBF24;pointer-events:none;"></div>'
        "</div></div>"
    )
    return barra


def construir_hemiciclo(escaños: dict[str, int], seleccion: list[str]) -> go.Figure:
    """350 puntos en arco semicircular ordenados por espectro."""
    orden = pm.escaños_para_hemiciclo(escaños)
    coords = pm.posiciones_hemiciclo(len(orden), n_filas=7)
    fig = go.Figure()
    # Trazar por partido para leyenda/hover agrupado
    by_party: dict[str, list[tuple[float, float, str]]] = {}
    for (partido, color), (x, y) in zip(orden, coords):
        by_party.setdefault(partido, []).append((x, y, color))

    for partido in pm.ORDEN_HEMICICLO + sorted(
        set(by_party) - set(pm.ORDEN_HEMICICLO)
    ):
        if partido not in by_party:
            continue
        pts = by_party[partido]
        activo = partido in seleccion or (
            partido == "FA" and ("FA" in seleccion or "SUMAR" in seleccion)
        )
        n = len(pts)
        color = pts[0][2]
        opacidad = 1.0 if activo else 0.22
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                name=partido,
                marker=dict(
                    color=color,
                    size=9,
                    opacity=opacidad,
                    line=dict(color="#0E1117", width=0.6),
                ),
                customdata=[[partido, n] for _ in pts],
                hovertemplate=f"<b>{partido}</b><br>{n} escaños<extra></extra>",
                showlegend=True,
            )
        )

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            scaleanchor="y", scaleratio=1, visible=False,
            range=[-1.15, 1.15],
        ),
        yaxis=dict(visible=False, range=[-0.12, 1.15]),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5,
            font=dict(size=11, color="#E6EDF3"),
        ),
        hoverlabel=dict(bgcolor="#111827", font_size=12),
        showlegend=True,
    )
    return fig


# ───────────────── Sidebar ─────────────────
with st.sidebar:
    st.markdown("### 🏛️ Consultor Electoral")
    st.caption("Análisis de encuestas · Congreso de los Diputados")

    if st.button("🔄 Actualizar datos ahora", type="primary", use_container_width=True):
        with st.status("Actualizando datos…", expanded=True) as status:
            st.write("1/3 Extrayendo e filtrando encuestas + informe IA…")
            ok, msg = ejecutar_actualizacion()
            if ok:
                st.write("3/3 Registrando histórico y momentum…")
                status.update(label="Datos actualizados", state="complete")
                st.success(msg)
                cargar_encuestas.clear()
                cargar_informe.clear()
                cargar_simulacion.clear()
                cargar_historico_ui.clear()
            else:
                status.update(label="Error", state="error")
                st.error(msg)

    st.divider()
    datos_side = cargar_encuestas()
    if datos_side:
        st.caption(f"Datos: {datos_side.get('actualizado', '—')}")
        f = datos_side.get("filtros", {})
        st.caption(
            f"Incluidas {f.get('total_incluidas', '?')} · "
            f"Excluidas {f.get('total_excluidas', '?')} (CIS / n<800)"
        )
    informe_side = cargar_informe()
    if informe_side:
        st.caption(f"Informe IA: {informe_side.get('generado_en', '—')}")

    st.divider()
    st.caption(
        "Metodología: media ponderada exp(−λt)·√n, "
        "sin CIS, muestra ≥ 800 · escenario D'Hondt con pool regionalista."
    )


# ───────────────── Datos ─────────────────
datos = cargar_encuestas()
if datos is None:
    st.warning(
        "No hay datos. Pulsa **«Actualizar datos ahora»** en la barra lateral."
    )
    st.stop()

sim = cargar_simulacion()
hist = cargar_historico_ui()
dias_hist = sorted((hist.get("dias") or {}).keys())

# Asegurar histórico mínimo (backfill en frío la primera vez)
if len(dias_hist) < 7:
    try:
        th.registrar_hoy()
        cargar_historico_ui.clear()
        hist = cargar_historico_ui()
        dias_hist = sorted((hist.get("dias") or {}).keys())
    except Exception:  # noqa: BLE001
        pass

act_live = datos.get("medias_actual_14d") or datos.get("medias") or {}
ant = datos.get("medias_sem_anterior_14_28d") or {}
momentum = {}
if dias_hist:
    momentum = (hist["dias"].get(dias_hist[-1]) or {}).get("momentum") or {}

# ───────────────── Máquina del tiempo ─────────────────
st.markdown(
    '<div class="section-title">Máquina del tiempo · histórico diario</div>',
    unsafe_allow_html=True,
)
opciones_fecha = list(dias_hist) + ["Hoy"]
default_idx = len(opciones_fecha) - 1
fecha_sel = st.select_slider(
    "Fecha del escenario",
    options=opciones_fecha,
    value=opciones_fecha[default_idx],
    label_visibility="collapsed",
)
es_hoy = fecha_sel == "Hoy"

# Snapshots para la fecha seleccionada
if es_hoy:
    medias_vis = act_live
    escaños_vis = sim["escaños"]
    origen_vis = "live"
else:
    snap_sel = (hist.get("dias") or {}).get(fecha_sel) or {}
    medias_vis = snap_sel.get("medias") or act_live
    escaños_vis = snap_sel.get("escaños") or sim["escaños"]
    origen_vis = snap_sel.get("origen", "backfill")

# Bloques recalculados sobre los escaños visibles
bloques = pm.simular_bloques(escaños_vis)
mejor = bloques[0] if bloques else None
absolutos = [b for b in bloques if b["alcanza_absoluta"]]
cercanos = [
    b for b in bloques
    if not b["alcanza_absoluta"] and b["total"] >= pm.MIN_SIMPLE_2A_VUELTA
]

if absolutos:
    veredicto = absolutos[0]
    v_class, v_meta = "ok", f"{veredicto['texto_distancia']}"
elif cercanos:
    veredicto = cercanos[0]
    v_class, v_meta = "warn", f"2ª vuelta · {veredicto['texto_distancia']}"
else:
    veredicto = mejor
    v_class, v_meta = "bad", "Sin bloque mayoritario claro"

# Escaños de la semana anterior para las tarjetas
esc_semana = th.variacion_escaños(hist, dias=7) if dias_hist else {}
fecha_label = "Hoy" if es_hoy else fecha_sel

# ───────────────── HERO: Pactómetro visual ─────────────────
st.markdown(
    f"""
    <div class="hero">
      <div class="kicker">Pactómetro · 350 escaños · {fecha_label}</div>
      <h1>Consultor Electoral España</h1>
      <div class="sub">
        Escenario <strong>{fecha_label}</strong> ({origen_vis}) · Congreso de los Diputados ·
        datos actualizados {datetime.now().strftime('%d/%m/%Y %H:%M')} ·
        fuente Wikipedia (sin CIS)
      </div>
      <div class="verdict">
        <div class="verdict-card {v_class}">
          <div class="label">Quién puede gobernar</div>
          <div class="value">{veredicto['bloque'] if veredicto else '—'}</div>
          <div class="meta">{veredicto['total'] if veredicto else 0} escaños · {v_meta}</div>
        </div>
        <div class="verdict-card">
          <div class="label">Mayoría absoluta</div>
          <div class="value">176 escaños</div>
          <div class="meta">barrera de investidura directa</div>
        </div>
        <div class="verdict-card">
          <div class="label">Bloques que alcanzan 176</div>
          <div class="value">{len(absolutos)} de {len(bloques)}</div>
          <div class="meta">
            {" · ".join(b['bloque'].split('(')[0].strip()[:20] + ' ' + str(b['total']) for b in bloques[:3])}
          </div>
        </div>
      </div>
      {construir_barra_escaños(escaños_vis)}
    </div>
    """,
    unsafe_allow_html=True,
)

# ───────────────── Tarjetas de tendencia (estilo mercado) ─────────────────
st.markdown(
    '<div class="section-title">Impulso electoral · tarjetas de tendencia</div>',
    unsafe_allow_html=True,
)

def _fmt_delta(v) -> str:
    if v is None:
        return "—"
    return f"{v:+.1f}"


kpi_partidos = [p for p in PARTIDOS_KPI if p in medias_vis] or sorted(
    medias_vis, key=medias_vis.get, reverse=True
)[:7]

n_cards = min(len(kpi_partidos), 7)
card_cols = st.columns(n_cards)
for i, p in enumerate(kpi_partidos[:n_cards]):
    valor = medias_vis.get(p)
    esc = escaños_vis.get(p, 0)
    d_esc = esc_semana.get(p, 0) if not es_hoy else esc_semana.get(p, 0)
    mom = momentum.get(p) or {}
    d7 = mom.get("delta_7d")
    estado = mom.get("estado", "Estancado ➡️")
    # color por impulso
    if d7 is None:
        color_mom = "#8B949E"
    elif d7 >= 0.3:
        color_mom = "#16A34A"
    elif d7 <= -0.3:
        color_mom = "#F87171"
    else:
        color_mom = "#FBBF24"
    esc_color = "#16A34A" if d_esc > 0 else "#F87171" if d_esc < 0 else "#8B949E"
    pp_color = "#16A34A" if (d7 or 0) > 0 else "#F87171" if (d7 or 0) < 0 else "#E6EDF3"

    with card_cols[i]:
        st.markdown(
            f"""
            <div style="background:#161B22;border:1px solid #30363D;border-radius:12px;
                        padding:0.75rem 0.85rem;height:100%;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:800;color:#F8FAFC;font-size:1rem;">{p}</span>
                <span style="font-size:0.72rem;color:{color_mom};font-weight:600;">{estado}</span>
              </div>
              <div style="font-size:1.65rem;font-weight:800;color:#F8FAFC;margin-top:0.25rem;">
                {valor if valor is not None else 0:.1f}%
              </div>
              <div style="font-size:0.82rem;color:#8B949E;">
                <strong style="color:#E6EDF3;">{esc}</strong> escaños
                <span style="color:{esc_color};font-weight:700;"> ({d_esc:+d} sem.)</span>
              </div>
              <div style="font-size:0.78rem;color:{pp_color};margin-top:0.15rem;">
                7d: {_fmt_delta(d7)} pp
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "Momentum = media 7 días vs 14 días previas · escaños vs snapshot hace 7 días · "
    f"escenario: {fecha_label}."
)

# ───────────────── Ganadores y perdedores ─────────────────
st.markdown(
    '<div class="section-title">Ganadores y perdedores</div>',
    unsafe_allow_html=True,
)
periodo = st.radio(
    "Periodo",
    options=[7, 30],
    format_func=lambda d: f"Últimos {d} días",
    horizontal=True,
    label_visibility="collapsed",
)
filas_gan = th.ganadores_perdedores(hist, periodo=periodo) if dias_hist else []
if filas_gan:
    df_gan = pd.DataFrame(filas_gan)
    df_gan = df_gan.sort_values("delta_pp")
    fig_gan = go.Figure()
    colores = ["#DC2626" if v < 0 else "#16A34A" if v > 0 else "#64748B"
               for v in df_gan["delta_pp"]]
    fig_gan.add_trace(
        go.Bar(
            y=df_gan["partido"],
            x=df_gan["delta_pp"],
            orientation="h",
            marker_color=colores,
            text=[f"{v:+.1f} pp" for v in df_gan["delta_pp"]],
            textposition="outside",
            hovertemplate=(
                "%{y}<br>Δ %{x:.2f} pp<br>Δ escaños: "
                + df_gan["delta_escaños"].astype(str).tolist().__repr__()
                + "<extra></extra>"
            ),
        )
    )
    # Corregir hover con customdata en vez de la lista hardcodeada
    fig_gan.data[0].customdata = df_gan[["delta_escaños"]].values
    fig_gan.data[0].hovertemplate = (
        "%{y}<br>Δ %{x:.2f} pp<br>Δ escaños: %{customdata[0]}<extra></extra>"
    )
    fig_gan.update_layout(
        height=max(280, 36 * len(df_gan)),
        margin=dict(l=10, r=40, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#21262D", zeroline=True, zerolinecolor="#30363D",
                   title=f"Δ pp · {periodo} días"),
        yaxis=dict(tickfont=dict(color="#E6EDF3", size=13)),
        font=dict(color="#E6EDF3"),
        showlegend=False,
    )
    st.plotly_chart(fig_gan, use_container_width=True, theme=None)
else:
    st.info("Sin histórico suficiente para comparar periodos.")

# ───────────────── KPIs intención de voto (complemento) ─────────────────
st.markdown(
    f'<div class="section-title">Intención de voto · media 14 días · {fecha_label}</div>',
    unsafe_allow_html=True,
)
cols = st.columns(min(len(kpi_partidos), 7))
for i, p in enumerate(kpi_partidos[:7]):
    with cols[i]:
        delta = round(medias_vis[p] - ant[p], 2) if p in ant and p in medias_vis else None
        st.metric(
            label=p,
            value=f"{medias_vis.get(p, 0):.1f}%",
            delta=f"{delta:+.1f} pp sem." if delta is not None else None,
            delta_color="normal",
        )

# ───────────────── Hemiciclo + Pactómetro interactivo ─────────────────
st.markdown(
    f'<div class="section-title">Hemiciclo del Congreso · {fecha_label}</div>',
    unsafe_allow_html=True,
)

partidos_escaños = [p for p in pm.ORDEN_HEMICICLO if escaños_vis.get(p)]
for p in sorted(escaños_vis, key=lambda x: -escaños_vis[x]):
    if p not in partidos_escaños and escaños_vis[p] > 0:
        partidos_escaños.append(p)

default_sel = [p for p in ["PP", "PSOE", "VOX", "FA"] if p in partidos_escaños]
seleccion = st.multiselect(
    "Resaltar partidos en el hemiciclo",
    options=partidos_escaños,
    default=default_sel,
    label_visibility="collapsed",
)

hemi_col, pacto_col = st.columns([1.35, 1], gap="medium")
with hemi_col:
    fig_h = construir_hemiciclo(escaños_vis, seleccion)
    st.plotly_chart(fig_h, use_container_width=True, theme=None)

with pacto_col:
    st.markdown("**Pactómetro manual** — suma coaliciones en tiempo real")
    if "pacto_sel" not in st.session_state:
        st.session_state.pacto_sel = ["PP", "VOX"]

    ncol = 3
    checkbox_cols = st.columns(ncol)
    pacto_sel = []
    for i, p in enumerate(partidos_escaños):
        with checkbox_cols[i % ncol]:
            etiqueta = f"{p} · {escaños_vis[p]}"
            if st.checkbox(etiqueta, key=f"pacto_{p}", value=p in st.session_state.pacto_sel):
                pacto_sel.append(p)
    st.session_state.pacto_sel = pacto_sel

    total_pacto = sum(escaños_vis.get(p, 0) for p in pacto_sel)
    info_p = pm.estado_bloque(total_pacto)
    pct = 100.0 * total_pacto / pm.TOTAL_ESCANOS
    maj_pct = 100.0 * pm.MAYORIA_ABSOLUTA / pm.TOTAL_ESCANOS

    st.markdown(
        f"""
        <div style="background:#161B22;border:1px solid #30363D;border-radius:12px;
                    padding:0.9rem 1rem;margin-top:0.4rem;">
          <div style="font-size:0.75rem;color:#8B949E;text-transform:uppercase;
                      letter-spacing:0.08em;">Coalición seleccionada</div>
          <div style="font-size:1.9rem;font-weight:800;color:#F8FAFC;">
            {total_pacto}<span style="font-size:0.95rem;color:#8B949E;"> / 176</span>
          </div>
          <div style="font-size:0.9rem;font-weight:600;color:
            {'#16A34A' if info_p['alcanza_absoluta'] else '#FBBF24' if info_p['total']>=pm.MIN_SIMPLE_2A_VUELTA else '#F87171'};">
            {info_p['estado']} · {info_p['texto_distancia']}
          </div>
          <div style="background:#0E1117;border-radius:6px;height:14px;
                      margin-top:0.6rem;position:relative;overflow:hidden;">
            <div style="width:{pct:.2f}%;height:100%;
                        background:{'#16A34A' if info_p['alcanza_absoluta'] else '#1E40AF'};">
            </div>
            <div style="position:absolute;top:0;bottom:0;left:{maj_pct:.2f}%;
                        border-left:2px dashed #FBBF24;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:0.7rem;
                      color:#8B949E;margin-top:0.3rem;">
            <span>0</span><span>176</span><span>350</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filas_bloques = [
        {
            "Bloque": b["bloque"],
            "Escaños": b["total"],
            "vs 176": b["texto_distancia"],
            "Estado": b["estado"],
        }
        for b in bloques
    ]
    st.dataframe(
        pd.DataFrame(filas_bloques),
        width="stretch",
        hide_index=True,
        height=280,
    )

# ───────────────── Tabs ─────────────────
st.markdown('<div class="section-title">Análisis</div>', unsafe_allow_html=True)
tab_tend, tab_aud, tab_ia = st.tabs(
    ["📈 Tendencia Temporal", "🔬 Auditoría Anti-Sesgo (Encuestadoras)", "💬 Consultor IA (Chat)"]
)

# ── Tab: Tendencia ──
with tab_tend:
    df = dataframe_evolucion(datos)
    partidos_disp = (
        sorted(
            df["partido"].unique().tolist(),
            key=lambda p: (
                p not in PARTIDOS_KPI,
                PARTIDOS_KPI.index(p) if p in PARTIDOS_KPI else 99,
                p,
            ),
        )
        if not df.empty
        else []
    )
    seleccion_t = st.multiselect(
        "Partidos",
        options=partidos_disp,
        default=[p for p in PARTIDOS_KPI if p in partidos_disp] or partidos_disp[:5],
    )
    if df.empty or not seleccion_t:
        st.info("Sin series temporales.")
    else:
        df_sel = df[df["partido"].isin(seleccion_t)]
        tend = suavizar(df_sel, seleccion_t)
        fig = go.Figure()
        for p in seleccion_t:
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
                    hovertemplate=f"{p}: %{{y:.1f}}%<extra></extra>",
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
            height=460,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="% intención de voto",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#21262D"),
            font=dict(color="#E6EDF3"),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)

# ── Tab: Auditoría ──
with tab_aud:
    he = datos.get("house_effects") or []
    if he:
        filas = [
            {
                "Encuestadora": h["encuestadora"],
                "n": h["n_encuestas"],
                "Partido": h["desviacion_max"]["partido"],
                "Desv. (pp)": h["desviacion_max"]["pp"],
            }
            for h in he
        ]
        st.caption("Desviación máxima frente al consenso (ventana 45 días, sin CIS).")
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    else:
        st.info("Sin house effects calculados todavía.")

    f = datos.get("filtros", {})
    st.markdown("**Filtros de calidad aplicados**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Incluidas", f.get("total_incluidas", "—"))
    c2.metric("CIS excluidas", f.get("excluidas_cis", "—"))
    c3.metric("n < 800", f.get("excluidas_muestra", "—"))
    c4.metric("Sin fecha / otra", (f.get("excluidas_fecha", 0) or 0) + (f.get("excluidas_otra", 0) or 0))

    excl = datos.get("excluidas") or []
    if excl:
        with st.expander(f"Detalle de {len(excl)} encuestas excluidas"):
            st.dataframe(pd.DataFrame(excl), use_container_width=True, hide_index=True, height=300)

# ── Tab: Consultor IA ──
with tab_ia:
    informe = cargar_informe()
    if informe is None:
        st.info("Sin informe. Ejecuta `python analizador_ia.py` o actualiza desde la barra lateral.")
    else:
        resumen = informe.get("resumen_ejecutivo", "")
        if resumen:
            st.info(resumen)

        sub1, sub2 = st.columns(2)
        with sub1:
            st.markdown("**Puntos de inflexión**")
            for it in (informe.get("puntos_inflexion") or [])[:6]:
                mag = it.get("magnitud_pp")
                titulo = f"{it.get('partido', '—')} · {it.get('semana_o_fecha', '')}"
                if isinstance(mag, (int, float)):
                    titulo += f" · {mag:+.1f} pp"
                with st.expander(titulo):
                    st.write(it.get("descripcion", ""))
        with sub2:
            aud = informe.get("auditoria_dispersion") or {}
            if aud.get("encuestadora_mas_desviada"):
                st.warning(
                    f"Mayor desviación del consenso: **{aud['encuestadora_mas_desviada']}**"
                )
            for a in (aud.get("alertas") or [])[:5]:
                st.error(f"🚨 {a}")
            if aud.get("nota_metodologica"):
                st.caption(aud["nota_metodologica"])

        with st.expander("📄 Informe completo (Markdown)"):
            md = informe.get("markdown")
            st.markdown(md if md else json.dumps(informe, ensure_ascii=False, indent=2))

        st.markdown("---")
        st.markdown("**Chat con el Consultor**")
        if "chat" not in st.session_state:
            st.session_state.chat = []
        for msg in st.session_state.chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        pregunta = st.chat_input("Pregunta sobre encuestas, pactos o tendencias…")
        if pregunta:
            st.session_state.chat.append({"role": "user", "content": pregunta})
            with st.chat_message("user"):
                st.markdown(pregunta)
            with st.chat_message("assistant"):
                with st.spinner("Analizando…"):
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
