"""Proyección de escaños del Congreso (350) y simulador de pactos.

Modelo: proporcional ajustado (D'Hondt) con umbral efectivo del 3%,
pool fijo de escaños regionalistas y reparto del resto entre partidos nacionales.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

TOTAL_ESCANOS = 350
MAYORIA_ABSOLUTA = 176
UMBRAL_PCT = 3.0
# Pool realista de escaños nacionalistas/regionalistas en el Congreso
POOL_REGIONALISTAS = 25
# A partir de esta media (pp) un regionalista entra en el pool
MIN_MEDIA_REGIONAL = 0.25
# Umbral operativo para considerar mayoría simple en 2ª vuelta (abstenciones parciales)
MIN_SIMPLE_2A_VUELTA = 171

# Colores editoriales del hemiciclo
COLORES_HEMICICLO = {
    "PP": "#1D4ED8",
    "PSOE": "#DC2626",
    "VOX": "#16A34A",
    "FA": "#E11D48",
    "SUMAR": "#E11D48",
    "PODEMOS": "#7C3AED",
    "SALF": "#0F172A",
    "OTROS": "#64748B",
}

# Orden ideológico del hemiciclo (izquierda → derecha)
ORDEN_HEMICICLO = [
    "PODEMOS",
    "FA",
    "PSOE",
    "ERC",
    "JUNTS",
    "EH Bildu",
    "PNV",
    "BNG",
    "CCa",
    "AA",
    "C-FV",
    "AC",
    "UPN",
    "PP",
    "VOX",
    "SALF",
]

REGIONALISTAS = [
    "ERC", "JUNTS", "EH Bildu", "PNV", "BNG", "CCa", "UPN", "AA", "C-FV", "AC",
]
NACIONALES = ["PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF"]

BLOQUES: dict[str, list[str]] = {
    "Bloque Derecha (PP+VOX+UPN)": ["PP", "VOX", "UPN"],
    "Investidura Progresista/Plurinacional": [
        "PSOE", "FA", "SUMAR", "PODEMOS",
        "ERC", "JUNTS", "EH Bildu", "PNV", "BNG", "CCa", "AA", "C-FV",
    ],
    "Gran Coalición (PP+PSOE)": ["PP", "PSOE"],
    "PP + VOX + Junts": ["PP", "VOX", "JUNTS"],
    "PP + VOX + PNV": ["PP", "VOX", "PNV"],
    "PP + VOX + C-FV": ["PP", "VOX", "C-FV"],
    "PP + PSOE + UPN": ["PP", "PSOE", "UPN"],
    "Izquierda sin regionalistas (PSOE+FA+PODEMOS)": [
        "PSOE", "FA", "SUMAR", "PODEMOS",
    ],
    "Derecha + Junts + PNV": ["PP", "VOX", "JUNTS", "PNV", "UPN"],
}


def _dhondt(pesos: dict[str, float], escaños: int) -> dict[str, int]:
    """Reparto D'Hondt. pesos: partido → peso (votos o media)."""
    activos = {p: w for p, w in pesos.items() if w > 0}
    if escaños <= 0 or not activos:
        return {p: 0 for p in pesos}
    asignados = {p: 0 for p in activos}
    # Optimización: solo los candidatos con opción real
    for _ in range(escaños):
        mejor = max(activos, key=lambda p: activos[p] / (asignados[p] + 1))
        asignados[mejor] += 1
    return {p: asignados.get(p, 0) for p in pesos}


def _normalizar_medias(medias: dict[str, float]) -> dict[str, float]:
    """Unifica FA/SUMAR y devuelve solo claves relevantes con valores >= 0."""
    out: dict[str, float] = {}
    for p, v in (medias or {}).items():
        if v is None or v <= 0:
            continue
        out[p] = float(v)
    # Coalición de izquierda: si existen ambas, manda FA (etiqueta actual)
    if "FA" in out and "SUMAR" in out:
        out["FA"] = max(out["FA"], out["SUMAR"])
        del out["SUMAR"]
    elif "SUMAR" in out and "FA" not in out:
        out["FA"] = out.pop("SUMAR")
    return out


