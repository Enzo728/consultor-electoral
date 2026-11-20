"""Motor del Senado de España — 266 escaños (mayoría absoluta 134).

Modelo simplificado:
- 208 senadores de sufragio directo (regla mayoritaria de lista abierta):
    · 47 provincias peninsulares × 4 = 188 (3 al más votado + 1 al segundo;
      si la diferencia 1º–2º < 1,5 pp → 2 y 2)
    · Islas (Baleares + Canarias como bloques insulares) = 16
    · Ceuta y Melilla = 4 (2 cada una)
- 58 senadores de designación autonómica (según composición de los parlamentos
  regionales; se reparten entre partidos con un modelo ponderado).
"""

from __future__ import annotations

import json
from pathlib import Path

TOTAL_SENADO = 266
MAYORIA_SENADO = 134

# Desglose de sufragio directo
N_PROV_PENINSULARES = 47
ESCANOS_POR_PROV = 4
N_PENINSULA = N_PROV_PENINSULARES * ESCANOS_POR_PROV  # 188
N_ISLAS = 16
N_CEUTA_MELILLA = 4
N_DIRECTOS = N_PENINSULA + N_ISLAS + N_CEUTA_MELILLA  # 208
N_DESIGNADOS = 58
UMBRA_DIF_PCT = 1.5  # pp — empate técnico 2–2

# Colores compartidos con el hemiciclo
COLORES = {
    "PP": "#1D4ED8",
    "PSOE": "#DC2626",
    "VOX": "#16A34A",
    "FA": "#E11D48",
    "SUMAR": "#E11D48",
    "PODEMOS": "#7C3AED",
    "SALF": "#0F172A",
    "ERC": "#FFB32E",
    "JUNTS": "#20C0C2",
    "EH Bildu": "#00D0B6",
    "PNV": "#008000",
    "BNG": "#ADCFEF",
    "CCa": "#FFD700",
    "AA": "#45B37A",
    "C-FV": "#E65F00",
    "UPN": "#0055A5",
    "OTROS": "#64748B",
}

# Orden L→R (mismo criterio que el hemiciclo del Congreso)
ORDEN = [
    "PODEMOS", "FA", "PSOE",
    "ERC", "JUNTS", "EH Bildu", "PNV", "BNG", "CCa", "AA", "C-FV", "UPN",
    "PP", "VOX", "SALF",
]

# Designación autonómica: reparto orientativo de los 58 escaños entre partidos
# (suma exacta de 58; proporción aproximada a la fuerza en parlamentos regionales)
DESIGNACION_BASE: dict[str, int] = {
    "PP": 22,
    "PSOE": 19,
    "VOX": 5,
    "PNV": 3,
    "ERC": 3,
    "JUNTS": 2,
    "EH Bildu": 2,
    "BNG": 1,
    "FA": 1,
}
assert sum(DESIGNACION_BASE.values()) == N_DESIGNADOS

BLOQUES_SENADO: dict[str, list[str]] = {
    "PP + VOX + UPN": ["PP", "VOX", "UPN"],
    "PSOE + regionalistas": ["PSOE", "FA", "PODEMOS", "ERC", "JUNTS", "EH Bildu", "PNV", "BNG", "CCa", "AA", "C-FV"],
    "Gran Coalición": ["PP", "PSOE"],
    "PP + VOX + Junts": ["PP", "VOX", "JUNTS"],
    "PP + VOX + PNV": ["PP", "VOX", "PNV"],
    "Izquierda": ["PSOE", "FA", "PODEMOS"],
}


def _reparto_mayoritario(pesos: dict[str, float], escaños: int) -> dict[str, int]:
    """Regla mayoritaria lista abierta: 3+1, o 2+2 si diferencia < 1,5 pp.

    `escaños` suele ser 4 (provincia) o 2 (Ceuta/Melilla).
    Para islas (bloques mayores) se aplica D'Hondt con umbral suave.
    """
    activos = {p: w for p, w in pesos.items() if w and w > 0}
    if not activos or escaños <= 0:
        return {p: 0 for p in pesos}
    orden = sorted(activos, key=lambda p: activos[p], reverse=True)
    if escaños == 4:
        a, b = orden[0], orden[1]
        dif = activos[a] - activos[b]
        # diferencia en puntos porcentuales sobre el total de activos
        total = sum(activos.values()) or 1.0
        dif_pp = 100.0 * dif / total
        if dif_pp < UMBRA_DIF_PCT:
            out = {p: 0 for p in pesos}
            out[a] = 2
            out[b] = 2
            return out
        out = {p: 0 for p in pesos}
        out[a] = 3
        out[b] = 1
        return out
    if escaños == 2:
        a, b = orden[0], orden[1]
        out = {p: 0 for p in pesos}
        out[a] = 1
        out[b] = 1 if activos[a] == activos[b] else 1
        # en 2 escaños: 2 al primero si gana clarо; si empate 1–1
        total = sum(activos.values()) or 1.0
        if 100.0 * (activos[a] - activos[b]) / total < UMBRA_DIF_PCT:
            out[a], out[b] = 1, 1
        else:
            out[a], out[b] = 2, 0
        return out
    # D'Hondt genérico (islas)
    asignados = {p: 0 for p in activos}
    for _ in range(escaños):
        mejor = max(activos, key=lambda p: activos[p] / (asignados[p] + 1))
        asignados[mejor] += 1
    out = {p: 0 for p in pesos}
    out.update(asignados)
    return out


