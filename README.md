# Consultor Electoral España

Streamlit + scraper multi-fuente (Wikipedia ES, ElectoralLab, Votomunicipal, Demócrata, EleccionesEspeña, MapaElectoral) + Gemini: **Congreso (350)**, **Senado (266)** y **Autonomías (10 CCAA)** — proyección D'Hondt, pactómetro, histórico diario, momentum, house effects, margen de error muestral (± IC 95%) y auditoría multi-fuente con verificación IA.

## Arranque rápido

Doble clic en **`iniciar_consultor.bat`** (Escritorio → «Consultor Electoral» o dentro de esta carpeta).

```bat
iniciar_consultor.bat
```

Abre `http://localhost:8501`.

## Requisitos

- Python 3.12+
- `.env` con `GEMINI_API_KEY=...` (no se sube a Git)

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Cámaras

| Cámara | Escaños | Mayoría | Umbral |
|--------|---------|---------|--------|
| Congreso | 350 | 176 | 3% |
| Senado | 266 | 134 | mayoritario 3+1 + 58 designados |
| Autonomías | por CCAA | (n/2)+1 | 5% o 3% según comunidad |

Selector en la cabecera: **Congreso · Senado · Autonomías** (+ combo de CCAA).

## Estructura

| Archivo | Función |
|---------|---------|
| `app.py` | Interfaz Streamlit (minimal, responsive, selector de cámaras) |
| `scraper.py` | 6 fuentes multi-agregador; filtros sin CIS, n≥800; autonómicas n≥600; `moe_pp` ± IC 95%; `auditoria_fuentes` (dispersión + pares cross-source) |
| `analizador_ia.py` | Informe + chat con Gemini |
| `pactometro.py` | D'Hondt 350 escaños, bloques, hemiciclo Congreso |
| `senado.py` | D'Hondt/mayoritario 266 escaños, diseño 134, designación 58 |
| `autonomias.py` | 10 CCAA: escaños, mayoría, umbrales, pactos, hemiciclo |
| `tracker_historico.py` | Snapshot diario (Congreso+Senado+Autonomías) + momentum |
| `iniciar_consultor.bat` | Lanzador Windows (venv + datos + Streamlit) |

## Datos

- `data/encuestas_limpias.json` — encuestas generales filtradas (6 fuentes, con `moe_pp` y `auditoria_fuentes`)
- `data/encuestas_autonomicas.json` — medias por CCAA (Wikipedia + MapaElectoral)
- `data/historico_diario.json` — histórico diario (3 cámaras)
- `data/informe_ia.json` — informe del consultor (incluye verificación de aproximación)

## Fuentes

| Fuente | Uso | Licencia / notas |
|--------|-----|------------------|
| Wikipedia ES | Tablas de encuestas generales y autonómicas | CC BY-SA |
| ElectoralLab (`electorallab.com/data/encuestas.csv`) | Generales (incluye Electomanía y otras casas) | CC BY 4.0 |
| Votomunicipal (`votomunicipal.es/datos/encuestas.json`) | Generales JSON | CC BY-SA |
| Demócrata (`democrata.es/.../sondeos.csv`) | Generales CSV long (sin CIS/agregados) | CC BY-SA |
| EleccionesEspeña (`xn--eleccionesespaa-crb.com/data/general.json`) | Generales JSON | datos de encuestas |
| MapaElectoral (`mapaelectoral.es/.../encuestas_limpias.csv`) | Generales + CCAA (`ambito`) | CC BY-SA |
| Electomanía | **No se scrapea** (ToS); llega vía agregadores | — |
| CIS | Excluido por diseño anti-sesgo | — |

Actualización automática: GitHub Actions diaria (`scraper → analizador_ia → tracker → auto-commit`) y botón 🔄 en la app (ttl 1 h).

`moe_pp` = margen de error al 95% con p=0.5: `1.96·√(0.25/n)·100`.
`auditoria_fuentes` = conteos por origen, MOE medio, dispersión 14d y pares cross-source (misma encuesta en ≥2 agregadores).

## CI

`.github/workflows/actualizar.yml` — actualización automática diaria de datos.