def proyectar_escaños(medias: dict[str, float]) -> dict:
    """Convierte intención de voto ponderada en 350 escaños.

    1) Pool fijo POOL_REGIONALISTAS para regionalistas (D'Hondt relativo).
    2) Resto (350 - pool) entre nacionales con D'Hondt; umbral 3% documentado
       (los porcentajes nacionales ya vienen de medias sin CIS).
    """
    votos = _normalizar_medias(medias)

    # ── Regionalistas: pool fijo ──
    reg_pesos = {
        p: votos[p] for p in REGIONALISTAS
        if p in votos and votos[p] >= MIN_MEDIA_REGIONAL
    }
    if not reg_pesos:
        # Reserva por defecto muy conservadora si faltan datos
        reg_pesos = {"ERC": 2.5, "JUNTS": 1.5, "PNV": 1.0, "EH Bildu": 1.0}
    esc_reg = _dhondt(reg_pesos, POOL_REGIONALISTAS)
    # Ajuste exacto al pool
    delta = POOL_REGIONALISTAS - sum(esc_reg.values())
    if delta != 0 and reg_pesos:
        # Añade/quita en el regionalista con mayor media
        top = max(reg_pesos, key=reg_pesos.get)
        esc_reg[top] = max(0, esc_reg.get(top, 0) + delta)

    # ── Nacionales: resto de escaños ──
    restantes = TOTAL_ESCANOS - POOL_REGIONALISTAS
    nac_pesos = {p: votos[p] for p in NACIONALES if p in votos and votos[p] > 0}
    if not nac_pesos:
        nac_pesos = {"PP": 30.0, "PSOE": 28.0, "VOX": 15.0, "FA": 8.0}
    # Umbral legal del 3%: por debajo se penaliza el peso (simula el corte
    # de circunscripción sin vaciar del todo partidos como Podemos/SALF
    # que aún pueden lograr escaños en provincias grandes).
    nac_umbral = {
        p: (w if w >= UMBRAL_PCT else w * 0.35) for p, w in nac_pesos.items()
    }
    esc_nac = _dhondt(nac_umbral, restantes)
    # Si el umbral deja escaños sin repartir, reasigna con pesos sin recorte
    fallos = restantes - sum(esc_nac.values())
    if fallos > 0:
        extra = _dhondt(nac_pesos, fallos)
        for p, n in extra.items():
            esc_nac[p] = esc_nac.get(p, 0) + n

    escaños: dict[str, int] = {p: 0 for p in set(list(votos) + REGIONALISTAS + NACIONALES)}
    for p, n in esc_reg.items():
        escaños[p] = escaños.get(p, 0) + n
    for p, n in esc_nac.items():
        escaños[p] = escaños.get(p, 0) + n
    escaños = {p: n for p, n in escaños.items() if n > 0}

    total = sum(escaños.values())
    if total != TOTAL_ESCANOS:
        # Corrección final de robustez
        diff = TOTAL_ESCANOS - total
        objetivo = max(escaños, key=escaños.get) if escaños else "PP"
        escaños[objetivo] = escaños.get(objetivo, 0) + diff
        if escaños[objetivo] < 0:
            escaños[objetivo] = 0

    return {
        "escaños": escaños,
        "total": sum(escaños.values()),
        "pool_regionalistas": POOL_REGIONALISTAS,
        "umbral_pct": UMBRAL_PCT,
        "medias_usadas": votos,
    }


def estado_bloque(total: int) -> dict:
    """Estado y distancia frente a los 176 escaños."""
    dist = total - MAYORIA_ABSOLUTA
    if total >= MAYORIA_ABSOLUTA:
        estado = "Mayoría Absoluta"
        texto = f"+{dist} sobre la absoluta" if dist else "exactamente 176"
    elif total >= MIN_SIMPLE_2A_VUELTA:
        estado = "Mayoría Simple en 2ª vuelta"
        texto = f"{abs(dist)} para la absoluta"
    else:
        estado = "Insuficiente"
        texto = f"{abs(dist)} para la absoluta"
    return {
        "total": total,
        "distancia_176": dist,
        "texto_distancia": texto,
        "estado": estado,
        "alcanza_absoluta": total >= MAYORIA_ABSOLUTA,
    }


