"""Seguimiento histórico diario + detección de impulso electoral (momentum).

Archivo local: data/historico_diario.json
- Instantánea diaria (medias ponderadas, escaños, bloque mayoritario)
- Backfill automático de ~30 días si hay menos de 7 registros
- Deltas 1d/7d/30d y estado de momentum por partido
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pactometro as pm
from scraper import medias_ponderadas

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HIST_PATH = DATA_DIR / "historico_diario.json"
ENCUESTAS_PATH = DATA_DIR / "encuestas_limpias.json"

PARTIDOS_MOMENTUM = ["PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF"]

# Umbrales de clasificación de momentum (pp, media 7d vs 14d previas)
UMBRAL_FUERTE = 1.0
UMBRAL_ASCENSO = 0.3
UMBRAL_RETROCESO = -0.3
UMBRAL_Caida = -1.0


# ───────────────── persistence ─────────────────

def cargar_historico() -> dict:
    if not HIST_PATH.exists():
        return {"actualizado": None, "dias": {}}
    try:
        datos = json.loads(HIST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"actualizado": None, "dias": {}}
    if not isinstance(datos, dict) or "dias" not in datos:
        return {"actualizado": None, "dias": {}}
    return datos


def guardar_historico(hist: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    hist["actualizado"] = datetime.now().isoformat(timespec="seconds")
    HIST_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    return HIST_PATH


# ───────────────── snapshots ─────────────────

def construir_snapshot(medias: dict, fecha: date, origen: str = "live") -> dict:
    """Instantánea: medias + escaños + mejor bloque para una fecha."""
    proy = pm.proyectar_escaños(medias)
    bloques = pm.simular_bloques(proy["escaños"])
    absolutos = [b for b in bloques if b["alcanza_absoluta"]]
    mayoritario = absolutos[0] if absolutos else (bloques[0] if bloques else None)
    return {
        "fecha": fecha.isoformat(),
        "medias": {k: round(float(v), 2) for k, v in medias.items() if v is not None},
        "escaños": proy["escaños"],
        "total_escaños": proy["total"],
        "bloque_mayoritario": mayoritario,
        "origen": origen,
    }


def registrar_hoy(encuestas: list[dict] | None = None) -> dict:
    """Guarda/sobrescribe la instantánea de hoy con las medias vivas."""
    if encuestas is None:
        from scraper import aplicar_filtros, extraer_encuestas, fetch_html, URL_WIKI

        # Preferir datos ya limpios en disco
        if ENCUESTAS_PATH.exists():
            datos = json.loads(ENCUESTAS_PATH.read_text(encoding="utf-8"))
            incluidas = datos.get("encuestas") or []
            medias = datos.get("medias_actual_14d") or datos.get("medias") or {}
        else:
            html = fetch_html(URL_WIKI)
            crudas = extraer_encuestas(html)
            incluidas, _, _ = aplicar_filtros(crudas)
            medias = medias_ponderadas(incluidas, date.today(), filtro_ventana=(0, 14))
    else:
        incluidas = encuestas
        medias = medias_ponderadas(incluidas, date.today(), filtro_ventana=(0, 14))

    if not medias:
        raise ValueError("No hay medias para registrar el día")

    hist = cargar_historico()
    hoy = date.today()
    snap = construir_snapshot(medias, hoy, origen="live")
    snap["momentum"] = calcular_momentum(incluidas if incluidas else None, hoy)
    hist["dias"][hoy.isoformat()] = snap  # sobrescribe si ya existía

    # Backfill si hace falta
    if len(hist["dias"]) < 7:
        backfill(hist, ENCUESTAS_PATH if ENCUESTAS_PATH.exists() else None)

    guardar_historico(hist)
    return snap


def backfill(hist: dict, encuestas_path: Path | None = None, dias: int = 30,
             intervalo: int = 3) -> int:
    """Reconstruye los últimos `dias` días cada `intervalo` días si hay <7 registros.

    Usa el historial de encuestas para calcular la media ponderada que habría
    existido en cada fecha (ref = esa fecha).
    """
    if encuestas_path is None:
        encuestas_path = ENCUESTAS_PATH
    if not encuestas_path.exists():
        return 0

    datos = json.loads(encuestas_path.read_text(encoding="utf-8"))
    incluidas = datos.get("encuestas") or []
    if not incluidas:
        return 0

    hoy = date.today()
    creados = 0
    for i in range(0, dias + 1, intervalo):
        d = hoy - timedelta(days=i)
        clave = d.isoformat()
        existente = hist["dias"].get(clave)
        # No pisar instantáneas "live" salvo que sea hoy (ya registrado antes)
        if existente and existente.get("origen") == "live" and d != hoy:
            continue
        if existente and d == hoy and existente.get("origen") == "live":
            continue

        medias = medias_ponderadas(incluidas, d, filtro_ventana=(0, 45))
        if not medias:
            # sin encuestas anteriores a esa fecha
            continue
        snap = construir_snapshot(medias, d, origen="backfill")
        # momentum histórico aproximado con encuestas hasta esa fecha
        snap["momentum"] = calcular_momentum(incluidas, d, ref_encuestas=incluidas)
        hist["dias"][clave] = snap
        creados += 1
    return creados


# ───────────────── momentum ─────────────────

def _clasificar_momentum(delta: float | None) -> str:
    if delta is None:
        return "Estancado ➡️"
    if delta >= UMBRAL_FUERTE:
        return "Subiendo fuerte 🚀"
    if delta >= UMBRAL_ASCENSO:
        return "En ligero ascenso 📈"
    if delta > UMBRAL_RETROCESO:
        return "Estancado ➡️"
    if delta > UMBRAL_Caida:
        return "En retroceso 📉"
    return "Caída libre ⚠️"


def calcular_momentum(
    incluidas: list[dict] | None,
    hoy: date | None = None,
    ref_encuestas: list[dict] | None = None,
) -> dict:
    """Por partido: delta_1d, delta_7d, delta_30d y estado de impulso.

    Momentum = media ponderada últimos 7 días vs 14 días anteriores.
    """
    if hoy is None:
        hoy = date.today()
    enc = ref_encuestas if ref_encuestas is not None else incluidas
    if not enc:
        return {}

    m_hoy = medias_ponderadas(enc, hoy, filtro_ventana=(0, 1))
    m_1d = medias_ponderadas(enc, hoy, filtro_ventana=(1, 2))
    m_7d = medias_ponderadas(enc, hoy, filtro_ventana=(0, 7))
    m_7d_prev = medias_ponderadas(enc, hoy, filtro_ventana=(7, 21))
    m_14d_prev = medias_ponderadas(enc, hoy, filtro_ventana=(7, 21))  # 14d previas ≈ 7-21
    m_30d = medias_ponderadas(enc, hoy, filtro_ventana=(0, 30))
    m_30d_prev = medias_ponderadas(enc, hoy, filtro_ventana=(30, 60))

    partidos = set()
    for d in (m_hoy, m_1d, m_7d, m_7d_prev, m_30d):
        partidos.update(d.keys())

    out: dict[str, dict] = {}
    for p in sorted(partidos):
        actual = m_7d.get(p, m_hoy.get(p))
        anterior = m_7d_prev.get(p)
        if actual is None:
            continue
        # Derivada de tendencia: 7d recientes vs 14d previas
        if anterior is not None:
            mom_delta = round(actual - anterior, 2)
        else:
            mom_delta = None

        ref_1 = m_hoy.get(p)
        prev_1 = m_1d.get(p)
        delta_1d = round(ref_1 - prev_1, 2) if (ref_1 is not None and prev_1 is not None) else None

        act_7 = m_7d.get(p)
        prev_7 = m_7d_prev.get(p)
        delta_7d = round(act_7 - prev_7, 2) if (act_7 is not None and prev_7 is not None) else None

        act_30 = m_30d.get(p)
        prev_30 = m_30d_prev.get(p)
        delta_30d = round(act_30 - prev_30, 2) if (act_30 is not None and prev_30 is not None) else None

        out[p] = {
            "media_7d": round(actual, 2),
            "delta_1d": delta_1d,
            "delta_7d": delta_7d,
            "delta_30d": delta_30d,
            "momentum_delta": mom_delta,
            "estado": _clasificar_momentum(mom_delta if mom_delta is not None else delta_7d),
        }
    return out


def variacion_escaños(hist: dict, dias: int = 7) -> dict[str, int]:
    """Cambio de escaños de cada partido respecto a hace `dias` días (snapshot)."""
    if not hist.get("dias"):
        return {}
    hoy = date.today()
    claves = sorted(hist["dias"].keys())
    actual = hist["dias"].get(hoy.isoformat()) or hist["dias"][claves[-1]]
    objetivo = (hoy - timedelta(days=dias)).isoformat()
    # snapshot más cercano a la fecha objetivo
    ant = None
    for k in claves:
        if k <= objetivo:
            ant = hist["dias"][k]
    if ant is None:
        ant = hist["dias"][claves[0]]
    esc_act = actual.get("escaños") or {}
    esc_ant = ant.get("escaños") or {}
    partidos = set(esc_act) | set(esc_ant)
    return {p: esc_act.get(p, 0) - esc_ant.get(p, 0) for p in partidos}


def ganadores_perdedores(hist: dict, periodo: int = 7) -> list[dict]:
    """Lista ordenada de variaciones (votos pp y escaños) para el gráfico."""
    if not hist.get("dias"):
        return []
    claves = sorted(hist["dias"].keys())
    hoy = date.today()
    actual = hist["dias"].get(hoy.isoformat()) or hist["dias"][claves[-1]]
    objetivo = (hoy - timedelta(days=periodo)).isoformat()
    ant = None
    for k in claves:
        if k <= objetivo:
            ant = hist["dias"][k]
    if ant is None:
        ant = hist["dias"][claves[0]]

    med_act = actual.get("medias") or {}
    med_ant = ant.get("medias") or {}
    esc_act = actual.get("escaños") or {}
    esc_ant = ant.get("escaños") or {}

    filas = []
    for p in PARTIDOS_MOMENTUM:
        a = med_act.get(p)
        b = med_ant.get(p)
        if a is None and b is None:
            continue
        d_pp = round((a or 0) - (b or 0), 2)
        d_esc = esc_act.get(p, 0) - esc_ant.get(p, 0)
        filas.append({"partido": p, "delta_pp": d_pp, "delta_escaños": d_esc})
    # incluir regionalistas con cambios de escaños relevantes
    for p in set(esc_act) | set(esc_ant):
        if p in PARTIDOS_MOMENTUM:
            continue
        d_esc = esc_act.get(p, 0) - esc_ant.get(p, 0)
        d_pp = round((med_act.get(p) or 0) - (med_ant.get(p) or 0), 2)
        if d_esc != 0 or abs(d_pp) >= 0.2:
            filas.append({"partido": p, "delta_pp": d_pp, "delta_escaños": d_esc})
    filas.sort(key=lambda x: x["delta_pp"], reverse=True)
    return filas


def snapshot_en_fecha(hist: dict, clave: str) -> dict | None:
    """Snapshot para una fecha concreta (o el más reciente si no existe)."""
    if not hist.get("dias"):
        return None
    if clave in hist["dias"]:
        return hist["dias"][clave]
    claves = sorted(hist["dias"].keys())
    anteriores = [k for k in claves if k <= clave]
    if anteriores:
        return hist["dias"][anteriores[-1]]
    return hist["dias"][claves[0]]


def main() -> int:
    def p(s: str) -> None:
        try:
            sys.stdout.buffer.write((s + "\n").encode("utf-8", "replace"))
            sys.stdout.buffer.flush()
        except Exception:
            print(s.encode("ascii", "replace").decode("ascii"))

    p("[tracker] Registrando instantanea diaria...")
    snap = registrar_hoy()
    hist = cargar_historico()
    n = len(hist.get("dias", {}))
    bloque = (snap.get("bloque_mayoritario") or {}).get("bloque", "-")
    p(f"[tracker] Hoy {snap['fecha']}: {snap['total_escaños']} escaños | bloque={bloque}")
    p(f"[tracker] Dias en historico: {n}")
    mom = snap.get("momentum") or {}
    for part in PARTIDOS_MOMENTUM:
        if part in mom:
            m = mom[part]
            p(f"  {part}: {m['media_7d']}% | 7d {m['delta_7d']} | {m['estado']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[tracker] Error: {exc}", file=sys.stderr)
        raise
