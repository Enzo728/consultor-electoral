import pactometro as pm

r = pm.simular_desde_medias()
assert r["total"] == 350, f"total={r['total']}"
h = pm.escaños_para_hemiciclo(r["escaños"])
assert len(h) == 350, f"hemi={len(h)}"
c = pm.posiciones_hemiciclo(350)
assert len(c) == 350, f"coords={len(c)}"
print("escaños total:", r["total"])
print("hemiciclo:", len(h), "coords:", len(c))
print("reparto:", dict(sorted(r["escaños"].items(), key=lambda x: -x[1])))
for b in r["bloques"]:
    print(f"  {b['bloque']}: {b['total']} -> {b['estado']} ({b['texto_distancia']})")

from app import construir_barra_escaños
html = construir_barra_escaños(r["escaños"])
assert "176" in html
print("barra HTML OK")

# rutas del bat
from pathlib import Path
bat = Path("iniciar_consultor.bat").read_text(encoding="utf-8", errors="replace")
for ruta in [".venv\\Scripts\\python.exe", "scraper.py", "analizador_ia.py", "app.py", "streamlit"]:
    assert ruta.replace("\\\\", "\\") in bat or ruta in bat, f"falta {ruta} en bat"
print("bat rutas OK")

lnk = Path.home() / "Desktop" / "Consultor Electoral.lnk"
# OneDrive desktop
import os
esc = os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive - Universidad de Castilla-La Mancha", "Escritorio", "Consultor Electoral.lnk")
print("lnk escritorio:", os.path.exists(esc), esc)
print("ALL CHECKS PASSED")
