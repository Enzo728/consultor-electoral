"""Scraper de encuestas electorales (Wikipedia ES) con filtros anti-sesgo y medias ponderadas."""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL_WIKI = (
    "https://es.wikipedia.org/wiki/"
    "Encuestas_de_opini%C3%B3n_para_las_elecciones_generales_de_Espa%C3%B1a_de_2026"
)
DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_PATH = DATA_DIR / "encuestas_limpias.json"
OUT_AUT_PATH = DATA_DIR / "encuestas_autonomicas.json"

# Páginas de Wikipedia con tablas de encuestas autonómicas (títulos reales).
# Se prueban en orden; se ignora lo que falle (404/429).
PAGINAS_AUTONOMICAS: dict[str, list[str]] = {
    "madrid": [
        "Elecciones a la Asamblea de Madrid de 2027",
        "Elecciones a la Asamblea de Madrid de 2023",
    ],
    "cataluna": ["Elecciones al Parlamento de Cataluña de 2028"],
    "andalucia": ["Elecciones al Parlamento de Andalucía de 2026"],
    "cvalenciana": [
        "Elecciones a las Cortes Valencianas de 2027",
        "Elecciones a las Cortes Valencianas de 2023",
    ],
    "galicia": [
        "Elecciones al Parlamento de Galicia de 2025",
        "Elecciones al Parlamento de Galicia de 2024",
    ],
    "paisvasco": ["Elecciones al Parlamento Vasco de 2024"],
    "cyl": ["Elecciones a las Cortes de Castilla y León de 2026"],
    "clm": [
        "Elecciones a las Cortes de Castilla-La Mancha de 2027",
        "Elecciones a las Cortes de Castilla-La Mancha de 2023",
    ],
    "aragon": ["Elecciones a las Cortes de Aragón de 2026"],
    "extremadura": ["Elecciones a la Asamblea de Extremadura de 2025"],
}

MESES = {
    "ene": 1, "enero": 1, "jan": 1,
    "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4, "apr": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "junio": 6,
    "jul": 7, "julio": 7,
    "ago": 8, "agosto": 8, "aug": 8,
    "sep": 9, "sept": 9, "setiembre": 9, "septiembre": 9,
    "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12, "dec": 12,
}

# Exclusión explícita anti-sesgo
EXCLUIR_ORGANISMOS = ("cis", "centro de investigaciones sociologicas", "centro de investigaciones sociológicas")

MUESTRA_MINIMA = 800
MUESTRA_MINIMA_AUT = 600
# Vida media de la ponderación temporal: 7 días
LAMBDA_DIAS = math.log(2) / 7.0

PARTIDOS_PRINCIPALES = ["PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF"]

COLORES = {
    "PP": "#1E4B8F",
    "PSOE": "#FF0000",
    "VOX": "#63BE21",
    "FA": "#6D28D9",
    "SUMAR": "#E51C55",
    "PODEMOS": "#9370DB",
    "SALF": "#111827",
    "ERC": "#FFB32E",
    "JUNTS": "#20C0C2",
    "EH BILDU": "#00D0B6",
    "PNV": "#008000",
    "BNG": "#ADCFEF",
    "CCA": "#FFD700",
    "AA": "#45B37A",
    "UPN": "#0055A5",
    "AC": "#F7941D",
    "C-FV": "#E65F00",
}


