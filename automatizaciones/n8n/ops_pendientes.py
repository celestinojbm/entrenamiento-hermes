#!/usr/bin/env python3
"""Pendientes operativos: prueba controlada del manejador de errores y resumen sin el tope de 50 filas."""
from __future__ import annotations
import json
import os
import ssl
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import n8n_api as api  # noqa: E402
ctx = ssl._create_unverified_context()
MONITOR = "jy8r4eCSwdp1vWe4"
RESUMEN = "LzQO4Qla7VIEtUtP"

print("=== A. PRUEBA CONTROLADA DEL MANEJADOR DE ERRORES ===")
antes_mon = (api.get(f"/api/v1/executions?workflowId={MONITOR}&limit=1").get("data") or [{}])[0].get("id", 0)
t = api.get("/api/v1/data-tables?limit=50").get("data") or []
tid = next((x["id"] for x in t if x["name"] == "homelab_error_log"), None)
filas_antes = api.get(f"/api/v1/data-tables/{tid}/rows?limit=50")
filas_antes = filas_antes if isinstance(filas_antes, list) else (filas_antes.get("data") or [])
print(f"  error_log antes: {len(filas_antes)} filas · ejecuciones del Monitor antes: {antes_mon}")
test = api.post("/api/v1/workflows", {"name": "TEST · fallo controlado (borrar)",
    "nodes": [{"parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 1}]}}, "id": "tt1",
               "name": "Cada minuto (prueba)", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0]},
              {"parameters": {"jsCode": "throw new Error('prueba controlada del manejador de errores HomeLab');"}, "id": "tt2",
               "name": "Fallo controlado", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [220, 0]}],
    "connections": {"Cada minuto (prueba)": {"main": [[{"node": "Fallo controlado", "type": "main", "index": 0}]]}},
    "settings": {"errorWorkflow": MONITOR}})
print(f"  workflow de prueba: {test['id']} (errorWorkflow=Monitor)")
api.post(f"/api/v1/workflows/{test['id']}/activate")
print("  activado; esperando a que falle y dispare el Monitor...")
time.sleep(75)
ex = api.get(f"/api/v1/executions?workflowId={MONITOR}&limit=2").get("data") or []
filas_desp = api.get(f"/api/v1/data-tables/{tid}/rows?limit=50")
filas_desp = filas_desp if isinstance(filas_desp, list) else (filas_desp.get("data") or [])
print(f"  Monitor: {[(e['id'], e['status'], e['mode'], e['startedAt'][11:19]) for e in ex[:2]]}")
print(f"  error_log despues: {len(filas_desp)} filas (+{len(filas_desp) - len(filas_antes)})")
if len(filas_desp) > len(filas_antes):
    print(f"  última entrada: {json.dumps(filas_desp[-1], ensure_ascii=False)[:230]}")
api.post(f"/api/v1/workflows/{test['id']}/deactivate")
print(f"  workflow de prueba desactivado ({api.get(f'/api/v1/workflows/{test[chr(39)+chr(39)] if False else test[chr(105)+chr(100)]}')['active']})")

print("\n=== B. RESUMEN DIARIO SIN EL TOPE DE 50 FILAS ===")
f = api.get(f"/api/v1/workflows/{RESUMEN}")
nodos = []
for n in f["nodes"]:
    if n.get("type", "").endswith("dataTable"):
        p = dict(n.get("parameters") or {})
        p["returnAll"] = True
        n = dict(n, parameters=p)
    nodos.append(n)
nodos.append({"parameters": {"httpMethod": "POST", "path": "homelab-resumen-sonda", "options": {}}, "id": "wh-r2",
              "name": "Sonda webhook (resumen)", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [-760, 500],
              "webhookId": "sonda-resumen"})
conex = dict(f["connections"])
conex["Sonda webhook (resumen)"] = {"main": [[{"node": n["name"], "type": "main", "index": i}
                                              for i, n in enumerate([x for x in nodos if x.get("type", "").endswith("dataTable")])]]}
api.put(f"/api/v1/workflows/{RESUMEN}", {"name": f["name"], "nodes": nodos, "connections": conex, "settings": f.get("settings") or {}})
print(f"  returnAll aplicado a {len([n for n in nodos if n.get('type','').endswith('dataTable')])} nodos de tabla")
api.post(f"/api/v1/workflows/{RESUMEN}/activate")
antes = (api.get(f"/api/v1/executions?workflowId={RESUMEN}&limit=1").get("data") or [{}])[0].get("id", 0)
req = urllib.request.Request(f"{api.BASE}/webhook/homelab-resumen-sonda", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=60, context=ctx)
time.sleep(20)
ex2 = api.get(f"/api/v1/executions?workflowId={RESUMEN}&limit=1").get("data") or []
if ex2 and ex2[0]["id"] != antes:
    det = api.get(f"/api/v1/executions/{ex2[0]['id']}?includeData=true")
    rd = ((det.get("data") or {}).get("resultData") or {}).get("runData") or {}
    try:
        j = rd["Preparar resumen"][0]["data"]["main"][0][0]["json"]
        print(f"  ejecución {ex2[0]['id']}: backlog leído = {j.get('backlog')} (>50 demuestra que ya no se topa)")
        print(f"  nuevas={j.get('nuevas')} errores={j.get('errores')}")
    except Exception as e:  # noqa: BLE001
        print("  (sin salida)", str(e)[:90])
print("\n  (pendiente: quitar la sonda webhook del resumen y dejarlo en cron)")
