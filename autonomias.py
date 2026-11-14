"""Motor de Gobiernos Autonómicos — 10 CCAA con D'Hondt y pactos.

Totales oficiales verificados en Wikipedia (nov 2026):
  Madrid 135/68 · Andalucía 109/55 · C. Valenciana 99/50 · Cataluña 135/68
  Galicia 75/38 · País Vasco 75/38 · Castilla y León 82/42 (Segovia +1 en 2026)
  CLM 33/17 · Aragón 67/34 · Extremadura 65/33

CLM usa D'Hondt PROVINCIAL real con umbral 3% por provincia
(Albacete 7, C.Real 7, Cuenca 5, Guadalajara 5, Toledo 9).
Sin encuestas recientes → "Sin encuestas recientes fiables" (NUNCA inventado).
"""

from __future__ import annotations

import json
from pathlib import Path

# ───────────────── Paleta (compatible con hemiciclo) ─────────────────
COLORES: dict[str, str] = {
    "PP": "#1D4ED8",
    "PSOE": "#DC2626",
    "VOX": "#16A34A",
    "FA": "#E11D48",
    "SUMAR": "#E11D48",
    "PODEMOS": "#7C3AED",
    "SALF": "#0F172A",
    "Cs": "#E87500",
    "ERC": "#FFB32E",
    "JUNTS": "#20C0C2",
    "EH Bildu": "#00D0B6",
    "PNV": "#008000",
    "BNG": "#ADCFEF",
    "CCa": "#FFD700",
    "AA": "#45B37A",
    "C-FV": "#E65F00",
    "UPN": "#0055A5",
    "POR A": "#0E9F6E",
    "Por Andalucía": "#0E9F6E",
    "Adelante": "#6D28D9",
    "UPL": "#059669",
    "Soria Ya": "#0891B2",
    "PCAL": "#A3E635",
    "PAR": "#C4B5FD",
    "CHA": "#F472B6",
    "Aragón Existe": "#34D399",
    "PA-AV": "#2DD4BF",
    "Compromís": "#EA580C",
    "Ahal Dugu": "#7C3AED",
    "PSE": "#DC2626",
    "Más Madrid": "#0D9488",
    "MC": "#14B8A6",
    "UpE": "#64748B",
    "JxE": "#94A3B8",
    "OTROS": "#64748B",
}

# Orden L→R por familia (para hemiciclo autonómico)
ORDEN_BASE = [
    "PODEMOS", "Ahal Dugu", "FA", "SUMAR", "Comuns",
    "PSOE", "PSE", "PSC",
    "ERC", "JUNTS", "EH Bildu", "PNV", "BNG", "CCa",
    "AA", "Por Andalucía", "POR A", "Adelante", "Compromís",
    "C-FV", "UPL", "Soria Ya", "PCAL", "PAR", "CHA", "Aragón Existe",
    "PA-AV", "UpE", "JxE", "MC", "Más Madrid",
    "Cs", "PP", "UPN", "VOX", "SALF",
]

# ───────────────── Configuración de CCAA ─────────────────
# umbral: barrera electoral legal (%)
# SIN pesos_base: solo datos scrapeados de Wikipedia con fecha real.

