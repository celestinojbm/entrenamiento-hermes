#!/usr/bin/env python3
"""Crea el workflow de salud de servicios (caída/recuperación sin repetir) y prueba su lógica."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import ssl

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import n8n_api as api  # noqa: E402

BASE = api.BASE
CRED_TG = {"id": "CREDENCIAL_TELEGRAM", "name": "Telegram Homelab"}
CHAT = "CHAT_PRIVADO_POR_VARIABLE"
RUTA = "homelab-salud-sonda"
ctx = ssl._create_unverified_context()

JS_EVAL = r"""
// Salud de servicios: avisa SOLO en transiciones (caida / recuperacion), nunca repite la misma incidencia.
const FALLOS_PARA_AVISAR = 2;
const sd = $getWorkflowStaticData('global');
sd.servicios = sd.servicios || {};
const defs = [
  { nombre: 'Uptime Kuma', nodo: 'Comprobar Kuma', esperado: 200 },
  { nombre: 'n8n', nodo: 'Comprobar n8n', esperado: 200 },
  { nombre: 'Hermes remoto', nodo: 'Comprobar Hermes', esperado: 200 },
];
const lineas = [];
for (const d of defs) {
  let code = null, err = null;
  try {
    const j = $('' + d.nodo).first().json;
    code = j.statusCode !== undefined ? j.statusCode : null;
    err = j.error || null;
  } catch (e) { err = String(e.message || e); }
  const ok = code === d.esperado;
  const prev = sd.servicios[d.nombre] || { fallosSeguidos: 0, ok: true, avisado: false };
  const st = { fallosSeguidos: ok ? 0 : (prev.fallosSeguidos || 0) + 1, ok };
  if (!ok) {
    if (st.fallosSeguidos >= FALLOS_PARA_AVISAR && !prev.avisado) {
      lineas.push('CAIDA: ' + d.nombre + ' (respuesta ' + (code === null ? 'sin respuesta' : code) +
        (err ? ' / ' + String(err).slice(0, 60) : '') + ')');
      st.avisado = true;
    }
  } else if (prev.avisado) {
    lineas.push('RECUPERADO: ' + d.nombre + ' vuelve a responder ' + code);
    st.avisado = false;
  }
  if (!ok && prev.avisado) st.avisado = true;
  st.desde = prev.desde && prev.ok === ok ? prev.desde : new Date().toISOString();
  sd.servicios[d.nombre] = st;
}
const msg = lineas.length ? 'HomeLab - salud de servicios\n' + lineas.join('\n') : '';
return [{ json: { message: msg, estado: sd.servicios } }];
"""

nodos = [
    {"parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}}, "id": "sched5",
     "name": "Cada 5 minutos", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [-560, 300]},
    {"parameters": {"mode": "runOnceForAllItems", "jsCode": JS_EVAL}, "id": "eval1",
     "name": "Evaluar y decidir", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [300, 300]},
    {"parameters": {"conditions": {"options": {"caseSensitive": True, "typeValidation": "loose", "version": 2},
                                   "conditions": [{"id": "c1", "leftValue": "={{ $json.message }}", "rightValue": "",
                                                   "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}],
                                   "combinator": "and"}, "options": {}}, "id": "if1",
     "name": "¿Hay aviso?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [520, 300]},
    {"parameters": {"chatId": CHAT, "text": "={{ $json.message }}", "additionalFields": {}}, "id": "tg1",
     "name": "Telegram · salud", "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": [740, 200],
     "credentials": {"telegramApi": CRED_TG}, "onError": "continueErrorOutput"},
    {"parameters": {}, "id": "noop1", "name": "Sin aviso", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [740, 400]},
    {"parameters": {"httpMethod": "POST", "path": RUTA, "options": {}}, "id": "sonda_salud",
     "name": "Sonda webhook (salud)", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [-760, 300],
     "webhookId": "sonda-salud"},
]
for i, (nombre, url) in enumerate((("Comprobar Kuma", f"{BASE}/"),
                                   ("Comprobar n8n", f"{BASE}/healthz"),
                                   ("Comprobar Hermes", f"{BASE.replace(':8443', ':10000')}/api/health"))):
    nodos.append({"parameters": {"url": url, "options": {"timeout": 15000, "response": {"response": {"fullResponse": True, "neverError": True}}}},
                  "id": f"http{i}", "name": nombre, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
                  "position": [60, 120 + i * 160], "onError": "continueRegularOutput"})

conex = {
    "Cada 5 minutos": {"main": [[{"node": "Comprobar Kuma", "type": "main", "index": 0},
                                 {"node": "Comprobar n8n", "type": "main", "index": 0},
                                 {"node": "Comprobar Hermes", "type": "main", "index": 0}]]},
    "Sonda webhook (salud)": {"main": [[{"node": "Comprobar Kuma", "type": "main", "index": 0},
                                        {"node": "Comprobar n8n", "type": "main", "index": 0},
                                        {"node": "Comprobar Hermes", "type": "main", "index": 0}]]},
    "Comprobar Kuma": {"main": [[{"node": "Evaluar y decidir", "type": "main", "index": 0}]]},
    "Comprobar n8n": {"main": [[{"node": "Evaluar y decidir", "type": "main", "index": 0}]]},
    "Comprobar Hermes": {"main": [[{"node": "Evaluar y decidir", "type": "main", "index": 0}]]},
    "Evaluar y decidir": {"main": [[{"node": "¿Hay aviso?", "type": "main", "index": 0}]]},
    "¿Hay aviso?": {"main": [[{"node": "Telegram · salud", "type": "main", "index": 0}],
                             [{"node": "Sin aviso", "type": "main", "index": 0}]]},
    "Telegram · salud": {"main": [[{"node": "Sin aviso", "type": "main", "index": 0}],
                                  [{"node": "Sin aviso", "type": "main", "index": 0}]]},
}

print("=== 1. BANCO DE PRUEBAS DE LA LÓGICA (sin tocar servicios) ===")
harness = r"""
const $getWorkflowStaticData = (() => { const sd = {}; return () => sd; })();
const st = {};
const $ = (n) => ({ first: () => ({ json: { statusCode: st[n], error: st[n] === undefined ? 'sin respuesta' : null } }) });
const ejecutar = new Function('$getWorkflowStaticData', '$', %s);
const disparo = (kuma, n8n, herm) => { st['Comprobar Kuma'] = kuma; st['Comprobar n8n'] = n8n; st['Comprobar Hermes'] = herm;
  return ejecutar($getWorkflowStaticData, $)[0].json; };
