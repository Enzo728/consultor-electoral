"""Consultor Electoral España — UI minimalista responsive (desktop + móvil)."""

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

# Mapa de momentum → etiqueta ultra-corta (máx. 2 palabras)
ESTADO_CORTO = {
    "Subiendo fuerte 🚀": "Sube",
    "Subiendo 📈": "Sube",
    "Estancado ➡️": "Estable",
    "En retroceso 📉": "Baja",
    "Caída libre ⚠️": "Baja",
}

st.set_page_config(
    page_title="Consultor Electoral",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ───────────────── CSS minimalista + responsive ─────────────────
st.markdown(
    """
    <style>
      :root {
        --bg: #0B0F14;
        --panel: #141A22;
        --borde: #243041;
        --texto: #E8EEF7;
        --suave: #8B9BB0;
        --azul: #3B82F6;
        --verde: #22C55E;
        --rojo: #EF4444;
        --oro: #FBBF24;
      }
      html, body, [class*="css"] {
        font-family: "Inter", "Segoe UI", system-ui, sans-serif;
        overflow-wrap: break-word;
      }
      .stApp { background: var(--bg); color: var(--texto); }
      #MainMenu, footer, header[data-testid="stHeader"],
      header[data-testid="stToolbar"] { visibility: hidden; }
      .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2.5rem;
        max-width: 1200px;
      }

      /* Cabecera */
      .top {
        display: flex; flex-wrap: wrap; align-items: baseline;
        justify-content: space-between; gap: 0.4rem;
        margin-bottom: 0.35rem;
      }
      .top h1 {
        margin: 0; font-size: 1.45rem; font-weight: 800;
        letter-spacing: -0.02em; color: #F8FAFC;
      }
      .top .meta { font-size: 0.78rem; color: var(--suave); }

      /* Barra 176 */
      .maj-wrap { margin: 0.4rem 0 0.2rem; }
      .maj-labels {
        display: flex; justify-content: space-between;
        font-size: 0.72rem; color: var(--suave); margin-bottom: 0.25rem;
      }
      .maj-labels .hit { color: var(--oro); font-weight: 700; }

      /* Tarjetas KPI (st.metric) */
      div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--borde);
        border-radius: 12px;
        padding: 12px;
        min-height: auto;
        overflow-wrap: break-word;
        word-break: break-word;
      }
      div[data-testid="stMetricLabel"] {
        color: var(--suave) !important;
        font-size: 0.78rem !important;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-size: 1.55rem !important;
        font-weight: 800 !important;
      }
      div[data-testid="stMetricDelta"] > div {
        font-size: 0.85rem !important;
        white-space: nowrap;
      }

      /* Secciones */
      .sec {
        font-size: 0.95rem; font-weight: 700; color: #F8FAFC;
        border-left: 3px solid var(--azul);
        padding-left: 0.5rem;
        margin: 1.1rem 0 0.45rem;
      }

      /* Pactómetro checkboxes compactos */
      .pact-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
        gap: 0.35rem;
        margin-bottom: 0.5rem;
      }
      .pact-chip {
        display: flex; align-items: center; justify-content: center;
        gap: 0.3rem; padding: 0.4rem 0.35rem;
        background: var(--panel); border: 1px solid var(--borde);
        border-radius: 999px; font-size: 0.8rem; font-weight: 700;
        color: var(--texto); cursor: pointer; user-select: none;
        text-align: center; min-height: auto; overflow-wrap: anywhere;
      }

      /* Info compacta coalición */
      .coal {
        background: var(--panel); border: 1px solid var(--borde);
        border-radius: 12px; padding: 12px; margin-top: 0.4rem;
        overflow-wrap: break-word; min-height: auto;
      }
      .coal .n { font-size: 1.7rem; font-weight: 800; color: #F8FAFC; }
      .coal .n span { font-size: 0.85rem; color: var(--suave); font-weight: 600; }
      .coal .st { font-size: 0.85rem; font-weight: 700; margin-top: 0.15rem; }

      /* Chips de fecha / filtros */
      .stRadio > div { gap: 0.4rem; }
      .stRadio label { font-size: 0.85rem !important; }

      /* Select slider más compacto */
      [data-baseweb="select"] { font-size: 0.9rem; }

      /* Tabs limpios */
      [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 0.88rem; font-weight: 600; padding-left: 0.7rem; padding-right: 0.7rem;
      }

      /* Expander sin párrafos largos en principal */
      .stExpander summary { font-size: 0.9rem !important; }

      /* Tablas */
      [data-testid="stDataFrame"] {
        border-radius: 10px; overflow: hidden;
      }

      /* Móvil */
      @media (max-width: 768px) {
        .block-container { padding-left: 0.65rem; padding-right: 0.65rem; }
        .top h1 { font-size: 1.15rem; }
        div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
        div[data-testid="stMetric"] { padding: 10px; }
        .sec { margin-top: 0.85rem; }
        .coal .n { font-size: 1.4rem; }
      }
      @media (max-width: 480px) {
        div[data-testid="stMetricLabel"] { font-size: 0.7rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.15rem !important; }
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


def estado_corto(mom: dict) -> str:
    bruto = str(mom.get("estado") or "Estancado ➡️")
    if bruto in ESTADO_CORTO:
        return ESTADO_CORTO[bruto]
    d7 = mom.get("delta_7d")
    if d7 is None:
        return "Estable"
    if d7 >= 0.3:
        return "Sube"
    if d7 <= -0.3:
        return "Baja"
    return "Estable"


def flecha(estado: str) -> str:
    if estado == "Sube":
        return "▲"
    if estado == "Baja":
        return "▼"
    return "•"


def ejecutar_actualizacion() -> tuple[bool, str]:
    pasos = []
    for script in ("scraper.py", "analizador_ia.py", "tracker_historico.py"):
        ruta = BASE_DIR / script
        if not ruta.exists():
            if script == "tracker_historico.py":
                continue
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
            if script == "analizador_ia.py":
                pasos.append("AVISO IA timeout")
                continue
            return False, f"Timeout {script}"
        if proc.returncode != 0:
            detalle = (proc.stderr or proc.stdout or "").strip()[-800:]
            if script in ("analizador_ia.py", "tracker_historico.py"):
                pasos.append(f"AVISO {script} fallo")
                continue
            return False, f"Error {script}:\n{detalle}"
        pasos.append(f"OK {script}")
    return True, " | ".join(pasos)


def barra_176(escaños: dict[str, int], bloque_total: int, bloque_nombre: str) -> str:
    """Barra horizontal limpia hacia 176 + relleno por partido."""
    orden = [p for p in pm.ORDEN_HEMICICLO if escaños.get(p)]
    for p in sorted(escaños, key=lambda x: -escaños[x]):
        if p not in orden and escaños[p] > 0:
            orden.append(p)
    partes = []
    for p in orden:
        n = escaños[p]
        pct = 100.0 * n / pm.TOTAL_ESCANOS
        color = color_partido_local(p)
        partes.append(
            f'<div style="width:{pct:.3f}%;background:{color};height:22px;" '
            f'title="{p}: {n}"></div>'
        )
    maj_pct = 100.0 * pm.MAYORIA_ABSOLUTA / pm.TOTAL_ESCANOS
    fill = min(100.0, 100.0 * bloque_total / pm.TOTAL_ESCANOS)
    bar_fill_pct = min(100.0, 100.0 * bloque_total / pm.MAYORIA_ABSOLUTA) if bloque_total else 0
    return f"""
    <div class="maj-wrap">
      <div class="maj-labels">
        <span>0</span>
        <span class="hit">176 mayorías</span>
        <span>350</span>
      </div>
      <div style="position:relative;">
        <div style="display:flex;width:100%;border-radius:6px;overflow:hidden;
                    border:1px solid #243041;">
          {''.join(partes)}
        </div>
        <div style="position:absolute;top:-3px;bottom:-3px;left:{maj_pct:.3f}%;
                    width:0;border-left:2px dashed #FBBF24;pointer-events:none;"></div>
        <div style="margin-top:0.35rem;height:8px;border-radius:99px;
                    background:#0B0F14;border:1px solid #243041;overflow:hidden;">
          <div style="width:{bar_fill_pct:.2f}%;height:100%;
                      background:linear-gradient(90deg,#3B82F6,#22C55E);"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;
                    color:#8B9BB0;margin-top:0.2rem;">
          <span style="color:#E8EEF7;font-weight:700;">{bloque_nombre}</span>
          <span style="color:#FBBF24;font-weight:700;">{bloque_total} / 176</span>
        </div>
      </div>
    </div>
    """


def construir_hemiciclo(escaños: dict[str, int], seleccion: list[str]) -> go.Figure:
    """350 escaños · 180°=izquierda (Podemos…) → 0°=derecha (…VOX/SALF)."""
    orden = pm.escaños_para_hemiciclo(escaños)
    coords = pm.posiciones_hemiciclo(len(orden), n_filas=7)
    fig = go.Figure()

    by_party: dict[str, list[tuple[float, float, str]]] = {}
    for (partido, color), (x, y) in zip(orden, coords):
        by_party.setdefault(partido, []).append((x, y, color))

    # Orden visual L→R: PODEMOS → FA/Sumar → PSOE → regionales → PP → VOX → SALF
    resto_ord = sorted(set(by_party) - set(pm.ORDEN_HEMICICLO))
    for partido in pm.ORDEN_HEMICICLO + resto_ord:
        if partido not in by_party:
            continue
        pts = by_party[partido]
        activo = partido in seleccion or (
            partido == "FA" and ("FA" in seleccion or "SUMAR" in seleccion)
        )
        n = len(pts)
        color = pts[0][2]
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                name=partido,
                marker=dict(
                    color=color,
                    size=8,
                    opacity=1.0 if activo else 0.18,
                    line=dict(color="#0B0F14", width=0.5),
                ),
                hovertemplate=f"<b>{partido}</b><br>{n} escaños<extra></extra>",
                showlegend=True,
            )
        )

    # Centro del arco: 2 líneas limpias
    if seleccion:
        total_sel = sum(escaños.get(p, 0) for p in seleccion)
        nombre_corto = "+".join(seleccion[:3]) + ("…" if len(seleccion) > 3 else "")
    else:
        top = max(escaños, key=escaños.get) if escaños else "—"
        total_sel = escaños.get(top, 0)
        nombre_corto = top

    fig.add_annotation(
        x=0,
        y=0.28,
        text=(
            f"<b>{nombre_corto} · {total_sel}</b><br>"
            f"<span style='font-size:12px;color:#FBBF24'>Mayoría: 176</span>"
        ),
        showarrow=False,
        font=dict(size=15, color="#F8FAFC"),
        align="center",
    )

    fig.update_layout(
        autosize=True,
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            scaleanchor="y", scaleratio=1, visible=False,
            range=[-1.12, 1.12],
        ),
        yaxis=dict(visible=False, range=[-0.1, 1.12]),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.06,
            xanchor="center", x=0.5,
            font=dict(size=11, color="#E8EEF7"),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="#141A22", font_size=12),
        showlegend=True,
    )
    return fig


# ═══════════════════════ DATOS ═══════════════════════
datos = cargar_encuestas()
if datos is None:
    st.warning("Sin datos. Actualiza desde el menú lateral ▸.")
    if st.button("🔄 Actualizar", type="primary"):
        st.cache_data.clear()
        ok, msg = ejecutar_actualizacion()
        st.success(msg if ok else msg)
        st.rerun()
    st.stop()

sim = cargar_simulacion()
hist = cargar_historico_ui()
dias_hist = sorted((hist.get("dias") or {}).keys())

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

# ═══════════════════════ SIDEBAR (colapsada) ═══════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Datos")
    if st.button("🔄 Actualizar", type="primary", use_container_width=True):
        with st.status("Actualizando…", expanded=False) as status:
            ok, msg = ejecutar_actualizacion()
            if ok:
                status.update(label="OK", state="complete")
                st.cache_data.clear()
            else:
                status.update(label="Error", state="error")
                st.error(msg)
        st.rerun()

    f = datos.get("filtros", {}) or {}
    st.caption(f"Fuente: Wikipedia · {datos.get('actualizado', '—')}")
    st.caption(
        f"Incluidas {f.get('total_incluidas', '?')} · "
        f"excluidas {f.get('total_excluidas', '?')}"
    )
    info = cargar_informe()
    if info:
        st.caption(f"IA: {info.get('generado_en', '—')}")
    st.caption("Media ponderada · sin CIS · n≥800 · D'Hondt 350")

# ═══════════════════════ MÁQUINA DEL TIEMPO ═══════════════════════
opciones_fecha = list(dias_hist) + ["Hoy"]
fecha_sel = st.select_slider(
    "📅",
    options=opciones_fecha,
    value=opciones_fecha[-1],
    label_visibility="collapsed",
    help="Máquina del tiempo: histórico diario",
)
es_hoy = fecha_sel == "Hoy"
fecha_label = "Hoy" if es_hoy else fecha_sel

if es_hoy:
    medias_vis = act_live
    escaños_vis = sim["escaños"]
    origen_vis = "live"
else:
    snap_sel = (hist.get("dias") or {}).get(fecha_sel) or {}
    medias_vis = snap_sel.get("medias") or act_live
    escaños_vis = snap_sel.get("escaños") or sim["escaños"]
    origen_vis = snap_sel.get("origen", "backfill")

bloques = pm.simular_bloques(escaños_vis)
mejor = bloques[0] if bloques else None
absolutos = [b for b in bloques if b["alcanza_absoluta"]]
veredicto = absolutos[0] if absolutos else mejor

# ═══════════════════════ ARRIBA: barra + hemiciclo ═══════════════════════
nombre_bloque = (veredicto or {}).get("bloque", "—")
total_bloque = (veredicto or {}).get("total", 0)

st.markdown(
    f"""
    <div class="top">
      <h1>Consultor Electoral España</h1>
      <div class="meta">{fecha_label} · {origen_vis} · Congreso 350</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(barra_176(escaños_vis, total_bloque, nombre_bloque), unsafe_allow_html=True)

# Selector hemiciclo compacto
partidos_escaños = [p for p in pm.ORDEN_HEMICICLO if escaños_vis.get(p)]
for p in sorted(escaños_vis, key=lambda x: -escaños_vis[x]):
    if p not in partidos_escaños and escaños_vis[p] > 0:
        partidos_escaños.append(p)

seleccion = st.multiselect(
    "Resaltar",
    options=partidos_escaños,
    default=[p for p in ["PP", "PSOE", "VOX", "FA"] if p in partidos_escaños],
    label_visibility="collapsed",
    width="stretch",
    help="Partidos resaltados en el hemiciclo",
)

st.plotly_chart(
    construir_hemiciclo(escaños_vis, seleccion),
    width="stretch",
    theme=None,
    config={"displayModeBar": False, "responsive": True},
)

# ═══════════════════════ MEDIO: pactómetro ═══════════════════════
st.markdown('<div class="sec">Pactómetro</div>', unsafe_allow_html=True)

if "pacto_sel" not in st.session_state:
    st.session_state.pacto_sel = [p for p in ["PP", "VOX"] if p in partidos_escaños]

# Checkboxes compactos en 1 fila responsive (máx 3 visibles por línea en móvil vía CSS grid)
ncol = min(3, max(1, len(partidos_escaños)))
pacto_cols = st.columns(ncol, gap="small")
pacto_sel: list[str] = []
for i, p in enumerate(partidos_escaños):
    with pacto_cols[i % ncol]:
        etiqueta = f"{p} ({escaños_vis[p]})"
        if st.checkbox(
            etiqueta,
            key=f"pacto_{p}",
            value=p in st.session_state.pacto_sel,
            label_visibility="visible",
        ):
            pacto_sel.append(p)
st.session_state.pacto_sel = pacto_sel

total_pacto = sum(escaños_vis.get(p, 0) for p in pacto_sel)
info_p = pm.estado_bloque(total_pacto)
color_estado = (
    "#22C55E"
    if info_p["alcanza_absoluta"]
    else "#FBBF24"
    if info_p["total"] >= pm.MIN_SIMPLE_2A_VUELTA
    else "#EF4444"
)
pct_maj = min(100.0, 100.0 * total_pacto / pm.MAYORIA_ABSOLUTA)

st.markdown(
    f"""
    <div class="coal">
      <div style="font-size:0.7rem;color:#8B9BB0;text-transform:uppercase;
                  letter-spacing:0.08em;">Coalición</div>
      <div class="n">{total_pacto}<span> / 176</span></div>
      <div class="st" style="color:{color_estado};">
        {info_p['estado']} · {info_p['texto_distancia']}
      </div>
      <div style="background:#0B0F14;border-radius:99px;height:10px;
                  margin-top:0.55rem;position:relative;overflow:hidden;
                  border:1px solid #243041;">
        <div style="width:{pct_maj:.2f}%;height:100%;
                    background:{color_estado};"></div>
        <div style="position:absolute;top:0;bottom:0;left:100%;
                    border-left:2px dashed #FBBF24;"></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Tabla compacta de bloques
filas_bloques = [
    {
        "Bloque": b["bloque"],
        "Escaños": b["total"],
        "vs 176": b["texto_distancia"],
        "Estado": "✅" if b["alcanza_absoluta"] else "—" ,
    }
    for b in bloques
]
st.dataframe(
    pd.DataFrame(filas_bloques),
    width="stretch",
    hide_index=True,
    height=min(320, 36 * len(filas_bloques) + 40),
)

# ═══════════════════════ Tarjetas partidos (máx 3 col) ═══════════════════════
st.markdown(f'<div class="sec">Partidos · {fecha_label}</div>', unsafe_allow_html=True)

kpi_partidos = [p for p in PARTIDOS_KPI if p in medias_vis] or sorted(
    medias_vis, key=lambda p: medias_vis.get(p) or 0, reverse=True
)[:6]
kpi_partidos = kpi_partidos[:6]  # 2 filas × 3

esc_semana = th.variacion_escaños(hist, dias=7) if dias_hist else {}

# chunk en grupos de 3 → nunca más de 3 columnas por fila
for start in range(0, len(kpi_partidos), 3):
    chunk = kpi_partidos[start : start + 3]
    cols = st.columns(len(chunk), gap="medium")
    for i, p in enumerate(chunk):
        valor = medias_vis.get(p) or 0.0
        esc = escaños_vis.get(p, 0)
        mom = momentum.get(p) or {}
        d7 = mom.get("delta_7d")
        estado = estado_corto(mom)
        d_esc = esc_semana.get(p, 0)
        delta_label = f"{flecha(estado)} {estado}"
        delta_color = (
            "normal" if (d7 or 0) > 0.05
            else "inverse" if (d7 or 0) < -0.05
            else "off"
        )
        esc_delta = f"{d_esc:+d} esc." if d_esc else "—"
        with cols[i]:
            st.metric(
                label=p,
                value=f"{valor:.1f}% · {esc}",
                delta=f"{delta_label} · {esc_delta}",
                delta_color=delta_color,
                border=True,
                label_visibility="visible",
            )

# ═══════════════════════ ABAJO: ganadores/perdedores ═══════════════════════
st.markdown('<div class="sec">Subidas y bajadas</div>', unsafe_allow_html=True)

c_per, c_gap, c_ai = st.columns([1, 1, 2], gap="small")
with c_per:
    periodo = st.radio(
        "Periodo",
        options=[7, 30],
        format_func=lambda d: f"{d}d",
        horizontal=True,
        index=0,
        label_visibility="collapsed",
    )

filas_gan = th.ganadores_perdedores(hist, periodo=periodo) if dias_hist else []
if filas_gan:
    df_gan = pd.DataFrame(filas_gan).sort_values("delta_pp")
    fig_gan = go.Figure()
    colores = [
        "#EF4444" if v < 0 else "#22C55E" if v > 0 else "#64748B"
        for v in df_gan["delta_pp"]
    ]
    textos = [
        f"{'▲' if v > 0 else '▼' if v < 0 else '•'} {v:+.1f}"
        for v in df_gan["delta_pp"]
    ]
    fig_gan.add_trace(
        go.Bar(
            y=df_gan["partido"],
            x=df_gan["delta_pp"],
            orientation="h",
            marker_color=colores,
            text=textos,
            textposition="outside",
            customdata=df_gan[["delta_escaños"]].values,
            hovertemplate="%{y}<br>Δ %{x:.2f} pp<br>Δ esc %{customdata[0]}<extra></extra>",
        )
    )
    fig_gan.update_layout(
        autosize=True,
        height=max(260, 34 * len(df_gan)),
        margin=dict(l=10, r=50, t=20, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            gridcolor="#1E293B",
            zeroline=True,
            zerolinecolor="#334155",
            title=dict(text=f"Δ pp · {periodo}d", font=dict(color="#8B9BB0", size=11)),
        ),
        yaxis=dict(tickfont=dict(color="#E8EEF7", size=12)),
        font=dict(color="#E8EEF7"),
        showlegend=False,
    )
    st.plotly_chart(
        fig_gan,
        width="stretch",
        theme=None,
        config={"displayModeBar": False, "responsive": True},
    )
else:
    st.info("Sin histórico suficiente.")

# Expander IA — no ocupa la pantalla principal
with st.expander("💬 Ver resumen breve de la IA"):
    informe = cargar_informe()
    if informe is None:
        st.caption("Sin informe. Actualiza datos o ejecuta analizador_ia.py.")
    else:
        resumen = informe.get("resumen_ejecutivo") or ""
        if resumen:
            st.write(resumen)
        for it in (informe.get("puntos_inflexion") or [])[:4]:
            mag = it.get("magnitud_pp")
            titulo = f"{it.get('partido', '—')} · {it.get('semana_o_fecha', '')}"
            if isinstance(mag, (int, float)):
                titulo += f" · {mag:+.1f} pp"
            with st.expander(titulo):
                st.write(it.get("descripcion", ""))
        with st.expander("Informe completo"):
            md = informe.get("markdown")
            st.markdown(md if md else json.dumps(informe, ensure_ascii=False, indent=2))

# ═══════════════════════ TABS profundo ═══════════════════════
tab_tend, tab_aud, tab_ia = st.tabs(
    ["📈 Tendencia", "🔬 Auditoría", "💬 Chat"]
)

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
        width="stretch",
    )
    if df.empty or not seleccion_t:
        st.info("Sin series.")
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
                    marker=dict(color=color, size=5, opacity=0.3),
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
                        line=dict(color=color, width=2.5),
                        legendgroup=p,
                        hovertemplate=f"{p}: %{{y:.1f}}%<extra></extra>",
                    )
                )
        fig.update_layout(
            autosize=True,
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="% intención",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#1E293B"),
            font=dict(color="#E8EEF7"),
        )
        st.plotly_chart(
            fig,
            width="stretch",
            theme=None,
            config={"displayModeBar": False, "responsive": True},
        )

with tab_aud:
    he = datos.get("house_effects") or []
    if he:
        filas = [
            {
                "Encuestadora": h["encuestadora"],
                "n": h["n_encuestas"],
                "Partido": h["desviacion_max"]["partido"],
                "Desv.": h["desviacion_max"]["pp"],
            }
            for h in he
        ]
        st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)
    else:
        st.info("Sin house effects.")

    f = datos.get("filtros", {}) or {}
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Incluidas", f.get("total_incluidas", "—"), border=True)
    m2.metric("CIS", f.get("excluidas_cis", "—"), border=True)
    m3.metric("n<800", f.get("excluidas_muestra", "—"), border=True)
    m4.metric(
        "Otras",
        (f.get("excluidas_fecha", 0) or 0) + (f.get("excluidas_otra", 0) or 0),
        border=True,
    )

    excl = datos.get("excluidas") or []
    if excl:
        with st.expander(f"Excluidas ({len(excl)})"):
            st.dataframe(pd.DataFrame(excl), width="stretch", hide_index=True)

with tab_ia:
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    pregunta = st.chat_input("Pregunta breve…")
    if pregunta:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("…"):
                try:
                    from analizador_ia import cargar_encuestas as _load
                    from analizador_ia import preguntar as _preguntar

                    respuesta = _preguntar(
                        pregunta,
                        historial=st.session_state.chat[:-1],
                        datos=_load(),
                    )
                except Exception as exc:  # noqa: BLE001
                    respuesta = f"Error IA: {exc}"
            st.markdown(respuesta)
        st.session_state.chat.append({"role": "assistant", "content": respuesta})
