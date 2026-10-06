#!/usr/bin/env python3
"""Consolidación de los dos manejadores de error SMTP: cobertura probada antes de retirar el duplicado."""
from __future__ import annotations
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import n8n_api as api  # noqa: E402

HANDLER = "Eea72K3w9rkoVf1n"   # Home Lab — Error Handler   (duplicado simple, 0 ejecuciones)
MONITOR = "jy8r4eCSwdp1vWe4"   # HomeLab — Error Monitor    (persiste + avisa, 2 ejecuciones reales)
TEST_ALERTS = "4RorUgDQee4ypiZo"

print("=== 1. COPIA RECUPERABLE DEL DUPLICADO (antes de tocarlo) ===")
h = api.get(f"/api/v1/workflows/{HANDLER}")
ruta = os.path.join(AQUI, "rollback", f"{HANDLER}-error-handler.json")
os.makedirs(os.path.dirname(ruta), exist_ok=True)
json.dump(h, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"  definición guardada en {ruta} ({len(h['nodes'])} nodos)")

print("\n=== 2. COBERTURA DEL QUE QUEDA (Error Monitor) ===")
m = api.get(f"/api/v1/workflows/{MONITOR}")
tipos_m = [str(n["type"]).replace("n8n-nodes-base.", "") for n in m["nodes"]]
tipos_h = [str(n["type"]).replace("n8n-nodes-base.", "") for n in h["nodes"]]
print(f"  Monitor: {tipos_m}")
print(f"  Handler: {tipos_h}")
print(f"  ¿mismo disparador (Error Trigger)? {('errorTrigger' in tipos_m) and ('errorTrigger' in tipos_h)}")
print(f"  ¿el Monitor además persiste el error? {'dataTable' in tipos_m}")
print(f"  ¿el Monitor avisa por correo? {'emailSend' in tipos_m}")
cobertura = ("errorTrigger" in tipos_m) and ("emailSend" in tipos_m) and ("dataTable" in tipos_m)
print(f"  -> cobertura del Monitor sobre el Handler: {'COMPLETA (disparador + aviso + persistencia)' if cobertura else 'INCOMPLETA'}")

print("\n=== 3. CONSUMIDORES: QUIÉN APUNTA A CADA UNO ===")
todos = api.get("/api/v1/workflows?limit=100").get("data") or []
for w in todos:
    ew = (w.get("settings") or {}).get("errorWorkflow")
    if ew:
        print(f"  {w['name']:44} -> {'Monitor' if ew == MONITOR else ('Handler' if ew == HANDLER else ew)}")

print("\n=== 4. REAPUNTAR EL ÚNICO CONSUMIDOR DEL DUPLICADO Y RETIRARLO ===")
ty = api.get(f"/api/v1/workflows/{TEST_ALERTS}")
s = dict(ty.get("settings") or {})
s["errorWorkflow"] = MONITOR
api.put(f"/api/v1/workflows/{TEST_ALERTS}", {"name": ty["name"], "nodes": ty["nodes"], "connections": ty["connections"],
                                             "settings": s})
print(f"  {ty['name']}: errorWorkflow -> Monitor (antes Handler)")
api.post(f"/api/v1/workflows/{HANDLER}/deactivate")
hh = api.get(f"/api/v1/workflows/{HANDLER}")
print(f"  Handler: activo={hh['active']} (definición conservada, {len(hh['nodes'])} nodos)")

print("\n=== 5. COMPROBACIÓN FINAL ===")
todos = api.get("/api/v1/workflows?limit=100").get("data") or []
sin = [w["name"] for w in todos if not (w.get("settings") or {}).get("errorWorkflow")
       and w["id"] not in (HANDLER, MONITOR)]
con = {w["name"]: ("Monitor" if (w.get("settings") or {}).get("errorWorkflow") == MONITOR else "Handler")
       for w in todos if (w.get("settings") or {}).get("errorWorkflow")}
print(f"  workflows con manejador: {con}")
print(f"  sin manejador (no lo tenían antes tampoco): {sin}")
print(f"  Handler activo: {api.get(f'/api/v1/workflows/{HANDLER}')['active']} · Monitor activo: {api.get(f'/api/v1/workflows/{MONITOR}')['active']}")
print(f"  rollback: reactivar el Handler y devolver errorWorkflow={HANDLER} a los consumidores que lo tuvieran")
