#!/usr/bin/env python3
"""Resumen diario: workflow en n8n (lee las tablas internas y avisa solo si hay novedad) + activación."""
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

CRED_TG = {"id": "CREDENCIAL_TELEGRAM", "name": "Telegram Homelab"}
CHAT = "CHAT_PRIVADO_POR_VARIABLE"
RUTA = "homelab-resumen-sonda"
ctx = ssl._create_unverified_context()

JS = r"""
// Resumen diario. Silencio si no hay nada nuevo desde el ultimo resumen.
const sd = $getWorkflowStaticData('global');
const filas = (n) => { try { return $(n).all().map(i => i.json); } catch (e) { return []; } };
const ejec = filas('Ejecutadas'), backlog = filas('Backlog'), errores = filas('Errores');
const desde = Number(sd.ultimo || 0);
const t = (x) => { const v = Date.parse(x || ''); return isNaN(v) ? 0 : v; };
const nuevas = ejec.filter(e => t(e.finished_at || e.finishedAt) > desde);
const errNuevos = errores.filter(e => t(e.cuando || e.createdAt) > desde);
const PRODUCTO = ['pull_request', 'issue', 'ci_run', 'backlog_update', 'backlog_proyectos'];
const producto = nuevas.filter(e => PRODUCTO.includes(String(e.tipo || '')));
const manteni = nuevas.filter(e => !PRODUCTO.includes(String(e.tipo || '')));
const fallo = backlog.filter(b => String(b.ci) === 'fallo' && String(b.estado) === 'abierto');
const altos = backlog.filter(b => Number(b.prioridad) >= 80);
const proyectos = new Set(backlog.map(b => b.proyecto));
const lineas = [];
if (producto.length) {
  lineas.push('AVANCE DE PRODUCTO (' + producto.length + '):');
  for (const e of producto.slice(0, 5)) lineas.push('  - ' + String(e.resultado || '').slice(0, 150));
}
if (manteni.length) lineas.push('MANTENIMIENTO: ' + manteni.length + ' comprobaciones ejecutadas');
if (fallo.length) {
  lineas.push('BLOQUEOS (' + fallo.length + ' PR con CI en fallo):');
  for (const b of fallo.slice(0, 5)) lineas.push('  - ' + b.proyecto + ' #' + b.numero + ' ' + String(b.titulo || '').slice(0, 70));
}
if (errNuevos.length) lineas.push('ERRORES NUEVOS: ' + errNuevos.length + ' (' + String(errNuevos[0].workflow_name || errNuevos[0].nombre || '') + ')');
lineas.push('Backlog: ' + backlog.length + ' elementos en ' + proyectos.size + ' proyectos (' + altos.length + ' de prioridad alta)');
const msg = (nuevas.length || errNuevos.length) ? ('Resumen diario HomeLab - ' + new Date().toISOString().slice(0, 16).replace('T', ' ') + '\n' + lineas.join('\n')) : '';
if (msg) { sd.ultimo = Date.now(); sd.ultimo_texto = msg; }
return [{ json: { message: msg, nuevas: nuevas.length, errores: errNuevos.length, backlog: backlog.length } }];
"""


def nodo_tabla(nombre, tabla_id, tabla_nombre, pos):
    return {"parameters": {"operation": "get", "dataTableId": {"__rl": True, "value": tabla_id, "mode": "list",
                                                               "cachedResultName": tabla_nombre}},
            "id": "dt-" + nombre.replace(" ", "")[:6], "name": nombre, "type": "n8n-nodes-base.dataTable",
            "typeVersion": 1, "position": pos}


def tablas():
    t = api.get("/api/v1/data-tables?limit=50").get("data") or []
    return {x["name"]: x["id"] for x in t}


