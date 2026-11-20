"""Consultor IA: genera el informe diario con Gemini (google-genai) a partir de encuestas_limpias.json."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ENCUESTAS_PATH = DATA_DIR / "encuestas_limpias.json"
INFORME_PATH = DATA_DIR / "informe_ia.json"

MODELO = "gemini-3.5-flash"  # gemini-2.5-flash retirado para cuentas nuevas
PARTIDOS_CLAVE = ["PP", "PSOE", "VOX", "FA", "SUMAR", "PODEMOS", "SALF"]


def get_client() -> genai.Client:
    load_dotenv(BASE_DIR / ".env")
    # genai.Client() lee GEMINI_API_KEY del entorno automáticamente
    return genai.Client()


def cargar_encuestas() -> dict:
    if not ENCUESTAS_PATH.exists():
        raise FileNotFoundError(
            f"No existe {ENCUESTAS_PATH}. Ejecuta antes: python scraper.py"
        )
    return json.loads(ENCUESTAS_PATH.read_text(encoding="utf-8"))


def resumen_para_ia(datos: dict) -> dict:
    """Compacta el JSON de encuestas en un payload apto para el prompt."""
    medias = datos.get("medias", {})
    act = datos.get("medias_actual_14d", {})
    ant = datos.get("medias_sem_anterior_14_28d", {})
    deltas = {
        p: round(act.get(p, 0) - ant.get(p, 0), 2)
        for p in set(act) | set(ant)
        if p in act and p in ant
    }

    # Serie semanal ponderada (aproximación por semana ISO)
    semanal: dict[str, dict[str, float]] = {}
    conteo_sem: dict[str, int] = {}
    for pt in datos.get("evolucion", []):
        try:
            f = datetime.fromisoformat(pt["fecha"])
        except (KeyError, ValueError):
            continue
        clave = f.isocalendar()[:2]
        sem = f"{clave[0]}-W{clave[1]:02d}"
        semanal.setdefault(sem, {})
        # media simple por semana y partido (suficiente para tendencia)
        lista = semanal[sem].setdefault(pt["partido"], [])
        if isinstance(lista, list):
            lista.append(pt["valor"])
        conteo_sem[sem] = conteo_sem.get(sem, 0) + 1

    serie = []
    for sem in sorted(semanal):
        fila = {"semana": sem}
        for p, vals in semanal[sem].items():
            if isinstance(vals, list) and vals:
                fila[p] = round(sum(vals) / len(vals), 2)
        serie.append(fila)

    recientes = []
    for e in sorted(datos.get("encuestas", []), key=lambda x: x.get("fecha_fin") or "", reverse=True)[:40]:
        votos = {k: v for k, v in (e.get("votos") or {}).items() if v is not None}
        recientes.append(
            {
                "encuestadora": e.get("fuente_nombre"),
                "fecha_fin": e.get("fecha_fin"),
                "trabajo_campo": e.get("trabajo_campo"),
                "muestra": e.get("muestra"),
                "moe_pp": e.get("moe_pp"),
                "origen": e.get("origen"),
                "votos": votos,
            }
        )

    fuentes_meta = []
    for f in datos.get("fuentes") or []:
        st = f.get("stats") or {}
        fuentes_meta.append(
            {
                "id": f.get("id"),
                "nombre": f.get("nombre"),
                "encuestas": st.get("encuestas_incluidas", st.get("encuestas")),
                "error": st.get("error"),
            }
        )

    return {
        "actualizado": datos.get("actualizado"),
        "filtros": datos.get("filtros"),
        "fuentes": fuentes_meta,
        "auditoria_fuentes": datos.get("auditoria_fuentes"),
        "medias_global": medias,
        "medias_actual_14d": act,
        "medias_sem_anterior": ant,
        "deltas_semana": deltas,
        "serie_semanal": serie[-16:],
        "encuestas_recientes": recientes,
        "house_effects_precomputados": datos.get("house_effects", [])[:10],
        "n_encuestas_incluidas": len(datos.get("encuestas", [])),
        "n_encuestas_excluidas": len(datos.get("excluidas", [])),
    }


def construir_prompt(resumen: dict) -> str:
    esquema = r"""
{
  "fecha_informe": "YYYY-MM-DD",
  "resumen_ejecutivo": "3-5 frases en español",
  "progreso_campana": {
    "situacion": "estado actual de la campaña en 4-6 frases",
    "tendencia_bloques": {
      "derecha_PP_VOX": "tendencia del bloque derecha",
      "izquierda_PSOE_FA_SUMAR_PODEMOS": "tendencia del bloque izquierda",
      "otras_fuerzas": "regionalistas, SALF y demás"
    },
    "momento_clave": "si la campaña está en recta final, meseta, volatilización..."
  },
  "puntos_inflexion": [
    {
      "semana_o_fecha": "ej. 2026-W44",
      "partido": "sigla o bloque",
      "descripcion": "qué cambió y por qué podría haber sido",
      "magnitud_pp": 0.0
    }
  ],
  "auditoria_dispersion": {
    "encuestadora_mas_desviada": "nombre",
    "house_effects": [
      {"encuestadora": "...", "partido": "...", "desviacion_pp": 0.0, "lectura": "posible house effect / alineación ideológica / muestra"}
    ],
    "alertas": ["encuesta atípica, outlier, cambio brusco sin respaldo..."],
    "nota_metodologica": "1-2 frases sobre calidad de la muestra y exclusiones (CIS fuera, n>=800)",
    "verificacion_aproximacion": {
      "coherencia_entre_fuentes": "OK | alerta — ¿las fuentes coinciden en las últimas encuestas?",
      "moe_y_dispersion": "¿la media 14d es consistente con moe_pp y la dispersión (desv_estandar) de los datos?",
      "fuentes_con_error_o_hueco": ["id de fuente con error o sin encuestas"],
      "pares_cross_source_revisados": "si hay pares con max_dif_pp alto, señalarlo; si max_dif_pp bajo, dar por buena la deduplicación",
      "confianza": "alta | media | baja",
      "justificacion_confianza": "1-2 frases basadas SOLO en los números de auditoria_fuentes y moe_pp"
    }
  },
  "markdown": "Informe completo en Markdown con encabezados ## Progreso de campaña, ## Puntos de inflexión, ## Auditoría de dispersión, ## Verificación de aproximación, ## Conclusión"
}
"""
    cabecera = (
        'Eres "Consultor Electoral España", un analista senior de encuestas. '
        "Analiza ÚNICAMENTE los datos proporcionados (no inventes cifras). "
        "En auditoria_fuentes.verificacion_aproximacion usa solo moe_pp, "
        "dispersion_14d_top, pares_cross_source y los errores de fuentes del JSON. "
        "Devuelve SOLO un objeto JSON válido con esta estructura exacta:\n"
    )
    return cabecera + esquema + "\nDATOS:\n" + json.dumps(resumen, ensure_ascii=False, indent=1)


def extraer_json(texto: str) -> dict:
    if not texto:
        raise ValueError("Respuesta vacía de Gemini")
    t = texto.strip()
    # Quitar fences ```json ... ```
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if fence:
        t = fence.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # Buscar primer { ... último }
    inicio = t.find("{")
    fin = t.rfind("}")
    if inicio >= 0 and fin > inicio:
        return json.loads(t[inicio : fin + 1])
    raise json.JSONDecodeError("No se encontró JSON en la respuesta", t, 0)


def generar_informe(client: genai.Client | None = None, datos: dict | None = None) -> dict:
    if datos is None:
        datos = cargar_encuestas()
    resumen = resumen_para_ia(datos)
    prompt = construir_prompt(resumen)

    if client is None:
        client = get_client()

    response = client.models.generate_content(
        model=MODELO,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            top_p=0.95,
            response_mime_type="application/json",
        ),
    )
    texto = response.text or ""
    informe = extraer_json(texto)
    informe.setdefault("fecha_informe", datetime.now().strftime("%Y-%m-%d"))
    informe["generado_en"] = datetime.now().isoformat(timespec="seconds")
    informe["modelo"] = MODELO
    informe["datos_referencia"] = {
        "actualizado": resumen.get("actualizado"),
        "medias_actual_14d": resumen.get("medias_actual_14d"),
        "deltas_semana": resumen.get("deltas_semana"),
        "n_encuestas": resumen.get("n_encuestas_incluidas"),
        "fuentes": resumen.get("fuentes"),
        "auditoria_fuentes": {
            k: resumen.get("auditoria_fuentes", {}).get(k)
            for k in (
                "por_fuente", "moe_medio_pp", "n_pares_cross_source",
                "cross_source_max_dif_pp", "house_effect_medio_pp",
            )
        },
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INFORME_PATH.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ia] Informe guardado en {INFORME_PATH}")
    return informe


def preguntar(pregunta: str, historial: list[dict] | None = None,
              datos: dict | None = None, client: genai.Client | None = None) -> str:
    """Chat en lenguaje natural sobre los datos cargados."""
    if datos is None:
        datos = cargar_encuestas()
    resumen = resumen_para_ia(datos)
    contexto = (
        "Eres el Consultor Electoral España. Responde en español, con precisión y "
        "sin inventar datos. Usa el siguiente contexto JSON:\n"
        + json.dumps(resumen, ensure_ascii=False)[:12000]
    )
    contents: list[types.Content | str] = [contexto]
    for msg in (historial or [])[-10:]:
        rol = "user" if msg.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg.get("content", ""))]))
    contents.append(types.Content(role="user", parts=[types.Part(text=pregunta)]))

    if client is None:
        client = get_client()
    response = client.models.generate_content(
        model=MODELO,
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.5, top_p=0.95),
    )
    return (response.text or "").strip()


def main() -> int:
    print("[ia] Generando informe con Gemini...")
    informe = generar_informe()
    print(f"[ia] OK — {informe.get('fecha_informe')} | "
          f"inflexiones={len(informe.get('puntos_inflexion', []))} | "
          f"alertas={len(informe.get('auditoria_dispersion', {}).get('alertas', []))}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[ia] Error: {exc}", file=sys.stderr)
        sys.exit(1)