def norm_partido(nombre: str) -> str:
    """Normaliza el nombre del partido para claves/etiquetas."""
    n = (nombre or "").strip()
    if not n:
        return n
    equivalencias = {
        "vox": "VOX",
        "pp": "PP",
        "ppc": "PP",
        "psoe": "PSOE",
        "pse": "PSE",
        "pse-ee": "PSE",
        "pse ee": "PSE",
        "psc": "PSC",
        "fa": "FA",
        "frente amplio": "FA",
        "sumar": "SUMAR",
        "podemos": "PODEMOS",
        "salf": "SALF",
        "se acabó la fiesta": "SALF",
        "se acabo la fiesta": "SALF",
        "derecha": None,
        "izquierda": None,
        "erc": "ERC",
        "junts": "JUNTS",
        "junts": "JUNTS",
        "eh bildu": "EH Bildu",
        "ehbildu": "EH Bildu",
        "eaj-pnv": "PNV",
        "eaj pnv": "PNV",
        "pnv": "PNV",
        "bng": "BNG",
        "cca": "CCa",
        "cc": "CCa",
        "aa": "AA",
        "adelante andalucía": "AA",
        "adelante andalucia": "AA",
        "upn": "UPN",
        "ac": "AC",
        "c-fv": "C-FV",
        "compromís-front valencià": "C-FV",
        "compromis-front valencia": "C-FV",
        "pora": "POR A",
        "por a": "POR A",
        "por andalucía": "POR A",
        "por andalucia": "POR A",
        "cs": "Cs",
        "ciudadanos": "Cs",
        "más madrid": "Más Madrid",
        "mas madrid": "Más Madrid",
        "compromís": "Compromís",
        "compromis": "Compromís",
        "cha": "CHA",
        "par": "PAR",
        "upe": "UpE",
        "jxe": "JxE",
        "hal dugu": "Ahal Dugu",
        "ahal dugu": "Ahal Dugu",
        "elkarrekin": "PODEMOS",
        "elkarrekin podemos": "PODEMOS",
        "smr": "OTROS",
        "otros": "OTROS",
        "ns/nr": None,
        "diferencia": None,
        "ventaja": None,
        "dif.": None,
        "dif": None,
        "part.": None,
        "participación": None,
        "participacion": None,
        # Nombres largos / siglas en catalán, vasco, etc.
        "partido de los socialistas de cataluña": "PSC",
        "psc": "PSC",
        "junts per catalunya": "JUNTS",
        "jxcat": "JUNTS",
        "esquerra republicana de catalunya": "ERC",
        "partido popular de cataluña": "PP",
        "ppc": "PP",
        "comuns sumar": "FA",
        "comuns": "FA",
        "candidatura de unidad popular": "OTROS",
        "aliança catalana": "OTROS",
        "alliança catalana": "OTROS",
        "alianza catalana": "OTROS",
        "podem catalunya": "PODEMOS",
        "se acabó la fiesta": "SALF",
        "se acabo la fiesta": "SALF",
        "partido nacionalista vasco": "PNV",
        "euskal herria bildu": "EH Bildu",
        "partido socialista de euskadi-euskadiko ezkerra": "PSE",
        "pse-ee": "PSE",
        "sumar euskadi": "FA",
        "partido popular del país vasco": "PP",
        "partido popular del pais vasco": "PP",
        "vox (partido político)": "VOX",
        "vox (partido politico)": "VOX",
        "ciudadanos (españa)": "Cs",
        "ciudadanos (espana)": "Cs",
        "juanma moreno": "PP",
        "maría jesús montero": "PSOE",
        "maria jesus montero": "PSOE",
        "manuel gavira": "VOX",
        "inmaculada nieto": "POR A",
        "antonio mälllo": "POR A",
        "antonio mello": "POR A",
        "josé ignacio garcía sánchez": "AA",
        "jose ignacio garcia sanchez": "AA",
        "adrián yacar lópez": "SALF",
        "adrian yacar lopez": "SALF",
        "por andalucía": "POR A",
        "por andalucia": "POR A",
    }
    key = n.lower().strip()
    if key in equivalencias:
        mapped = equivalencias[key]
        return mapped if mapped is not None else n
    # quitar prefijo de candidato: "Moreno PP" → "PP"
    m = re.search(r"\b(PP|PSOE|VOX|PODEMOS|SALF|ERC|JUNTS|PNV|BNG|CCa|AA|UPN|Cs|PSC|PSE)\b", n, re.I)
    if m:
        return m.group(1).upper() if m.group(1).upper() in ("PP", "PSOE", "VOX", "PODEMOS", "SALF", "ERC", "JUNTS", "PNV", "BNG", "UPN", "CS", "PSC", "PSE") else m.group(1)
    return n.upper() if len(n) <= 5 else n


