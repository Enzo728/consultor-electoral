# Consultor Electoral España

Streamlit + scraper de Wikipedia + Gemini: proyección de escaños del Congreso (350), pactómetro, histórico diario y momentum.

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

## Estructura

| Archivo | Función |
|---------|---------|
| `app.py` | Interfaz Streamlit (minimal, responsive) |
| `scraper.py` | Extrae/filtra encuestas (sin CIS, n≥800) |
| `analizador_ia.py` | Informe + chat con Gemini |
| `pactometro.py` | D'Hondt 350 escaños, bloques, hemiciclo |
| `tracker_historico.py` | Snapshot diario + momentum |
| `iniciar_consultor.bat` | Lanzador Windows (venv + datos + Streamlit) |

## Datos

- `data/encuestas_limpias.json` — encuestas filtradas
- `data/historico_diario.json` — histórico diario
- `data/informe_ia.json` — informe del consultor

## CI

`.github/workflows/actualizar.yml` — actualización automática diaria de datos.