AUTONOMIAS: dict[str, dict] = {
    "Madrid": {
        "id": "madrid",
        "parlamento": "Asamblea de Madrid",
        "escaños": 135,
        "mayoria": 68,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "PODEMOS", "FA", "SALF", "Cs", "Más Madrid", "MC"],
        "wiki": ["Elecciones a la Asamblea de Madrid de 2023"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "PODEMOS", "FA"],
            ["PP", "PSOE"],
            ["PSOE", "Más Madrid"],
        ],
    },
    "Cataluña": {
        "id": "cataluna",
        "parlamento": "Parlamento de Cataluña",
        "escaños": 135,
        "mayoria": 68,
        "umbral": 3.0,
        "partidos": ["PSC", "JUNTS", "ERC", "PP", "VOX", "PODEMOS", "Comuns", "SALF"],
        "wiki": ["Elecciones al Parlamento de Cataluña de 2028"],
        "pactos": [
            ["PSC", "ERC"],
            ["PSC", "JUNTS"],
            ["PP", "VOX"],
            ["PSC", "ERC", "Comuns"],
        ],
    },
    "Andalucía": {
        "id": "andalucia",
        "parlamento": "Parlamento de Andalucía",
        "escaños": 109,
        "mayoria": 55,
        "umbral": 3.0,
        "partidos": ["PP", "PSOE", "VOX", "POR A", "AA", "PODEMOS", "SALF"],
        "wiki": ["Elecciones al Parlamento de Andalucía de 2026"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "POR A"],
            ["PSOE", "AA", "PODEMOS"],
            ["PP", "PSOE"],
        ],
    },
    "Comunidad Valenciana": {
        "id": "cvalenciana",
        "parlamento": "Corts Valencianes",
        "escaños": 99,
        "mayoria": 50,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "Compromís", "PODEMOS", "FA", "SALF", "Cs"],
        "wiki": ["Elecciones a las Cortes Valencianas de 2023"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "Compromís"],
            ["PSOE", "Compromís", "PODEMOS"],
            ["PP", "PSOE"],
        ],
    },
    "Galicia": {
        "id": "galicia",
        "parlamento": "Parlamento de Galicia",
        "escaños": 75,
        "mayoria": 38,
        "umbral": 3.0,
        "partidos": ["PP", "PSOE", "BNG", "VOX", "PODEMOS", "FA", "SALF"],
        "wiki": ["Elecciones al Parlamento de Galicia de 2024"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "BNG"],
            ["BNG", "PSOE", "PODEMOS"],
            ["PP", "PSOE"],
        ],
    },
    "País Vasco": {
        "id": "paisvasco",
        "parlamento": "Parlamento Vasco",
        "escaños": 75,
        "mayoria": 38,
        "umbral": 3.0,
        "partidos": ["PNV", "EH Bildu", "PSE", "PP", "VOX", "PODEMOS", "Ahal Dugu", "SALF"],
        "wiki": ["Elecciones al Parlamento Vasco de 2024"],
        "pactos": [
            ["PNV", "PSE"],
            ["EH Bildu", "PSE"],
            ["PP", "VOX"],
            ["PSE", "PODEMOS", "Ahal Dugu"],
        ],
    },
    "Castilla y León": {
        "id": "cyl",
        "parlamento": "Cortes de Castilla y León",
        "escaños": 82,
        "mayoria": 42,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "UPL", "Soria Ya", "PCAL", "PODEMOS", "FA", "SALF", "Cs"],
        "wiki": ["Elecciones a las Cortes de Castilla y León de 2026"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "UPL"],
            ["PSOE", "PODEMOS", "FA"],
            ["PP", "PSOE"],
        ],
    },
    "Castilla-La Mancha": {
        "id": "clm",
        "parlamento": "Cortes de Castilla-La Mancha",
        "escaños": 33,
        "mayoria": 17,
        "umbral": 3.0,
        "partidos": ["PSOE", "PP", "VOX", "PODEMOS", "FA", "SALF", "Cs"],
        "wiki": ["Elecciones a las Cortes de Castilla-La Mancha de 2023"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "PODEMOS", "FA"],
            ["PSOE", "PP"],
        ],
        # D'Hondt PROVINCIAL (Ley Electoral CLM): umbral 3% por provincia
        "provincial": {
            "Albacete": 7,
            "Ciudad Real": 7,
            "Cuenca": 5,
            "Guadalajara": 5,
            "Toledo": 9,
        },
    },
    "Aragón": {
        "id": "aragon",
        "parlamento": "Cortes de Aragón",
        "escaños": 67,
        "mayoria": 34,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "CHA", "PAR", "Aragón Existe", "PA-AV", "PODEMOS", "FA", "SALF"],
        "wiki": ["Elecciones a las Cortes de Aragón de 2026"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "CHA"],
            ["PSOE", "Aragón Existe"],
            ["PP", "PSOE"],
        ],
    },
    "Extremadura": {
        "id": "extremadura",
        "parlamento": "Asamblea de Extremadura",
        "escaños": 65,
        "mayoria": 33,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "UpE", "JxE", "PODEMOS", "FA", "SALF", "Cs"],
        "wiki": ["Elecciones a la Asamblea de Extremadura de 2025"],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "UpE"],
            ["PSOE", "JxE"],
            ["PP", "PSOE"],
        ],
    },
}