def color_partido(nombre: str) -> str:
    n = norm_partido(nombre)
    if n in COLORES:
        return COLORES[n]
    paleta = [
        "#0284C7", "#F59E0B", "#10B981", "#8B5CF6", "#EC4899",
        "#14B8A6", "#F97316", "#64748B", "#84CC16", "#EF4444",
    ]
    idx = sum(ord(c) for c in n) % len(paleta)
    return paleta[idx]


def fetch_html(url: str) -> str:
    headers = {"User-Agent": "ConsultorElectoralEspana/1.0 (proyecto educativo local; Python requests)"}
    resp = requests.get(url, headers=headers, timeout=45)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def clean_text(el) -> str:
    if el is None:
        return ""
    # Eliminar superíndices de referencias [n]
    for sup in el.find_all("sup"):
        sup.decompose()
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def extract_pct(cell) -> float | None:
    """Extrae el porcentaje de una celda tipo '28.5 113/119', '–', '?', '? 10'."""
    if cell is None:
        return None
    txt = clean_text(cell)
    if not txt or txt in {"–", "-", "—", "?", "n/a", "N/A"}:
        return None
    if txt.startswith("?"):
        return None
    m = re.search(r"(\d{1,2}(?:[.,]\d+)?)", txt)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    if not 0 <= val <= 100:
        return None
    return val


def parse_muestra(txt: str) -> int | None:
    if not txt:
        return None
    t = txt.strip()
    if t in {"?", "-", "–", ""}:
        return None
    m = re.search(r"(\d[\d.,\s]*)", t)
    if not m:
        return None
    digits = re.sub(r"[^\d]", "", m.group(1))
    if not digits:
        return None
    return int(digits)


def _mes(token: str) -> int | None:
    return MESES.get(token.lower().strip(".,"))