def construir(con_webhook):
    ids = tablas()
    nodos = [
        nodo_tabla("Ejecutadas", ids["homelab_dispatch_results"], "homelab_dispatch_results", [-460, 120]),
        nodo_tabla("Backlog", ids["homelab_backlog"], "homelab_backlog", [-460, 300]),
        nodo_tabla("Errores", ids["homelab_error_log"], "homelab_error_log", [-460, 480]),
        {"parameters": {"mode": "runOnceForAllItems", "jsCode": JS}, "id": "resumen1", "name": "Preparar resumen",
         "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [-180, 300]},
        {"parameters": {"conditions": {"options": {"caseSensitive": True, "typeValidation": "loose", "version": 2},
                                       "conditions": [{"id": "c1", "leftValue": "={{ $json.message }}", "rightValue": "",
                                                       "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}],
                                       "combinator": "and"}, "options": {}}, "id": "if-r", "name": "¿Hay resumen?",
         "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [40, 300]},
        {"parameters": {"chatId": CHAT, "text": "={{ $json.message }}", "additionalFields": {}}, "id": "tg-r",
         "name": "Telegram · resumen", "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": [260, 200],
         "credentials": {"telegramApi": CRED_TG}, "onError": "continueErrorOutput"},
        {"parameters": {}, "id": "noop-r", "name": "Sin novedades", "type": "n8n-nodes-base.noOp", "typeVersion": 1,
         "position": [260, 400]},
    ]
    conex = {
        "Ejecutadas": {"main": [[{"node": "Merge (espera las 3 tablas)", "type": "main", "index": 0}]]},
        "Backlog": {"main": [[{"node": "Merge (espera las 3 tablas)", "type": "main", "index": 1}]]},
        "Errores": {"main": [[{"node": "Merge (espera las 3 tablas)", "type": "main", "index": 2}]]},
        "Merge (espera las 3 tablas)": {"main": [[{"node": "Preparar resumen", "type": "main", "index": 0}]]},
        "Preparar resumen": {"main": [[{"node": "¿Hay resumen?", "type": "main", "index": 0}]]},
        "¿Hay resumen?": {"main": [[{"node": "Telegram · resumen", "type": "main", "index": 0}],
                                   [{"node": "Sin novedades", "type": "main", "index": 0}]]},
        "Telegram · resumen": {"main": [[{"node": "Sin novedades", "type": "main", "index": 0}],
                                        [{"node": "Sin novedades", "type": "main", "index": 0}]]},
    }
    nodos.append({"parameters": {"mode": "combineAll", "numberInputs": 3}, "id": "merge-r",
                  "name": "Merge (espera las 3 tablas)", "type": "n8n-nodes-base.merge", "typeVersion": 3,
                  "position": [-300, 300]})
    if con_webhook:
        nodos.append({"parameters": {"httpMethod": "POST", "path": RUTA, "options": {}}, "id": "wh-r",
                      "name": "Sonda webhook (resumen)", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
                      "position": [-760, 300], "webhookId": "sonda-resumen"})
        conex["Sonda webhook (resumen)"] = {"main": [[{"node": "Ejecutadas", "type": "main", "index": 0},
                                                     {"node": "Backlog", "type": "main", "index": 0},
                                                     {"node": "Errores", "type": "main", "index": 0}]]}
    else:
        nodos.insert(0, {"parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "30 21 * * *"}]}},
                         "id": "cron-r", "name": "Cada día a las 21:30", "type": "n8n-nodes-base.scheduleTrigger",
                         "typeVersion": 1.2, "position": [-760, 300]})
        conex["Cada día a las 21:30"] = {"main": [[{"node": "Ejecutadas", "type": "main", "index": 0},
                                                  {"node": "Backlog", "type": "main", "index": 0},
                                                  {"node": "Errores", "type": "main", "index": 0}]]}
    return nodos, conex


print("=== 1. WORKFLOW (reutiliza el existente por nombre; con webhook temporal) ===")
prev = next((x for x in (api.get("/api/v1/workflows?limit=100").get("data") or [])
             if x.get("name", "").startswith("HomeLab · resumen diario")), None)
nodos, conex = construir(True)
if prev:
    w = api.put(f"/api/v1/workflows/{prev['id']}", {"name": prev["name"], "nodes": nodos, "connections": conex,
                                                    "settings": prev.get("settings") or {}})
    print(f"  actualizado id={w['id']} (no se crea otro)")
else:
    w = api.post("/api/v1/workflows", {"name": "HomeLab · resumen diario (producto, mantenimiento y bloqueos)",
                                       "nodes": nodos, "connections": conex,
                                       "settings": {"saveDataSuccessExecution": "all", "executionOrder": "v1"}})
    print(f"  creado id={w['id']} nodos={len(w['nodes'])}")
api.post(f"/api/v1/workflows/{w['id']}/activate")
antes = (api.get(f"/api/v1/executions?workflowId={w['id']}&limit=1").get("data") or [{}])[0].get("id", 0)
req = urllib.request.Request(f"{api.BASE}/webhook/{RUTA}", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=60, context=ctx)
time.sleep(18)
ex = api.get(f"/api/v1/executions?workflowId={w['id']}&limit=1").get("data") or []
if ex and ex[0]["id"] != antes:
    det = api.get(f"/api/v1/executions/{ex[0]['id']}?includeData=true")
    rd = ((det.get("data") or {}).get("resultData") or {}).get("runData") or {}
    print(f"  ejecución {ex[0]['id']} ({ex[0]['status']}): {' -> '.join(rd.keys())}")
    try:
        j = rd["Preparar resumen"][0]["data"]["main"][0][0]["json"]
        print(f"  nuevas={j.get('nuevas')} errores={j.get('errores')} backlog={j.get('backlog')}")
        print("  MENSAJE:")
        for l in (j.get("message") or "").split("\n"):
            print(f"    {l[:120]}")
        t = rd.get("Telegram · resumen")
        if t:
            print(f"  Telegram: ok={(t[0]['data']['main'][0][0]['json'] or {}).get('ok')} "
                  f"message_id={((t[0]['data']['main'][0][0]['json'] or {}).get('result') or {}).get('message_id')}")
    except Exception as e:  # noqa: BLE001
        print("  (sin salida)", str(e)[:90])

print("\n=== 2. FORMA DE PRODUCCIÓN (cron diario 21:30) y ACTIVACIÓN ===")
f = api.get(f"/api/v1/workflows/{w['id']}")
nodos, conex = construir(False)
api.put(f"/api/v1/workflows/{w['id']}", {"name": f["name"], "nodes": nodos, "connections": conex,
                                         "settings": f.get("settings") or {}})
api.post(f"/api/v1/workflows/{w['id']}/activate")
f2 = api.get(f"/api/v1/workflows/{w['id']}")
print(f"  activo={f2['active']} · nodos={len(f2['nodes'])} · disparadores={[n['name'] for n in f2['nodes'] if 'trigger' in n['type'].lower()]}")
print(f"  enlace: {api.BASE}/workflow/{w['id']}")
open(os.path.join(AQUI, "workflow_resumen.json"), "w", encoding="utf-8").write(json.dumps({"id": w["id"]}, indent=1))