SIN_ENCUESTAS = "Sin encuestas recientes fiables"


def validar_config() -> None:
    for nombre, cfg in AUTONOMIAS.items():
        total = cfg["escaños"]
        may = cfg["mayoria"]
        assert may == total // 2 + 1, f"{nombre}: mayoría {may} ≠ {total//2+1}"
        assert total > 0
        assert cfg["umbral"] in (3.0, 5.0), f"{nombre}: umbral {cfg['umbral']}"
        assert len(cfg["partidos"]) >= 3
        prov = cfg.get("provincial")
        if prov:
            s = sum(prov.values())
            assert s == total, f"{nombre}: provincias {s} ≠ {total}"


def _dhondt(pesos: dict[str, float], escaños: int, umbral_pct: float) -> dict[str, int]:
    """D'Hondt con barrera: partidos bajo umbral no reciben escaños."""
    if escaños <= 0 or not pesos:
        return {p: 0 for p in pesos}
    activos = {
        p: w for p, w in pesos.items()
        if w is not None and w > 0 and w >= umbral_pct
    }
    if not activos:
        # si todos bajo umbral, reparte igual entre los >0 (mejor que no repartir)
        activos = {p: w for p, w in pesos.items() if w is not None and w > 0}
    if not activos:
        return {p: 0 for p in pesos}
    asignados = {p: 0 for p in activos}
    for _ in range(escaños):
        mejor = max(activos, key=lambda p: activos[p] / (asignados[p] + 1))
        asignados[mejor] += 1
    out = {p: 0 for p in pesos}
    out.update(asignados)
    fallos = escaños - sum(out.values())
    if fallos > 0:
        extra = {p: w for p, w in activos.items()}
        for _ in range(fallos):
            if not extra:
                break
            mejor = max(extra, key=lambda p: extra[p])
            out[mejor] = out.get(mejor, 0) + 1
    return out


def _dhondt_provincial(
    votos: dict[str, float],
    provincias: dict[str, int],
    umbral_pct: float,
) -> dict[str, int]:
    """D'Hondt por provincia con umbral 3% en cada una (CLM)."""
    total = {p: 0 for p in votos}
    for _prov, escaños in provincias.items():
        reparto = _dhondt(votos, escaños, umbral_pct)
        for p, n in reparto.items():
            total[p] = total.get(p, 0) + n
    # Ajuste exacto al total de la CCAA
    s = sum(total.values())
    objetivo_total = sum(provincias.values())
    if s != objetivo_total:
        diff = objetivo_total - s
        if total:
            key = max(total, key=total.get)
            total[key] = total.get(key, 0) + diff
    return {p: n for p, n in total.items() if n > 0}


def estado_bloque(total: int, mayoria: int) -> dict:
    dist = total - mayoria
    if total >= mayoria:
        estado = "Mayoría Absoluta"
        texto = f"+{dist}" if dist else f"exactamente {mayoria}"
    else:
        estado = "Insuficiente"
        texto = f"{abs(dist)} para la absoluta"
    return {
        "total": total,
        "distancia": dist,
        "texto_distancia": texto,
        "estado": estado,
        "alcanza_absoluta": total >= mayoria,
    }


def simular_bloques(escaños: dict[str, int], mayoria: int, pactos: list[list[str]]) -> list[dict]:
    out = []
    for miembros in pactos:
        total = sum(escaños.get(p, 0) for p in miembros)
        info = estado_bloque(total, mayoria)
        nombre = " + ".join(miembros)
        out.append({
            "bloque": nombre,
            "miembros": list(miembros),
            **info,
            "detalle": {p: escaños.get(p, 0) for p in miembros},
        })
    out.sort(key=lambda x: x["total"], reverse=True)
    return out