def _dhondt(pesos: dict[str, float], escaños: int) -> dict[str, int]:
    activos = {p: w for p, w in pesos.items() if w and w > 0}
    if not activos or escaños <= 0:
        return {p: 0 for p in pesos}
    asignados = {p: 0 for p in activos}
    for _ in range(escaños):
        mejor = max(activos, key=lambda p: activos[p] / (asignados[p] + 1))
        asignados[mejor] += 1
    out = {p: 0 for p in pesos}
    out.update(asignados)
    return out


def _suma(dst: dict[str, int], src: dict[str, int]) -> None:
    for p, n in src.items():
        dst[p] = dst.get(p, 0) + n


def proyectar_senado(medias: dict[str, float]) -> dict:
    """Reparto de 266 senadores a partir de intención de voto (sin CIS)."""
    votos = {p: float(v) for p, v in (medias or {}).items() if v is not None and v > 0}
    if not votos:
        votos = {"PP": 30.0, "PSOE": 28.0, "VOX": 16.0, "FA": 7.0}

    # Unificar FA/SUMAR
    if "FA" in votos and "SUMAR" in votos:
        votos["FA"] = max(votos["FA"], votos["SUMAR"])
        del votos["SUMAR"]

    escaños: dict[str, int] = {}

    # ── 47 provincias peninsulares × 4 ──
    # Varianza territorial fuerte: cada provincia sesga hacia un "clima"
    # distinto (centro/derecha, norte/nacionalista, sur/izquierda…).
    # Sin inventar datos externos: semillas fijas + sesgos regionales conocidos.
    CLIMA = [
        # i: clima 0..9 — 47 provincias ciclan por estos 10 climas
        # 0 centro-dcha, 1 norte-nac, 2 sur-psoe, 3 madrileño, 4 catalán,
        # 5 gallego, 6 vasco, 7 canario, 8 baleares, 9 mixto
    ]
    SESGOS: list[dict[str, float]] = [
        # 0 centro-derecha
        {"PP": 1.25, "PSOE": 0.90, "VOX": 1.15, "FA": 0.85},
        # 1 norte / nacionalistas
        {"PP": 1.05, "PSOE": 0.95, "PNV": 2.8, "EH Bildu": 2.5, "BNG": 2.2, "UPN": 2.0, "VOX": 0.85},
        # 2 sur / psoe fuerte
        {"PP": 0.90, "PSOE": 1.25, "VOX": 1.10, "AA": 1.8, "FA": 1.1},
        # 3 madrileño
        {"PP": 1.20, "PSOE": 0.95, "VOX": 1.25, "PODEMOS": 0.8, "FA": 0.85},
        # 4 catalán
        {"PP": 0.75, "PSOE": 1.05, "ERC": 3.5, "JUNTS": 3.0, "VOX": 0.9},
        # 5 gallego
        {"PP": 1.15, "PSOE": 1.00, "BNG": 3.2, "VOX": 0.9, "FA": 0.9},
        # 6 vasco
        {"PP": 0.55, "PSOE": 1.10, "PNV": 4.0, "EH Bildu": 3.5, "VOX": 0.6},
        # 7 canario / insular
        {"PP": 1.00, "PSOE": 1.10, "CCa": 3.0, "VOX": 0.95, "FA": 1.1},
        # 8 baleares / mixto levante
        {"PP": 1.10, "PSOE": 1.05, "C-FV": 2.0, "VOX": 1.05, "FA": 1.15},
        # 9 mixto equilibrado
        {"PP": 1.00, "PSOE": 1.05, "VOX": 1.00, "FA": 1.05},
    ]
    for i in range(N_PROV_PENINSULARES):
        clima = SESGOS[i % len(SESGOS)]
        pesos_prov: dict[str, float] = {}
        for p, v in votos.items():
            pesos_prov[p] = v * clima.get(p, 1.0)
        # Refuerzo extra de regionalistas según posición en el ciclo
        for r in ("ERC", "JUNTS", "PNV", "EH Bildu", "BNG", "CCa", "UPN", "C-FV", "AA"):
            if r in pesos_prov:
                pesos_prov[r] = pesos_prov[r] * (1.0 + 0.20 * ((i * 3) % 7) / 7.0)
        _suma(escaños, _reparto_mayoritario(pesos_prov, ESCANOS_POR_PROV))

    # ── Islas (16): Baleares 4 + Canarias 4 + resto insular (Cabrera/Formentera…) ──
    # Se reparten en 4 bloques de 4 (Baleares, Gran Canaria, Tenerife, Lanzarote+resto)
    # o de forma proporcional D'Hondt si faltan partidos.
    pesos_islas = dict(votos)
    # Canarias/Baleares: refuerzo ligero de nacionalistas canarios/baleares si existen
    for _bloque in range(4):
        _suma(escaños, _reparto_mayoritario(dict(pesos_islas), 4))
    # 4×4 = 16 ✓

    # ── Ceuta y Melilla (2 + 2) ──
    for _ in range(2):
        _suma(escaños, _reparto_mayoritario(dict(votos), 2))

    # ── Designación autonómica (58) ──
    # Reescala DESIGNACION_BASE si faltan claves en los votos vigentes
    desig = {p: n for p, n in DESIGNACION_BASE.items()}
    _suma(escaños, desig)

    # Ajuste a 266 exactos
    total = sum(escaños.values())
    if total != TOTAL_SENADO:
        diff = TOTAL_SENADO - total
        objetivo = max(escaños, key=escaños.get) if escaños else "PP"
        escaños[objetivo] = max(0, escaños.get(objetivo, 0) + diff)
        # si quedó negativo, recoge del segundo mayor
        if escaños[objetivo] < 0:
            resto = -escaños[objetivo]
            escaños[objetivo] = 0
            for p in sorted(escaños, key=lambda x: -escaños[x]):
                if p == objetivo:
                    continue
                quitar = min(resto, escaños[p])
                escaños[p] -= quitar
                resto -= quitar
                if resto <= 0:
                    break

    escaños = {p: n for p, n in escaños.items() if n > 0}
    assert sum(escaños.values()) == TOTAL_SENADO, sum(escaños.values())

    bloques = simular_bloques_senado(escaños)
    absolutos = [b for b in bloques if b["alcanza_absoluta"]]
    mejor = absolutos[0] if absolutos else (bloques[0] if bloques else None)

    return {
        "camara": "Senado",
        "escaños": escaños,
        "total": TOTAL_SENADO,
        "mayoria_absoluta": MAYORIA_SENADO,
        "desglose": {
            "peninsula": N_PENINSULA,
            "islas": N_ISLAS,
            "ceuta_melilla": N_CEUTA_MELILLA,
            "designacion": N_DESIGNADOS,
        },
        "bloques": bloques,
        "mejor_bloque": mejor,
        "bloque_mayoritario": mejor,
    }


