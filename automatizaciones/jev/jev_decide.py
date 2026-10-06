#!/usr/bin/env python3
"""Decisión acotada con Jev: propone un ORDEN de ejecución entre opciones permitidas.

Reglas (permisos definidos por código, no por el modelo):
  - Jev SOLO puede reordenar las opciones que el código le entrega. Nunca añade opciones ni concede permisos.
  - La ordenación se acepta únicamente si Jev responde con confianza suficiente y todas las claves son válidas.
  - Si falla, se abstiene, tarda demasiado o responde algo inválido -> FALLBACK determinista (prioridad del backlog).
  - Se registran métricas (ms, tokens, coste) y el motivo de uso o descarte.
"""
from __future__ import annotations
import inspect
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import jev_adapter  # noqa: E402

UMBRAL = 0.65
FUNCIONES = ("decidir", "clasificar", "recomendar", "recomendar_orden", "evaluar", "llamar", "procesar")
LOG = os.path.join(AQUI, "jev_decisiones.jsonl")


def _fallback(candidatas, motivo, extra=None):
    orden = [c["clave"] for c in sorted(candidatas, key=lambda x: -(x.get("prioridad") or 0))]
    reg = {"usado": False, "motivo": motivo, "orden": orden, "fallback": True, "cuando": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if extra:
        reg.update(extra)
    _log(reg)
    return reg


def _log(reg):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")


def recomendar_orden(candidatas, opciones):
    """candidatas: [{clave, titulo, ci, prioridad, proyecto}] · opciones: claves permitidas."""
    if not candidatas or not opciones:
        return _fallback(candidatas or [{"clave": "nada", "prioridad": 0}], "sin candidatas")
    funciones = [(n, f) for n in FUNCIONES for f in [getattr(jev_adapter, n, None)] if callable(f)]
    if not funciones:
        # el adaptador puede exponer una clase: se instancia y se busca su método público de decisión
        clases = [(n, c) for n, c in vars(jev_adapter).items()
                  if isinstance(c, type) and not n.startswith("_") and "Adapter" in n]
        for nombre_clase, cls in clases:
            try:
                try:
                    inst = cls(offline=False)
                except Exception:
                    inst = cls()
            except Exception:  # noqa: BLE001
                continue
            for m in ("clasificar_tarea", "seleccionar_herramienta", "decidir", "clasificar", "recomendar", "evaluar"):
                f = getattr(inst, m, None)
                if callable(f) and not m.startswith("_"):
                    funciones.append((f"{nombre_clase}.{m}", f))
                    break
    if not funciones:
        return _fallback(candidatas, "el adaptador no expone función ni método de decisión utilizables")
    nombre, fn = funciones[0]
    params = list(inspect.signature(fn).parameters)
    texto = ("Ordena de mayor a menor prioridad estas tareas de proyecto. Responde SOLO con un JSON "
             '{"orden": ["clave", ...], "confianza": 0.0-1.0} usando exactamente estas claves: '
             + json.dumps(opciones, ensure_ascii=False) + ". Tareas: "
             + json.dumps([{k: c.get(k) for k in ("clave", "proyecto", "ci", "prioridad", "titulo")} for c in candidatas],
                          ensure_ascii=False))
    try:
        if len(params) >= 2:
            r = fn(texto, opciones)
        else:
            r = fn(texto)
    except Exception as e:  # noqa: BLE001
        return _fallback(candidatas, f"error al llamar al adaptador ({nombre}): {str(e)[:80]}")
    if isinstance(r, dict):
        datos = r
    elif hasattr(r, "__dict__"):
        datos = {k: v for k, v in vars(r).items()}
    else:
        datos = {"respuesta": str(r)}
    if datos.get("abstener"):
        return _fallback(candidatas, f"Jev se abstiene: {datos.get('motivo')}")
    dist = datos.get("distribucion") or {}
    if isinstance(dist, dict) and dist:
        orden = [k for k, _ in sorted(((k, v) for k, v in dist.items() if k in opciones),
                                      key=lambda x: -(x[1] if isinstance(x[1], (int, float)) else 0))]
    else:
        favorito = datos.get("valor") or datos.get("campo")
        orden = [favorito] + [k for k in opciones if k != favorito] if favorito in opciones else None
    conf = datos.get("confianza", datos.get("confidence"))
    if isinstance(orden, str):
        try:
            orden = json.loads(orden).get("orden")
        except Exception:  # noqa: BLE001
            orden = None
    ok_claves = isinstance(orden, list) and orden and all(k in opciones for k in orden)
    if not ok_claves:
        return _fallback(candidatas, "respuesta sin orden válido (o con claves no permitidas)",
                         {"respuesta_cruda": json.dumps(datos, ensure_ascii=False)[:200]})
    if conf is not None and float(conf) < UMBRAL:
        return _fallback(candidatas, f"confianza {conf} por debajo del umbral {UMBRAL}",
                         {"confianza": conf, "orden_sugerido": orden})
    faltan = [k for k in opciones if k not in orden]
    orden = orden + faltan
    reg = {"usado": True, "motivo": f"recomendación aceptada de {nombre}", "orden": orden, "confianza": conf,
           "tokens": datos.get("tokens") or datos.get("usage"), "coste_usd": datos.get("coste_usd") or datos.get("cost"),
           "modelo": datos.get("modelo") or datos.get("model"), "fallback": False,
           "cuando": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _log(reg)
    return reg


if __name__ == "__main__":
    demo = [{"clave": "celestinojbm/nova-context#19", "proyecto": "nova-context", "ci": "fallo", "prioridad": 83,
             "titulo": "filas de tarea ilegibles en movil"},
            {"clave": "celestinojbm/Dona-agent#276", "proyecto": "Dona-agent", "ci": "fallo", "prioridad": 80,
             "titulo": "detalle de accion y decision en el centro de accion"},
            {"clave": "celestinojbm/Donalabs#4", "proyecto": "Donalabs", "ci": "fallo", "prioridad": 72,
             "titulo": "expand DonaLabs agent platform"}]
    t0 = time.time()
    r = recomendar_orden(demo, [c["clave"] for c in demo])
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"  ms={int((time.time() - t0) * 1000)}")