def parse_fecha_campo(txt: str, anio_defecto: int) -> tuple[date | None, date | None]:
    """Parsea rangos de trabajo de campo en español.

    Acepciones: '26 Oct–9 Nov', '4–6 Nov', '1–6 Sep', '8-22 Oct',
    '2–4 Nov 2026', '25 Oct', '1 Sep–8 Nov', '30 Dic–2 Ene' (cambio de año),
    '21 de abril de 2024', '1-9 Sep 2026', '29 Abr-6 May 2026'.
    """
    if not txt:
        return None, None
    t = re.sub(r"\s+", " ", txt.strip())
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    # Quitar 'de' en fechas largas: '21 de abril de 2024' → '21 abril 2024'
    t = re.sub(r"\bde\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()

    # Rango día-mes a día-mes: '26 Oct - 9 Nov [2026]'
    pat_rango = re.match(
        r"^(\d{1,2})\s+([A-Za-záéíóúÁÉÍÓÚ]+)\s*(\d{4})?\s*-\s*(\d{1,2})\s+"
        r"([A-Za-záéíóúÁÉÍÓÚ]+)\s*(\d{4})?$",
        t,
    )
    if pat_rango:
        d1, m1, y1, d2, m2, y2 = pat_rango.groups()
        mes1, mes2 = _mes(m1), _mes(m2)
        if mes1 and mes2:
            anio1 = int(y1) if y1 else anio_defecto
            anio2 = int(y2) if y2 else anio1
            try:
                f1 = date(anio1, mes1, int(d1))
                f2 = date(anio2, mes2, int(d2))
            except ValueError:
                return None, None
            if f2 < f1:
                try:
                    f2 = date(f2.year + 1, f2.month, f2.day)
                except ValueError:
                    return f1, f1
            return f1, f2

    # Rango de días en el mismo mes: '4-6 Nov', '1-6 Sep [2026]'
    pat_dias = re.match(
        r"^(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-záéíóúÁÉÍÓÚ]+)\s*(\d{4})?$",
        t,
    )
    if pat_dias:
        d1, d2, m1, y1 = pat_dias.groups()
        mes = _mes(m1)
        if mes:
            anio = int(y1) if y1 else anio_defecto
            try:
                f1 = date(anio, mes, int(d1))
                f2 = date(anio, mes, int(d2))
            except ValueError:
                return None, None
            if f2 < f1:
                return None, None
            return f1, f2

    # Fecha única: '25 Oct' o '25 Oct 2026' o '21 abril 2024'
    pat_unica = re.match(
        r"^(\d{1,2})\s+([A-Za-záéíóúÁÉÍÓÚ]+)\s*(\d{4})?$",
        t,
    )
    if pat_unica:
        d, m, y = pat_unica.groups()
        mes = _mes(m)
        if mes:
            anio = int(y) if y else anio_defecto
            try:
                f = date(anio, mes, int(d))
                return f, f
            except ValueError:
                return None, None

    # Fecha ISO: '2024-04-21'
    pat_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
    if pat_iso:
        try:
            f = date(int(pat_iso.group(1)), int(pat_iso.group(2)), int(pat_iso.group(3)))
            return f, f
        except ValueError:
            return None, None

    return None, None


def header_partidos(table) -> list[str] | None:
    """Devuelve lista de nombres de partido (columnas de votos).

    Compatible con dos formatos:
    - Generales: Encuestadora | Trabajo de campo | Muestra | % Voto | partidos… | Ventaja
    - Autonómicas: Encuestadora | Fecha | Muestra | partidos… | Diferencia/Ventaja
    """
    row = table.find("tr")
    if not row:
        return None
    ths = row.find_all("th")
    if not ths:
        # algunas tablas usan td en la primera fila
        ths = row.find_all("td")
    texts = [clean_text(th) for th in ths]
    joined = " ".join(texts).lower()
    if "encuestadora" not in joined and "encuestadora/medio" not in joined:
        return None

    # Columnas de metadatos (las 3 primeras típicamente)
    # Buscar inicio de partidos: tras Muestra/Fecha
    inicio = None
    for i, t in enumerate(texts):
        tl = t.lower()
        if tl in ("muestra", "n", "sample") or "muestra" in tl:
            inicio = i + 1
            break
    if inicio is None:
        # fallback: tras la 3ª columna
        inicio = 3

    # Fin: columna de ventaja/diferencia
    fin = len(texts)
    for i in range(inicio, len(texts)):
        tl = texts[i].lower()
        if tl in ("ventaja", "vent.", "diferencia", "dif.", "dif", "mayoría", "mayoria"):
            fin = i
            break

    partidos: list[str] = []
    for th, txt in zip(ths[inicio:fin], texts[inicio:fin]):
        # saltar % Voto si aparece intercalado
        if txt.startswith("%") or txt in ("Voto", "% Voto", "Part.", "Participación", ""):
            # intentar nombre desde img/a
            nombre = _nombre_partido_th(th, txt)
            if nombre and nombre not in ("", "???") and not nombre.startswith("%"):
                # solo si parece partido (no metadato)
                if nombre.lower() not in ("part.", "participación", "voto"):
                    partidos.append(nombre)
            continue
        nombre = _nombre_partido_th(th, txt)
        partidos.append(nombre)

    if not partidos:
        return None
    norms = {norm_partido(p) for p in partidos}
    # Tablas de agregados por bloque (Derecha/Izquierda) — no sirven
    if norms <= {"Derecha", "Izquierda"}:
        return None
    # Debe haber al menos un partido conocido o varios nombres plausibles
    conocidos = {"PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF", "ERC", "JUNTS",
                 "PNV", "BNG", "CCa", "AA", "UPN", "PSC", "PSE", "EAJ-PNV", "EH Bildu"}
    if not (norms & conocidos) and len(partidos) < 3:
        return None
    # Rechazar si solo hay metadatos residual
    if all(p.lower() in ("diferencia", "ventaja", "dif.", "dif", "otros", "ns/nr") for p in partidos):
        return None
    return partidos


def _nombre_partido_th(th, txt: str) -> str:
    img = th.find("img")
    if img:
        for attr in ("alt", "title"):
            v = (img.get(attr) or "").strip()
            if v and v.lower() not in {"", "none"}:
                return v
    a = th.find("a")
    if a and a.get("title"):
        title = a["title"].strip()
        if title and "wiki" not in title.lower():
            return title
    # data-mw caption
    span = th.find("span", attrs={"typeof": "mw:File"})
    if span and span.get("data-mw"):
        m = re.search(r'"caption"\s*:\s*"([^"]+)"', span.get("data-mw") or "")
        if m:
            return m.group(1)
    if txt and txt not in {"Ventaja"}:
        return txt
    return txt or "???"


def es_cis(texto: str) -> bool:
    t = (texto or "").lower()
    return any(org in t for org in EXCLUIR_ORGANISMOS)


def parse_tabla(table, anio_defecto: int) -> list[dict]:
    partidos = header_partidos(table)
    if not partidos:
        return []
    filas: list[dict] = []
    for tr in table.find_all("tr")[1:]:
        celdas = tr.find_all(["td", "th"])
        if len(celdas) < 4:
            continue
        # Saltar filas de cabecera residuales
        if all(c.name == "th" for c in celdas):
            continue

        nombre_raw = clean_text(celdas[0])
        if not nombre_raw or "Encuestadora" in nombre_raw:
            continue
        # Fila de resultados electorales (sin encuestadora real)
        if nombre_raw.lower().startswith(("resultados", "elecciones", "sondeo anterior")):
            continue

        fecha_raw = clean_text(celdas[1]) if len(celdas) > 1 else ""
        muestra_raw = clean_text(celdas[2]) if len(celdas) > 2 else ""

        # Detectar si hay columna '% Voto' (formato general) o no (autonómico)
        # General: [enc, fecha, muestra, %voto, ...partidos]
        # Autonómico: [enc, fecha, muestra, ...partidos]
        tiene_pct_voto = False
        if len(celdas) > 3:
            c3 = clean_text(celdas[3])
            if c3.startswith("%") or c3 in ("Voto", "% Voto"):
                tiene_pct_voto = True
            # también si la 4ª celda parece no-numérica y partidos empiezan en 4
            # (autonómico: PP/PSOE en celdas[3])
            elif c3 and not re.match(r"^[\d.,?\-–—\s%/]*$", c3) and not c3.startswith("?"):
                # podría ser nombre de partido → autonómico
                if norm_partido(c3) and len(c3) <= 30:
                    tiene_pct_voto = False

        votos_celdas = celdas[4:] if tiene_pct_voto else celdas[3:]

        votos: dict[str, float | None] = {}
        cursor = 0
        for cell in votos_celdas:
            colspan = int(cell.get("colspan", 1) or 1)
            valor = extract_pct(cell)
            for k in range(colspan):
                if cursor < len(partidos):
                    nombre_p = norm_partido(partidos[cursor])
                    # Solo la primera columna del colspan recibe el valor
                    votos[nombre_p] = valor if k == 0 else None
                cursor += 1
            if cursor >= len(partidos):
                break

        # Rellenar partidos no presentes
        for p in partidos:
            np_ = norm_partido(p)
            votos.setdefault(np_, None)

        f_ini, f_fin = parse_fecha_campo(fecha_raw, anio_defecto)
        muestra = parse_muestra(muestra_raw)

        # Separar encuestadora / comisionista
        if "/" in nombre_raw:
            enc, com = [x.strip() for x in nombre_raw.split("/", 1)]
        else:
            enc, com = nombre_raw.strip(), ""

        # Rechazar filas sin fecha válida o sin votos
        if not f_fin:
            continue
        if all(v is None for v in votos.values()):
            continue

        filas.append(
            {
                "encuestadora": enc,
                "comisionista": com,
                "fuente_nombre": nombre_raw,
                "trabajo_campo": fecha_raw,
                "fecha_inicio": f_ini.isoformat() if f_ini else None,
                "fecha_fin": f_fin.isoformat() if f_fin else None,
                "muestra": muestra,
                "muestra_raw": muestra_raw,
                "votos": votos,
            }
        )
    return filas


def anio_de_seccion(table) -> int | None:
    """Busca el encabezado h4/h3 anterior a la tabla con un año."""
    node = table
    while node is not None:
        prev = node.find_previous(["h4", "h3", "h2"])
        if prev is None:
            return None
        m = re.search(r"\b(20\d{2})\b", prev.get_text(" ", strip=True))
        if m:
            return int(m.group(1))
        node = prev
    return None


def extraer_encuestas(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    todas: list[dict] = []
    for table in soup.find_all("table", class_="wikitable"):
        anio = anio_de_seccion(table) or date.today().year
        filas = parse_tabla(table, anio)
        todas.extend(filas)
    return todas


def aplicar_filtros(encuestas: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """Excluye CIS y muestras < 800. Devuelve (incluidas, excluidas, stats)."""
    incluidas: list[dict] = []
    excluidas: list[dict] = []
    stats = {"total": len(encuestas), "excluidas_cis": 0, "excluidas_muestra": 0,
             "excluidas_fecha": 0, "excluidas_otra": 0}

    for e in encuestas:
        nombre = e.get("fuente_nombre", "")
        motivo = None
        if es_cis(nombre) or es_cis(e.get("encuestadora", "")) or es_cis(e.get("comisionista", "")):
            motivo = "cis"
            stats["excluidas_cis"] += 1
        elif e.get("muestra") is None:
            motivo = "muestra_desconocida"
            stats["excluidas_otra"] += 1
        elif e["muestra"] < MUESTRA_MINIMA:
            motivo = f"muestra_<_{MUESTRA_MINIMA}"
            stats["excluidas_muestra"] += 1
        elif not e.get("fecha_fin"):
            motivo = "sin_fecha"
            stats["excluidas_fecha"] += 1

        if motivo:
            excluidas.append(
                {
                    "encuestadora": e.get("fuente_nombre"),
                    "trabajo_campo": e.get("trabajo_campo"),
                    "muestra": e.get("muestra"),
                    "motivo": motivo,
                }
            )
        else:
            incluidas.append(e)

    return incluidas, excluidas, stats


def peso_encuesta(e: dict, ref: date) -> float:
    """Peso exponencial por recencia * raíz cuadrada de la muestra."""
    f = date.fromisoformat(e["fecha_fin"])
    dias = max((ref - f).days, 0)
    muestra = e.get("muestra") or MUESTRA_MINIMA
    return math.exp(-LAMBDA_DIAS * dias) * math.sqrt(muestra)


def medias_ponderadas(encuestas: list[dict], ref: date,
                      filtro_ventana: tuple[int, int] | None = None) -> dict[str, float]:
    """Media ponderada. filtro_ventana = (min_dias_ago, max_dias_ago] opcional."""
    num: dict[str, float] = {}
    den: dict[str, float] = {}
    for e in encuestas:
        f = date.fromisoformat(e["fecha_fin"])
        dias = (ref - f).days
        if filtro_ventana is not None:
            lo, hi = filtro_ventana
            if not (lo < dias <= hi):
                continue
        w = peso_encuesta(e, ref)
        for p, v in e["votos"].items():
            if v is None:
                continue
            num[p] = num.get(p, 0.0) + w * v
            den[p] = den.get(p, 0.0) + w
    return {p: round(num[p] / den[p], 2) for p in num if den.get(p, 0) > 0}


def construir_evolucion(encuestas: list[dict]) -> list[dict]:
    puntos = []
    for e in encuestas:
        for p, v in e["votos"].items():
            if v is None:
                continue
            puntos.append(
                {
                    "fecha": e["fecha_fin"],
                    "partido": p,
                    "valor": v,
                    "muestra": e["muestra"],
                    "encuestadora": e.get("fuente_nombre", ""),
                }
            )
    puntos.sort(key=lambda x: (x["fecha"], x["partido"]))
    return puntos


def house_effects(encuestas: list[dict], ref: date, dias: int = 45,
                  min_encuestas: int = 2) -> list[dict]:
    """Desviación media de cada encuestadora frente al consenso (ventana reciente)."""
    recientes = [
        e for e in encuestas
        if (ref - date.fromisoformat(e["fecha_fin"])).days <= dias
    ]
    if not recientes:
        return []
    consenso = medias_ponderadas(recientes, ref)
    por_casa: dict[str, list[dict]] = {}
    for e in recientes:
        por_casa.setdefault(e["encuestadora"], []).append(e)

    resultados = []
    for casa, polls in por_casa.items():
        if len(polls) < min_encuestas:
            continue
        meds = medias_ponderadas(polls, ref)
        desv = {
            p: round(meds[p] - consenso[p], 2)
            for p in meds
            if p in consenso and abs(meds[p] - consenso[p]) >= 0.3
        }
        if not desv:
            continue
        max_partido = max(desv, key=lambda k: abs(desv[k]))
        resultados.append(
            {
                "encuestadora": casa,
                "n_encuestas": len(polls),
                "desviaciones_pp": desv,
                "desviacion_max": {"partido": max_partido, "pp": desv[max_partido]},
            }
        )
    resultados.sort(key=lambda x: abs(x["desviacion_max"]["pp"]), reverse=True)
    return resultados


def _url_wiki_titulo(titulo: str) -> str:
    enc = requests.utils.quote(titulo.replace(" ", "_"), safe="")
    return f"https://es.wikipedia.org/wiki/{enc}"


def scrappear_autonomicas() -> dict:
    """Descarga tablas de encuestas de las páginas autonómicas configuradas.

    Devuelve:
    {
      "actualizado": iso,
      "medias": {cid: {partido: media_ponderada_14d}},
      "encuestas": {cid: [filas]},
      "stats": {cid: {incluidas, excluidas, fuente}},
    }
    """
    from datetime import date as _date

    hoy = _date.today()
    medias_out: dict[str, dict[str, float]] = {}
    enc_out: dict[str, list[dict]] = {}
    stats_out: dict[str, dict] = {}

    for cid, titulos in PAGINAS_AUTONOMICAS.items():
        html = None
        fuente = None
        for t in titulos:
            try:
                url = _url_wiki_titulo(t)
                html = fetch_html(url)
                fuente = url
                break
            except requests.RequestException:
                continue
        if not html:
            stats_out[cid] = {"incluidas": 0, "excluidas": 0, "fuente": None, "error": "sin_pagina"}
            continue
        try:
            crudas = extraer_encuestas(html)
        except Exception as exc:  # noqa: BLE001
            stats_out[cid] = {"incluidas": 0, "excluidas": 0, "fuente": fuente, "error": str(exc)[:120]}
            continue

        # Filtro autonómico: sin CIS, n≥600
        incluidas: list[dict] = []
        n_cis = n_muestra = n_otra = 0
        for e in crudas:
            nombre = e.get("fuente_nombre", "")
            if es_cis(nombre) or es_cis(e.get("encuestadora", "")):
                n_cis += 1
                continue
            m = e.get("muestra")
            if m is None:
                n_otra += 1
                continue
            if m < MUESTRA_MINIMA_AUT:
                n_muestra += 1
                continue
            if not e.get("fecha_fin"):
                n_otra += 1
                continue
            incluidas.append(e)

        # Dedup
        vistos = set()
        unicas = []
        for e in incluidas:
            clave = (e["fuente_nombre"], e["trabajo_campo"], e["muestra"], e["fecha_fin"])
            if clave in vistos:
                continue
            vistos.add(clave)
            unicas.append(e)
        incluidas = unicas

        if incluidas:
            meds = medias_ponderadas(incluidas, hoy, filtro_ventana=(0, 14))
            if not meds:
                meds = medias_ponderadas(incluidas, hoy, filtro_ventana=(0, 90))
            if not meds:
                meds = medias_ponderadas(incluidas, hoy)
            # Limpiar claves de candidatos / NS-NR / metadatos
            meds = {
                k: v for k, v in meds.items()
                if k and k.upper() not in (
                    "NS/NR", "NS/NR", "OTROS", "DIFERENCIA", "VENTAJA", "DIF.", "DIF",
                    "PART.", "PARTICIPACIÓN", "VOTO",
                )
                and not k.startswith("%")
                and len(k) <= 30
            }
        else:
            meds = {}

        medias_out[cid] = meds
        enc_out[cid] = incluidas
        stats_out[cid] = {
            "incluidas": len(incluidas),
            "excluidas_cis": n_cis,
            "excluidas_muestra": n_muestra,
            "excluidas_otra": n_otra,
            "fuente": fuente,
        }
        print(f"[scraper-aut] {cid}: {len(incluidas)} encuestas · {len(meds)} partidos")

    payload = {
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "filtros": {
            "excluir_cis": True,
            "muestra_minima": MUESTRA_MINIMA_AUT,
            "lambda_ponderacion": round(LAMBDA_DIAS, 5),
        },
        "medias": medias_out,
        "encuestas": enc_out,
        "stats": stats_out,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_AUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scraper-aut] Guardado en {OUT_AUT_PATH}")
    return payload


def main() -> int:
    print(f"[scraper] Descargando {URL_WIKI} ...")
    html = fetch_html(URL_WIKI)
    crudas = extraer_encuestas(html)
    print(f"[scraper] Filas extraídas: {len(crudas)}")

    incluidas, excluidas, stats = aplicar_filtros(crudas)
    # Deduplicar por (fuente_nombre, trabajo_campo, muestra)
    vistos = set()
    unicas = []
    for e in incluidas:
        clave = (e["fuente_nombre"], e["trabajo_campo"], e["muestra"], e["fecha_fin"])
        if clave in vistos:
            continue
        vistos.add(clave)
        unicas.append(e)
    incluidas = unicas
    print(f"[scraper] Incluidas: {len(incluidas)} | Excluidas: {len(excluidas)} ({stats})")

    hoy = date.today()
    medias_global = medias_ponderadas(incluidas, hoy)
    medias_actual = medias_ponderadas(incluidas, hoy, filtro_ventana=(0, 14))
    medias_sem_ant = medias_ponderadas(incluidas, hoy, filtro_ventana=(14, 28))
    evolucion = construir_evolucion(incluidas)
    he = house_effects(incluidas, hoy)

    partidos_ord = sorted(
        {p for e in incluidas for p, v in e["votos"].items() if v is not None},
        key=lambda p: (p not in PARTIDOS_PRINCIPALES, PARTIDOS_PRINCIPALES.index(p)
                       if p in PARTIDOS_PRINCIPALES else 99, p),
    )

    payload = {
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "fuente": URL_WIKI,
        "filtros": {
            "excluir_cis": True,
            "muestra_minima": MUESTRA_MINIMA,
            "lambda_ponderacion": round(LAMBDA_DIAS, 5),
            "notas": (
                "Media ponderada = exp(-lambda*dias) * sqrt(muestra). "
                "Se excluyen CIS y muestras < 800."
            ),
            **stats,
            "total_excluidas": len(excluidas),
            "total_incluidas": len(incluidas),
        },
        "partidos": partidos_ord,
        "colores": {p: color_partido(p) for p in partidos_ord},
        "encuestas": incluidas,
        "excluidas": excluidas,
        "medias": medias_global,
        "medias_actual_14d": medias_actual,
        "medias_sem_anterior_14_28d": medias_sem_ant,
        "house_effects": he,
        "evolucion": evolucion,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scraper] Guardado en {OUT_PATH}")
    top = sorted(medias_actual.items(), key=lambda x: -x[1])[:6]
    print(f"[scraper] Medias (14d): {top}")

    # Autonómicas (mejor esfuerzo; no bloquea si fallan todas)
    try:
        scrappear_autonomicas()
    except Exception as exc:  # noqa: BLE001
        print(f"[scraper-aut] Aviso: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.RequestException as exc:
        print(f"[scraper] Error de red: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[scraper] Error: {exc}", file=sys.stderr)
        raise