def simular_bloques(escaños: dict[str, int]) -> list[dict]:
    """Evalúa todas las combinaciones de gobierno definidas."""
    resultados = []
    for nombre, miembros in BLOQUES.items():
        total = sum(escaños.get(p, 0) for p in miembros)
        info = estado_bloque(total)
        resultados.append(
            {
                "bloque": nombre,
                "miembros": miembros,
                **info,
                "detalle": {p: escaños.get(p, 0) for p in miembros},
            }
        )
    resultados.sort(key=lambda x: x["total"], reverse=True)
    return resultados


def escaños_para_hemiciclo(escaños: dict[str, int]) -> list[tuple[str, str]]:
    """Lista de 350 (partido, color) en orden ideológico izquierda→derecha."""
    orden = []
    usados = set()
    for p in ORDEN_HEMICICLO:
        clave = p
        if p == "FA" and "SUMAR" in escaños and "FA" not in escaños:
            clave = "SUMAR"
        n = escaños.get(clave, 0) + (escaños.get(p, 0) if clave != p else 0)
        if p == "FA":
            n = escaños.get("FA", 0) + escaños.get("SUMAR", 0)
        if n <= 0:
            continue
        color = COLORES_HEMICICLO.get(p, COLORES_HEMICICLO["OTROS"])
        orden.extend([(p if p != "FA" else "FA", color)] * n)
        usados.add(p)
    # Resto (partidos no listados)
    resto = {p: n for p, n in escaños.items() if p not in usados and n > 0}
    for p, n in sorted(resto.items(), key=lambda x: -x[1]):
        orden.extend([(p, COLORES_HEMICICLO["OTROS"])] * n)
    # Ajuste a 350
    if len(orden) > TOTAL_ESCANOS:
        orden = orden[:TOTAL_ESCANOS]
    elif len(orden) < TOTAL_ESCANOS:
        orden.extend([("?", COLORES_HEMICICLO["OTROS"])] * (TOTAL_ESCANOS - len(orden)))
    return orden


def posiciones_hemiciclo(n: int = TOTAL_ESCANOS, n_filas: int = 7) -> list[tuple[float, float]]:
    """Coordenadas (x, y) de n puntos en arco semicircular de 180° (izq→der)."""
    if n_filas < 1:
        n_filas = 1
    # Distribuir asientos en filas concéntricas
    base = n // n_filas
    extra = n % n_filas
    conteos = [base + (1 if i < extra else 0) for i in range(n_filas)]
    coords: list[tuple[float, float]] = []
    for fila, cnt in enumerate(conteos):
        r = 0.55 + 0.45 * (fila + 1) / n_filas  # radio normalizado 0.55–1.0
        for i in range(cnt):
            # De izquierda (180°) a derecha (0°)
            if cnt == 1:
                ang = math.pi / 2
            else:
                ang = math.pi - (math.pi * i / (cnt - 1))
            x = r * math.cos(ang)
            y = r * math.sin(ang)
            coords.append((x, y))
    return coords


def cargar_medias(ruta: Path | None = None) -> dict[str, float]:
    if ruta is None:
        ruta = Path(__file__).resolve().parent / "data" / "encuestas_limpias.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return datos.get("medias_actual_14d") or datos.get("medias") or {}


def simular_desde_medias(medias: dict[str, float] | None = None) -> dict:
    if medias is None:
        medias = cargar_medias()
    proy = proyectar_escaños(medias)
    bloques = simular_bloques(proy["escaños"])
    return {
        **proy,
        "bloques": bloques,
        "mayoria_absoluta": MAYORIA_ABSOLUTA,
        "mejor_bloque": bloques[0] if bloques else None,
    }


if __name__ == "__main__":
    res = simular_desde_medias()
    print(f"Total escaños: {res['total']} (objeto {TOTAL_ESCANOS})")
    print("Reparto:", dict(sorted(res["escaños"].items(), key=lambda x: -x[1])))
    for b in res["bloques"]:
        print(f"  {b['bloque']}: {b['total']} -> {b['estado']} ({b['texto_distancia']})")
    coords = posiciones_hemiciclo()
    print(f"Hemiciclo puntos: {len(coords)}")
