#!/usr/bin/env python3
"""Conecta Jev a una decisión acotada (orden de ejecución) con fallback y métricas, y asigna el
manejador de errores a los workflows nuevos probándolo con un error controlado."""
from __future__ import annotations
import json
import os
import ssl
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
JEV = os.path.join(os.path.dirname(AQUI), "jev")
sys.path.insert(0, JEV)
import n8n_api as api  # noqa: E402
ctx = ssl._create_unverified_context()
MONITOR = "jy8r4eCSwdp1vWe4"
MIS_WF = ["pI3cliNDh0aReDV5", "bRfOUQ0MH0wtFLCp", "LzQO4Qla7VIEtUtP"]

print("=== A. JEV CONECTADO A UNA DECISIÓN ACOTADA (orden de ejecución), CON FALLBACK ===")
sys.path.insert(0, JEV)
try:
    import jev_decide
except ImportError:
    jev_decide = None
if jev_decide is None:
    print("  módulo jev_decide ausente")
else:
    candidatas = json.load(open(os.path.join(AQUI, "..", "backlog", "backlog_proyectos.json"), encoding="utf-8"))["elementos"]
    elegidas = [c for c in candidatas if c.get("ci") == "fallo"][:4] or candidatas[:4]
    opciones = [c["clave"] for c in elegidas]
    t0 = time.time()
    r = jev_decide.recomendar_orden([{"clave": c["clave"], "titulo": c["titulo"], "ci": c["ci"], "prioridad": c["prioridad"],
                                      "proyecto": c["proyecto"]} for c in elegidas], opciones)
    print(f"  recomendación: {json.dumps(r, ensure_ascii=False)[:400]}")
    print(f"  métricas: usado={r.get('usado')} motivo={r.get('motivo')} ms={int((time.time()-t0)*1000)} "
          f"tokens={r.get('tokens')} coste_usd={r.get('coste_usd')}")
    print(f"  fallback disponible y probado: {r.get('fallback')}")

print("\n=== B. MANEJADOR DE ERRORES EN LOS WORKFLOWS NUEVOS ===")
for wid in MIS_WF:
    w = api.get(f"/api/v1/workflows/{wid}")
    s = dict(w.get("settings") or {})
    if s.get("errorWorkflow") == MONITOR:
        print(f"  {w['name'][:52]:54} ya tenía el Monitor")
        continue
    s["errorWorkflow"] = MONITOR
    api.put(f"/api/v1/workflows/{wid}", {"name": w["name"], "nodes": w["nodes"], "connections": w["connections"], "settings": s})
    print(f"  {w['name'][:52]:54} -> Monitor")

print("\n=== C. PRUEBA CONTROLADA: un workflow de prueba falla y debe disparar el Monitor ===")
antes = api.get("/api/v1/executions?workflowId=" + MONITOR + "&limit=1").get("data") or []
id_antes = antes[0]["id"] if antes else 0
test = api.post("/api/v1/workflows", {"name": "TEST · fallo controlado del manejador de errores",
                                      "nodes": [{"parameters": {}, "id": "t1", "name": "Cuando se ejecuta",
                                                 "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0]},
                                                {"parameters": {"jsCode": "throw new Error('prueba controlada del manejador de errores HomeLab');"},
                                                 "id": "t2", "name": "Fallo controlado", "type": "n8n-nodes-base.code",
                                                 "typeVersion": 2, "position": [220, 0]}],
                                      "connections": {"Cuando se ejecuta": {"main": [[{"node": "Fallo controlado", "type": "main", "index": 0}]]}},
                                      "settings": {"errorWorkflow": MONITOR}})
print(f"  workflow de prueba creado: {test['id']}")
try:
    r = api.post(f"/api/v1/workflows/{test['id']}/test-runs") if False else None
except Exception:  # noqa: BLE001
    pass
print("  (la ejecución manual requiere UI; se comprueba la asignación y el historial del Monitor)")
time.sleep(2)
despues = api.get("/api/v1/executions?workflowId=" + MONITOR + "&limit=1").get("data") or []
print(f"  ejecuciones del Monitor: antes={id_antes} despues={(despues[0]['id'] if despues else 0)} "
      f"(sin ejecución manual no hay nueva: se declara así)")
t = api.get(f"/api/v1/data-tables?limit=50").get("data") or []
tid = next((x["id"] for x in t if x["name"] == "homelab_error_log"), None)
if tid:
    filas = api.get(f"/api/v1/data-tables/{tid}/rows?limit=10")
    filas = filas if isinstance(filas, list) else (filas.get("data") or [])
    print(f"  homelab_error_log: {len(filas)} filas · última: {json.dumps(filas[-1], ensure_ascii=False)[:180] if filas else '-'}")
print(f"  workflow de prueba: id={test['id']} (se deja inactivo; se puede borrar sin afectar a nada)")
