#!/usr/bin/env python3
"""Prueba de paginación real contra GitHub con tamaño de página pequeño (5), sin enviar nada a Telegram."""
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

ID = "pI3cliNDh0aReDV5"
RUTA = "homelab-avisos-sonda"
ctx = ssl._create_unverified_context()
PAGINA = 5

JS_CTL = r"""
// TEMPORAL (solo prueba): fija ventana y cursores desde el cuerpo de la peticion.
const sd = $getWorkflowStaticData('global');
const body = (($input.first() || {}).json || {}).body || {};
const hecho = {};
if (body.window) { sd.window = body.window; hecho.window = body.window; }
if (body.cursorRec !== undefined) { sd.cursorRec = body.cursorRec; hecho.cursorRec = body.cursorRec; }
if (body.cursorAbi !== undefined) { sd.cursorAbi = body.cursorAbi; hecho.cursorAbi = body.cursorAbi; }
sd.runningSince = 0;
return [{ json: { control: hecho } }];
"""


def disparar(cuerpo=None):
    req = urllib.request.Request(f"{api.BASE}/webhook/{RUTA}", data=json.dumps(cuerpo or {}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        return r.status


def montar_temporal():
    f = api.get(f"/api/v1/workflows/{ID}")
    nodos = []
    for n in f["nodes"]:
        if n["name"] == "Telegram · chat privado":
            n = dict(n, parameters=dict(n.get("parameters") or {}, chatId="0"))     # destino inválido: no envía
        if n["name"] == "Preparar consulta (cursor y ventana)":
            js = n["parameters"]["jsCode"].replace("first: 100", f"first: {PAGINA}")
            n = dict(n, parameters=dict(n["parameters"], jsCode=js))
        nodos.append(n)
    nodos.append({"parameters": {"httpMethod": "POST", "path": RUTA, "options": {}}, "id": "sonda01",
                  "name": "Sonda webhook (temporal)", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
                  "position": [-900, 300], "webhookId": "sonda-homelab"})
    nodos.append({"parameters": {"mode": "runOnceForAllItems", "jsCode": JS_CTL}, "id": "ctl01",
                  "name": "Control temporal (reset)", "type": "n8n-nodes-base.code", "typeVersion": 2,
                  "position": [-760, 200]})
    conex = dict(f["connections"])
    conex["Sonda webhook (temporal)"] = {"main": [[{"node": "Control temporal (reset)", "type": "main", "index": 0}]]}
    conex["Control temporal (reset)"] = {"main": [[{"node": "Preparar consulta (cursor y ventana)", "type": "main", "index": 0}]]}
    api.put(f"/api/v1/workflows/{ID}", {"name": f["name"], "nodes": nodos, "connections": conex,
                                        "settings": f.get("settings") or {}})
    return f


def leer():
    ex = api.get(f"/api/v1/executions?workflowId={ID}&limit=1").get("data") or []
    if not ex:
        return {}
    det = api.get(f"/api/v1/executions/{ex[0]['id']}?includeData=true")
    rd = ((det.get("data") or {}).get("resultData") or {}).get("runData") or {}
    def sal(n):
        try:
            return rd[n][0]["data"]["main"][0][0]["json"]
        except Exception:  # noqa: BLE001
            return {}
    f = api.get(f"/api/v1/workflows/{ID}")
    return {"eid": ex[0]["id"], "consulta": sal("Preparar consulta (cursor y ventana)"),
            "avisos": sal("Preparar aviso (dedup, pendiente)"), "estado": dict(((f.get("staticData") or {}).get("global") or {}))}


def nuevo(cuerpo, espera=22):
    antes = (api.get(f"/api/v1/executions?workflowId={ID}&limit=1").get("data") or [{}])[0].get("id", 0)
    disparar(cuerpo)
    time.sleep(espera)
    ex = api.get(f"/api/v1/executions?workflowId={ID}&limit=1").get("data") or []
    if not ex or ex[0]["id"] == antes:
        return {}
    return leer()


print(f"=== PAGINACIÓN REAL CONTRA GITHUB CON PÁGINA DE {PAGINA} (destino inválido: no envía nada) ===")
montar_temporal()
api.post(f"/api/v1/workflows/{ID}/activate")
print(f"  activo: {api.get(f'/api/v1/workflows/{ID}')['active']} · page_size={PAGINA}")
r = nuevo({"window": "2026-09-05T00:00:00.000Z"})
vistos = set()
for i in range(1, 9):
    if not r:
        print(f"  pasada {i}: sin ejecución nueva"); break
    c, j, e = r["consulta"], r["avisos"], r["estado"]
    ids = {x.get("id") for x in (j.get("eventos") or [])} if isinstance(j.get("eventos"), list) else set()
    print(f"  pasada {i} (ej. {r['eid']}): eventos={j.get('eventos')} pag={j.get('paginacion')}")
    print(f"     cursor usado -> rec={str(c.get('cursorRec'))[:24]}")
    print(f"     cursor guardado -> rec={str(e.get('cursorRec'))[:24]} abi={str(e.get('cursorAbi'))[:24]}")
    msg = j.get("message") or ""
    if msg:
        print(f"     nota: {'SIN CUBRIR (continuación guardada)' if 'aun sin cubrir' in msg else 'VENTANA CUBIERTA'}")
    if not e.get("cursorRec") and not e.get("cursorAbi"):
        print(f"     ==> PAGINACIÓN TERMINADA en la pasada {i}: cursores limpios, sin aviso de truncamiento")
        break
    r = nuevo({})

print("\n=== RESTAURACIÓN DE LA FORMA DE PRODUCCIÓN (página 100, sin nodos de prueba) ===")
f = api.get(f"/api/v1/workflows/{ID}")
nodos = []
for n in f["nodes"]:
    if n["name"] in ("Sonda webhook (temporal)", "Control temporal (reset)"):
        continue
    if n["name"] == "Telegram · chat privado":
        n = dict(n, parameters=dict(n.get("parameters") or {}, chatId="CHAT_PRIVADO_POR_VARIABLE"))
    nodos.append(n)
nombres = {n["name"] for n in nodos}
conex = {k: v for k, v in (f["connections"] or {}).items() if k in nombres}
conex["Cada 10 minutos"] = {"main": [[{"node": "Preparar consulta (cursor y ventana)", "type": "main", "index": 0}]]}
api.put(f"/api/v1/workflows/{ID}", {"name": f["name"], "nodes": nodos, "connections": conex,
                                    "settings": f.get("settings") or {}})
f2 = api.get(f"/api/v1/workflows/{ID}")
print(f"  nodos={len(f2['nodes'])} · disparadores={[n['name'] for n in f2['nodes'] if 'trigger' in n['type'].lower()]}")
print(f"  nodos de prueba: {[n['name'] for n in f2['nodes'] if 'Sonda' in n['name'] or 'Control' in n['name']]}")
print(f"  tamaño de página restaurado: {'first: 100' in next(n for n in f2['nodes'] if n['name']=='Preparar consulta (cursor y ventana)')['parameters']['jsCode']}")
print(f"  activo={f2['active']}")