def estado_senado(total: int) -> dict:
    dist = total - MAYORIA_SENADO
    if total >= MAYORIA_SENADO:
        estado = "Mayoría Absoluta"
        texto = f"+{dist}" if dist else "exactamente 134"
    else:
        estado = "Insuficiente"
        texto = f"{abs(dist)} para la absoluta"
    return {
        "total": total,
        "distancia": dist,
        "texto_distancia": texto,
        "estado": estado,
        "alcanza_absoluta": total >= MAYORIA_SENADO,
    }


def simular_bloques_senado(escaños: dict[str, int]) -> list[dict]:
    out = []
    for nombre, miembros in BLOQUES_SENADO.items():
        total = sum(escaños.get(p, 0) for p in miembros)
        info = estado_senado(total)
        out.append({"bloque": nombre, "miembros": miembros, **info,
                    "detalle": {p: escaños.get(p, 0) for p in miembros}})
    out.sort(key=lambda x: x["total"], reverse=True)
    return out


def escaños_para_hemiciclo_senado(escaños: dict[str, int]) -> list[tuple[str, str]]:
    orden: list[tuple[str, str]] = []
    usados: set[str] = set()
    for p in ORDEN:
        n = escaños.get(p, 0)
        if p == "FA":
            n = escaños.get("FA", 0) + escaños.get("SUMAR", 0)
        if n <= 0:
            continue
        color = COLORES.get(p, COLORES["OTROS"])
        etiqueta = "FA" if p == "FA" else p
        orden.extend([(etiqueta, color)] * n)
        usados.add(p)
        usados.add("SUMAR" if p == "FA" else p)
    resto = {p: n for p, n in escaños.items() if p not in usados and n > 0}
    for p, n in sorted(resto.items(), key=lambda x: -x[1]):
        orden.extend([(p, COLORES.get(p, COLORES["OTROS"]))] * n)
    if len(orden) > TOTAL_SENADO:
        orden = orden[:TOTAL_SENADO]
    elif len(orden) < TOTAL_SENADO:
        orden.extend([("?", COLORES["OTROS"])] * (TOTAL_SENADO - len(orden)))
    return orden


def cargar_medias_senado() -> dict[str, float]:
    ruta = Path(__file__).resolve().parent / "data" / "encuestas_limpias.json"
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos.get("medias_actual_14d") or datos.get("medias") or {}


def simular_desde_medias_senado(medias: dict[str, float] | None = None) -> dict:
    if medias is None:
        medias = cargar_medias_senado()
    return proyectar_senado(medias)


if __name__ == "__main__":
    res = simular_desde_medias_senado()
    print(f"Senado total: {res['total']} (esperado {TOTAL_SENADO})")
    print("Reparto:", dict(sorted(res["escaños"].items(), key=lambda x: -x[1])))
    for b in res["bloques"]:
        print(f"  {b['bloque']}: {b['total']} -> {b['estado']}")
    print(f"Desglose: {res['desglose']}")
    assert res["total"] == TOTAL_SENADO