def proyectar_comunidad(
    nombre: str,
    medias_nacionales: dict[str, float] | None = None,
    medias_locales: dict[str, float] | None = None,
    stats_locales: dict | None = None,
) -> dict:
    """Proyecta el parlamento de una CCAA SOLO con datos reales.

    Si no hay encuestas locales recientes → estado SIN_ENCUESTAS (sin escaños inventados).
    """
    if nombre not in AUTONOMIAS:
        raise KeyError(f"Comunidad desconocida: {nombre}")
    cfg = AUTONOMIAS[nombre]
    umbral = cfg["umbral"]
    mayoria = cfg["mayoria"]
    total = cfg["escaños"]
    partidos = cfg["partidos"]
    cid = cfg["id"]

    # ¿Hay medias locales recientes?
    locales = None
    if medias_locales:
        locales = {p: float(v) for p, v in medias_locales.items()
                   if p in partidos and v and v > 0}
        if len(locales) < 3:
            locales = None

    if stats_locales is not None and not stats_locales.get("reciente", bool(locales)):
        locales = None

    if not locales:
        # SIN encuestas recientes → NUNCA inventar
        return {
            "comunidad": nombre,
            "id": cid,
            "parlamento": cfg["parlamento"],
            "escaños": {},
            "total": total,
            "mayoria_absoluta": mayoria,
            "umbral": umbral,
            "partidos": partidos,
            "medias_usadas": {},
            "bloques": [],
            "mejor_bloque": None,
            "bloque_mayoritario": None,
            "fuente_medias": "sin_datos",
            "aviso": SIN_ENCUESTAS,
            "ultima_encuesta": (stats_locales or {}).get("ultima_encuesta"),
        }

    votos = dict(locales)
    # alias PSC ← PSOE / PSE ← PSOE si hace falta (solo con datos locales ya presentes)
    if "PSC" in partidos and "PSC" not in votos and "PSOE" in votos:
        votos["PSC"] = votos["PSOE"]
    if "PSE" in partidos and "PSE" not in votos and "PSOE" in votos:
        votos["PSE"] = votos["PSOE"]

    votos = {p: v for p, v in votos.items() if p in partidos and v and v > 0}
    if not votos:
        return {
            "comunidad": nombre,
            "id": cid,
            "parlamento": cfg["parlamento"],
            "escaños": {},
            "total": total,
            "mayoria_absoluta": mayoria,
            "umbral": umbral,
            "partidos": partidos,
            "medias_usadas": {},
            "bloques": [],
            "mejor_bloque": None,
            "bloque_mayoritario": None,
            "fuente_medias": "sin_datos",
            "aviso": SIN_ENCUESTAS,
            "ultima_encuesta": (stats_locales or {}).get("ultima_encuesta"),
        }

    prov = cfg.get("provincial")
    if prov:
        escaños = _dhondt_provincial(votos, prov, umbral)
    else:
        escaños = _dhondt(votos, total, umbral)

    s = sum(escaños.values())
    if s != total and escaños:
        diff = total - s
        objetivo = max(escaños, key=escaños.get)
        escaños[objetivo] = escaños.get(objetivo, 0) + diff
        if escaños[objetivo] < 0:
            escaños[objetivo] = 0

    escaños = {p: n for p, n in escaños.items() if n > 0}
    assert sum(escaños.values()) == total, (nombre, sum(escaños.values()), total)

    bloques = simular_bloques(escaños, mayoria, cfg["pactos"])
    absolutos = [b for b in bloques if b["alcanza_absoluta"]]
    mejor = absolutos[0] if absolutos else (bloques[0] if bloques else None)

    return {
        "comunidad": nombre,
        "id": cid,
        "parlamento": cfg["parlamento"],
        "escaños": escaños,
        "total": total,
        "mayoria_absoluta": mayoria,
        "umbral": umbral,
        "partidos": partidos,
        "medias_usadas": votos,
        "bloques": bloques,
        "mejor_bloque": mejor,
        "bloque_mayoritario": mejor,
        "fuente_medias": "locales",
        "aviso": None,
        "ultima_encuesta": (stats_locales or {}).get("ultima_encuesta"),
    }


def cargar_medias_nacionales() -> dict[str, float]:
    ruta = Path(__file__).resolve().parent / "data" / "encuestas_limpias.json"
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos.get("medias_actual_14d") or datos.get("medias") or {}


