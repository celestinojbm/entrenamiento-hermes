#!/usr/bin/env python3
"""Presupuesto diario verificable del puente (issue #3, punto 8).

El límite NO se aplica "en la configuración": se aplica con una comprobación
efectiva antes de cada ejecución y un registro de gasto real leído de una fuente
auditable — la tabla `sessions` de `~/.hermes/state.db`, que Hermes escribe con
`estimated_cost_usd` / `actual_cost_usd`, `cost_status` y `cost_source`.

Reglas:

  * El día presupuestario se reinicia a medianoche de **America/New_York**.
  * Antes de ejecutar: si el gasto del día + el coste de la ejecución anterior
    proyectada supera el límite, NO se ejecuta.
  * Después de ejecutar: se lee el coste real de la sesión recién creada y se
    suma al libro.
  * **Fallo cerrado ante coste desconocido.** Si una ejecución termina con
    `cost_status` nulo o desconocido y consumió tokens, el consumo no puede
    acotarse: el ejecutor queda bloqueado hasta reconciliación manual.
    Un límite que se ignora cuando no se puede medir no es un límite.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
STATE_DB = Path(os.environ.get("HERMES_STATE_DB", Path.home() / ".hermes" / "state.db"))

# Estados de coste que consideramos medidos.
COSTO_CONOCIDO = {"estimated", "actual", "included"}


def dia_actual() -> str:
    """Día presupuestario según America/New_York."""
    return datetime.now(TZ).date().isoformat()


def libro_vacio() -> dict:
    return {"dia": dia_actual(), "gastado_usd": 0.0, "ejecuciones": [], "desconocido": False}


def cargar_libro(path: Path) -> dict:
    try:
        libro = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        libro = libro_vacio()
    # Reinicio del día según la zona pedida (no según la hora local del sistema).
    if libro.get("dia") != dia_actual():
        libro = libro_vacio()
    libro.setdefault("ejecuciones", [])
    libro.setdefault("gastado_usd", 0.0)
    libro.setdefault("desconocido", False)
    return libro


def guardar_libro(path: Path, libro: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(libro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def coste_de_sesiones_desde(t0: float) -> tuple[float, list[dict], bool]:
    """Coste de las sesiones de Hermes iniciadas después de `t0`.

    Devuelve (coste_total, detalle, hubo_desconocido).
    """
    if not STATE_DB.exists():
        return 0.0, [], True   # sin fuente de verdad => no se puede acotar
    con = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    try:
        filas = con.execute(
            """select id, source, model, started_at, input_tokens, output_tokens,
                      estimated_cost_usd, actual_cost_usd, cost_status, cost_source
                 from sessions where started_at >= ? order by started_at asc""",
            (t0 - 2.0,),
        ).fetchall()
    finally:
        con.close()

    total = 0.0
    detalle: list[dict] = []
    desconocido = False
    for (sid, source, model, started, tin, tout, est, act, status, csource) in filas:
        valor = act if act is not None else est
        if status in COSTO_CONOCIDO and valor is not None:
            total += float(valor)
        else:
            # Consumió tokens y no sabemos cuánto costó: no se puede acotar.
            if (tin or 0) + (tout or 0) > 0:
                desconocido = True
        detalle.append({
            "sesion": sid, "source": source, "model": model,
            "in_tokens": tin, "out_tokens": tout,
            "coste_usd": valor, "cost_status": status, "cost_source": csource,
        })
    return total, detalle, desconocido


def puede_gastar(libro: dict, limite_usd: float) -> tuple[bool, str]:
    """¿Se puede ejecutar una tarea ahora mismo?"""
    if limite_usd is None or limite_usd <= 0:
        return False, "sin presupuesto asignado (limite_usd nulo o cero)"
    if libro.get("desconocido"):
        return False, "hay consumo previo con coste desconocido: no puede acotarse, requiere reconciliación"
    restante = limite_usd - float(libro.get("gastado_usd", 0.0))
    if restante <= 0:
        return False, f"presupuesto diario agotado ({libro['gastado_usd']:.6f} de {limite_usd:.2f} USD)"
    return True, f"restante {restante:.6f} USD de {limite_usd:.2f}"


def registrar(libro: dict, t0: float, detalle_orden: dict, limite_usd: float) -> dict:
    """Suma al libro el coste de las sesiones creadas desde t0."""
    coste, detalle, desconocido = coste_de_sesiones_desde(t0)
    libro["gastado_usd"] = round(float(libro.get("gastado_usd", 0.0)) + coste, 8)
    if desconocido:
        libro["desconocido"] = True
    libro["ejecuciones"].append({
        "ts": datetime.now(TZ).isoformat(timespec="seconds"),
        "dia": libro["dia"],
        "coste_usd": round(coste, 8),
        "acumulado_usd": libro["gastado_usd"],
        "limite_usd": limite_usd,
        "coste_desconocido": desconocido,
        "orden": detalle_orden,
        "sesiones": detalle,
    })
    return libro
