# Consultor Electoral España

Streamlit + scraper de Wikipedia + Gemini: **Congreso (350)**, **Senado (266)** y **Autonomías (10 CCAA)** — proyección D'Hondt, pactómetro, histórico diario y momentum.

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
| `scraper.py` | Extrae/filtra encuestas generales (sin CIS, n≥800) y autonómicas (n≥600) |
| `analizador_ia.py` | Informe + chat con Gemini |
| `pactometro.py` | D'Hondt 350 escaños, bloques, hemiciclo Congreso |
| `senado.py` | D'Hondt/mayoritario 266 escaños, diseño 134, designación 58 |
| `autonomias.py` | 10 CCAA: escaños, mayoría, umbrales, pactos, hemiciclo |
| `tracker_historico.py` | Snapshot diario (Congreso+Senado+Autonomías) + momentum |
| `iniciar_consultor.bat` | Lanzador Windows (venv + datos + Streamlit) |

## Datos

- `data/encuestas_limpias.json` — encuestas generales filtradas
- `data/encuestas_autonomicas.json` — medias por CCAA
- `data/historico_diario.json` — histórico diario (3 cámaras)
- `data/informe_ia.json` — informe del consultor

## CI

`.github/workflows/actualizar.yml` — actualización automática diaria de datos.