def cargar_medias_autonomicas() -> dict[str, dict[str, float]]:
    """data/encuestas_autonomicas.json → {comunidad_id: {partido: media}}"""
    ruta = Path(__file__).resolve().parent / "data" / "encuestas_autonomicas.json"
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return datos.get("medias") or {}


def cargar_stats_autonomicas() -> dict[str, dict]:
    ruta = Path(__file__).resolve().parent / "data" / "encuestas_autonomicas.json"
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return datos.get("stats") or {}


def listar_comunidades() -> list[str]:
    return list(AUTONOMIAS.keys())


def proyectar_todas(
    medias_nacionales: dict[str, float] | None = None,
    medias_autonomicas: dict[str, dict[str, float]] | None = None,
    stats_autonomicas: dict[str, dict] | None = None,
) -> dict[str, dict]:
    if medias_nacionales is None:
        medias_nacionales = cargar_medias_nacionales()
    if medias_autonomicas is None:
        medias_autonomicas = cargar_medias_autonomicas()
    if stats_autonomicas is None:
        stats_autonomicas = cargar_stats_autonomicas()
    out = {}
    for nombre in AUTONOMIAS:
        cid = AUTONOMIAS[nombre]["id"]
        locales = medias_autonomicas.get(cid) or medias_autonomicas.get(nombre)
        stats = stats_autonomicas.get(cid)
        out[nombre] = proyectar_comunidad(nombre, medias_nacionales, locales, stats)
    return out


def escaños_para_hemiciclo(escaños: dict[str, int]) -> list[tuple[str, str]]:
    orden: list[tuple[str, str]] = []
    usados: set[str] = set()
    for p in ORDEN_BASE:
        n = escaños.get(p, 0)
        if p == "FA":
            n = escaños.get("FA", 0) + escaños.get("SUMAR", 0)
        if n <= 0:
            continue
        color = COLORES.get(p, COLORES["OTROS"])
        orden.extend([(p if p != "FA" else "FA", color)] * n)
        usados.add(p)
    resto = {p: n for p, n in escaños.items() if p not in usados and n > 0}
    for p, n in sorted(resto.items(), key=lambda x: -x[1]):
        orden.extend([(p, COLORES.get(p, COLORES["OTROS"]))] * n)
    return orden


def posiciones_hemiciclo(n: int, n_filas: int = 7) -> list[tuple[float, float]]:
    import math
    if n_filas < 1:
        n_filas = 1
    base = n // n_filas
    extra = n % n_filas
    conteos = [base + (1 if i < extra else 0) for i in range(n_filas)]
    coords: list[tuple[float, float]] = []
    for fila, cnt in enumerate(conteos):
        r = 0.55 + 0.45 * (fila + 1) / n_filas
        for i in range(cnt):
            if cnt == 1:
                ang = math.pi / 2
            else:
                ang = math.pi - (math.pi * i / (cnt - 1))
            coords.append((r * math.cos(ang), r * math.sin(ang)))
    return coords


if __name__ == "__main__":
    validar_config()
    print(f"CCAA configuradas: {len(AUTONOMIAS)}")
    for nombre, cfg in AUTONOMIAS.items():
        prov = ""
        if cfg.get("provincial"):
            prov = " | prov: " + ", ".join(f"{k} {v}" for k, v in cfg["provincial"].items())
        print(f"  {nombre}: {cfg['escaños']} esc · mayoría {cfg['mayoria']} · umbral {cfg['umbral']}%{prov}")
    todas = proyectar_todas()
    for nombre, res in todas.items():
        if res.get("aviso"):
            print(f"[AVISO] {nombre}: {res['aviso']} (última: {res.get('ultima_encuesta') or '—'})")
            continue
        s = sum(res["escaños"].values())
        ok = "OK" if s == res["total"] else "FAIL"
        print(f"[{ok}] {nombre}: {s}/{res['total']} | mejor={res['mejor_bloque']['bloque'] if res['mejor_bloque'] else '—'}")
        assert s == res["total"]
    print("AUTONOMIAS_OK")
