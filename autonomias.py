"""Motor de Gobiernos Autonómicos — 10 CCAA con D'Hondt y pactos.

Cada comunidad define: total de escaños, mayoría absoluta, barrera legal y
partidos relevantes (incluye fuerzas regionales). Proyección con Ley D'Hondt
simplificada sobre medias ponderadas (sin CIS).
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
# Wikipedia: páginas con tablas de encuestas cuando existen (se scrapea en scraper.py)

AUTONOMIAS: dict[str, dict] = {
    "Madrid": {
        "id": "madrid",
        "parlamento": "Asamblea de Madrid",
        "escaños": 132,
        "mayoria": 67,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "PODEMOS", "FA", "SALF", "Cs", "Más Madrid", "MC"],
        "wiki": [
            "Elecciones a la Asamblea de Madrid de 2027",
            "Elecciones a la Asamblea de Madrid de 2023",
        ],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "PODEMOS", "FA"],
            ["PP", "PSOE"],
            ["PSOE", "Más Madrid"],
        ],
        "pesos_base": {"PP": 34, "PSOE": 27, "VOX": 12, "PODEMOS": 6, "FA": 5, "Más Madrid": 5, "SALF": 3, "MC": 2, "Cs": 2},
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
        "pesos_base": {"PSC": 28, "JUNTS": 22, "ERC": 18, "PP": 10, "VOX": 9, "Comuns": 7, "PODEMOS": 3, "SALF": 3},
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
        "pesos_base": {"PP": 40, "PSOE": 23, "VOX": 14, "POR A": 7, "AA": 7, "PODEMOS": 3, "SALF": 3},
    },
    "Comunidad Valenciana": {
        "id": "cvalenciana",
        "parlamento": "Corts Valencianes",
        "escaños": 99,
        "mayoria": 50,
        "umbral": 5.0,
        "partidos": ["PP", "PSOE", "VOX", "Compromís", "PODEMOS", "FA", "SALF", "Cs"],
        "wiki": [
            "Elecciones a las Cortes Valencianas de 2027",
            "Elecciones a las Cortes Valencianas de 2023",
        ],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "Compromís"],
            ["PSOE", "Compromís", "PODEMOS"],
            ["PP", "PSOE"],
        ],
        "pesos_base": {"PP": 36, "PSOE": 24, "VOX": 15, "Compromís": 9, "PODEMOS": 5, "FA": 4, "SALF": 4, "Cs": 2},
    },
    "Galicia": {
        "id": "galicia",
        "parlamento": "Parlamento de Galicia",
        "escaños": 75,
        "mayoria": 38,
        "umbral": 3.0,
        "partidos": ["PP", "PSOE", "BNG", "VOX", "PODEMOS", "FA", "SALF"],
        "wiki": [
            "Elecciones al Parlamento de Galicia de 2025",
            "Elecciones al Parlamento de Galicia de 2024",
        ],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "BNG"],
            ["BNG", "PSOE", "PODEMOS"],
            ["PP", "PSOE"],
        ],
        "pesos_base": {"PP": 40, "PSOE": 24, "BNG": 22, "VOX": 8, "PODEMOS": 3, "SALF": 3},
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
        "pesos_base": {"PNV": 34, "EH Bildu": 24, "PSE": 22, "PP": 7, "VOX": 5, "PODEMOS": 4, "Ahal Dugu": 3, "SALF": 2},
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
        "pesos_base": {"PP": 35, "PSOE": 30, "VOX": 18, "UPL": 5, "Soria Ya": 2, "PCAL": 2, "PODEMOS": 3, "SALF": 3},
    },
    "Castilla-La Mancha": {
        "id": "clm",
        "parlamento": "Cortes de Castilla-La Mancha",
        "escaños": 33,
        "mayoria": 17,
        "umbral": 5.0,
        "partidos": ["PSOE", "PP", "VOX", "PODEMOS", "FA", "SALF", "Cs"],
        "wiki": [
            "Elecciones a las Cortes de Castilla-La Mancha de 2027",
            "Elecciones a las Cortes de Castilla-La Mancha de 2023",
        ],
        "pactos": [
            ["PP", "VOX"],
            ["PSOE", "PODEMOS", "FA"],
            ["PSOE", "PP"],
        ],
        "pesos_base": {"PSOE": 40, "PP": 34, "VOX": 14, "PODEMOS": 5, "FA": 3, "SALF": 3, "Cs": 2},
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
        "pesos_base": {"PP": 36, "PSOE": 24, "VOX": 17, "CHA": 8, "Aragón Existe": 4, "PAR": 3, "PA-AV": 3, "PODEMOS": 3, "FA": 2, "SALF": 2},
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
        "pesos_base": {"PP": 42, "PSOE": 26, "VOX": 16, "UpE": 8, "JxE": 3, "PODEMOS": 3, "SALF": 2},
    },
}

# Comprobación de totales (se ejecuta en tests / __main__)
def validar_config() -> None:
    for nombre, cfg in AUTONOMIAS.items():
        total = cfg["escaños"]
        may = cfg["mayoria"]
        assert may == total // 2 + 1, f"{nombre}: mayoría {may} ≠ {total//2+1}"
        assert total > 0
        assert cfg["umbral"] in (3.0, 5.0), f"{nombre}: umbral {cfg['umbral']}"
        assert len(cfg["partidos"]) >= 3


def _dhondt(pesos: dict[str, float], escaños: int, umbral_pct: float) -> dict[str, int]:
    """D'Hondt con barrera: partidos bajo umbral reciben peso residual pequeño."""
    if escaños <= 0 or not pesos:
        return {p: 0 for p in pesos}
    ajustado = {
        p: (w if w >= umbral_pct else w * 0.15)
        for p, w in pesos.items()
        if w is not None and w > 0
    }
    if not ajustado:
        ajustado = dict(pesos)
    activos = {p: w for p, w in ajustado.items() if w > 0}
    asignados = {p: 0 for p in activos}
    for _ in range(escaños):
        mejor = max(activos, key=lambda p: activos[p] / (asignados[p] + 1))
        asignados[mejor] += 1
    out = {p: 0 for p in pesos}
    out.update(asignados)
    # Ajuste exacto si algún residual no repartió
    fallos = escaños - sum(out.values())
    if fallos > 0:
        extra = {p: w for p, w in pesos.items() if w > 0}
        for _ in range(fallos):
            if not extra:
                break
            mejor = max(extra, key=lambda p: extra[p])
            out[mejor] = out.get(mejor, 0) + 1
    return out


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
) -> dict:
    """Proyecta el parlamento de una CCAA.

    Prioridad de medias:
    1) medias_locales (encuestas autonómicas scrapeadas)
    2) medias_nacionales filtradas a los partidos de la comunidad + pesos_base
    3) pesos_base por defecto
    """
    if nombre not in AUTONOMIAS:
        raise KeyError(f"Comunidad desconocida: {nombre}")
    cfg = AUTONOMIAS[nombre]
    umbral = cfg["umbral"]
    mayoria = cfg["mayoria"]
    total = cfg["escaños"]
    partidos = cfg["partidos"]

    votos: dict[str, float] = {}
    if medias_locales:
        for p in partidos:
            if p in medias_locales and medias_locales[p]:
                votos[p] = float(medias_locales[p])
        # alias PSC ← PSOE si la encuesta trae PSC
        if "PSC" in partidos and "PSC" not in votos and medias_nacionales:
            if "PSOE" in medias_nacionales:
                votos.setdefault("PSC", float(medias_nacionales["PSOE"]))
        if "PSE" in partidos and "PSE" not in votos and medias_nacionales:
            if "PSOE" in medias_nacionales:
                votos.setdefault("PSE", float(medias_nacionales["PSOE"]))

    if len(votos) < 3 and medias_nacionales:
        for p in partidos:
            if p in votos:
                continue
            src = p
            if p in ("PSC", "PSE") and "PSOE" in medias_nacionales:
                src = "PSOE"
            if p in ("Ahal Dugu",) and "PODEMOS" in medias_nacionales:
                src = "PODEMOS"
            if src in medias_nacionales and medias_nacionales[src]:
                # mezcla 60% nacional + 40% base local
                base = cfg["pesos_base"].get(p, 5.0)
                votos[p] = 0.6 * float(medias_nacionales[src]) + 0.4 * base

    if len(votos) < 3:
        votos = {p: float(v) for p, v in cfg["pesos_base"].items() if p in partidos or True}

    # Solo partidos de la comunidad
    votos = {p: v for p, v in votos.items() if p in partidos and v and v > 0}
    if not votos:
        votos = {p: float(v) for p, v in cfg["pesos_base"].items() if p in partidos}

    escaños = _dhondt(votos, total, umbral)
    # Ajuste exacto
    s = sum(escaños.values())
    if s != total:
        diff = total - s
        objetivo = max(escaños, key=escaños.get) if escaños else partidos[0]
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
        "id": cfg["id"],
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
        "fuente_medias": "locales" if medias_locales else ("mixto" if medias_nacionales else "base"),
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


def listar_comunidades() -> list[str]:
    return list(AUTONOMIAS.keys())


def proyectar_todas(
    medias_nacionales: dict[str, float] | None = None,
    medias_autonomicas: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict]:
    if medias_nacionales is None:
        medias_nacionales = cargar_medias_nacionales()
    if medias_autonomicas is None:
        medias_autonomicas = cargar_medias_autonomicas()
    out = {}
    for nombre in AUTONOMIAS:
        cid = AUTONOMIAS[nombre]["id"]
        locales = medias_autonomicas.get(cid) or medias_autonomicas.get(nombre)
        out[nombre] = proyectar_comunidad(nombre, medias_nacionales, locales)
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
        print(f"  {nombre}: {cfg['escaños']} esc · mayoría {cfg['mayoria']} · umbral {cfg['umbral']}%")
    todas = proyectar_todas()
    for nombre, res in todas.items():
        s = sum(res["escaños"].values())
        ok = "OK" if s == res["total"] else "FAIL"
        print(f"[{ok}] {nombre}: {s}/{res['total']} | mejor={res['mejor_bloque']['bloque'] if res['mejor_bloque'] else '—'}")
        assert s == res["total"]
    print("AUTONOMIAS_OK")