let r = disparo(200, 200, 200);
const ok1 = r.message === '';
console.log('  1) todo sano -> mensaje vacio: ' + ok1);
r = disparo(500, 200, 200);
const ok2 = r.message === '';
console.log('  2) primer fallo (umbral 2) -> sin aviso todavia: ' + ok2);
r = disparo(500, 200, 200);
const ok3 = r.message.includes('CAIDA: Uptime Kuma');
console.log('  3) segundo fallo -> aviso de caida: ' + ok3 + ' | ' + JSON.stringify(r.message));
r = disparo(500, 200, 200);
const ok4 = r.message === '';
console.log('  4) la incidencia persiste -> NO repite: ' + ok4);
r = disparo(200, 200, 200);
const ok5 = r.message.includes('RECUPERADO: Uptime Kuma');
console.log('  5) vuelve a responder -> aviso de recuperacion: ' + ok5 + ' | ' + JSON.stringify(r.message));
r = disparo(200, 200, 200);
const ok6 = r.message === '';
console.log('  6) ya recuperado -> silencio: ' + ok6);
console.log('  RESULTADO: ' + ([ok1, ok2, ok3, ok4, ok5, ok6].every(Boolean) ? '6/6 OK' : 'revisar'));
"""
rutina = harness.replace("%s", json.dumps(JS_EVAL))
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
    fh.write(rutina)
    tmp = fh.name
rr = subprocess.run(["node", tmp], capture_output=True, text=True)
print(rr.stdout.strip() or rr.stderr[:600])

print("\n=== 2. CREACIÓN DEL WORKFLOW PARA LA PRUEBA REAL ===")
nodos_prueba = [n for n in nodos if n["name"] != "Cada 5 minutos"]
conex_prueba = {k: v for k, v in conex.items() if k != "Cada 5 minutos"}
w = api.post("/api/v1/workflows", {"name": "HomeLab · salud de servicios (caída y recuperación)",
                                   "nodes": nodos_prueba, "connections": conex_prueba,
                                   "settings": {"saveDataSuccessExecution": "all", "executionOrder": "v1"}})
print(f"  creado id={w['id']} nodos={len(w['nodes'])} activo={w['active']}")
open(os.path.join(AQUI, "workflow_salud.json"), "w", encoding="utf-8").write(json.dumps({"id": w["id"]}, indent=1))
api.post(f"/api/v1/workflows/{w['id']}/activate")
print(f"  activo para la prueba: {api.get(f'/api/v1/workflows/{w["id"]}')['active']}")
antes = (api.get(f"/api/v1/executions?workflowId={w['id']}&limit=1").get("data") or [{}])[0].get("id", 0)
req = urllib.request.Request(f"{BASE}/webhook/{RUTA}", data=b"{}", method="POST", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
    print(f"  disparo real: HTTP {resp.status}")
time.sleep(15)
ex = api.get(f"/api/v1/executions?workflowId={w['id']}&limit=1").get("data") or []
if ex and ex[0]["id"] != antes:
    det = api.get(f"/api/v1/executions/{ex[0]['id']}?includeData=true")
    rd = ((det.get("data") or {}).get("resultData") or {}).get("runData") or {}
    print(f"  ejecución {ex[0]['id']} ({ex[0]['status']}): {' -> '.join(rd.keys())}")
    try:
        j = rd["Evaluar y decidir"][0]["data"]["main"][0][0]["json"]
        print(f"  estado real de los servicios: {json.dumps(j.get('estado'), ensure_ascii=False)[:300]}")
        print(f"  mensaje: {j.get('message')!r} (vacío = todo sano, no se envía nada)")
    except Exception as e:  # noqa: BLE001
        print("  (sin salida legible)", str(e)[:100])
