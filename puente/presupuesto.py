#!/usr/bin/env python3
"""Presupuesto diario con control DURANTE la ejecución (issue #3, v3).

Por qué no basta con leer el coste al terminar: si el límite solo se comprueba
al final, una ejecución larga, un reintento o una tarea auxiliar pueden rebasar
el techo antes de que nadie mire. Este módulo implementa las cuatro piezas que
hacen que el techo se respete *mientras* se ejecuta:

  1. RESERVA POR INTENTO. Antes de lanzar nada se reserva un techo `R` para esa
     ejecución. Si `gastado + R > limite`, no se lanza. La reserva es el
     compromiso contable: nunca se autoriza más de lo que queda.
  2. SEGMENTACIÓN. Cada intento (el inicial y cada reintento) es un segmento
     independiente: se liquida su coste real y se vuelve a comprobar el margen
     antes de autorizar el siguiente. Un reintento no es gratis ni invisible.
  3. SESIONES AUXILIARES. Todo lo que Hermes cree dentro de la ventana de un
     segmento —incluidos subagentes y sesiones de otras fuentes— se atribuye a
     ese segmento y consume del mismo presupuesto.
  4. FALLO CERRADO. Coste desconocido o exceso sobre la reserva → el día queda
     bloqueado y se reporta. Un techo que se ignora cuando no se puede medir no
     es un techo.

El gasto se lee de la tabla `sessions` de `~/.hermes/state.db` (fuente
auditable), no de una estimación propia. El día se reinicia a medianoche de
America/New_York.
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

COSTO_CONOCIDO = {"estimated", "actual", "included"}

# Reserva por defecto si la configuración no la fija. Se mide, no se inventa:
# el coste observado de una ejecución acotada del ejecutor ronda los 0,0034 USD
# (ver PRUEBAS.md), así que 0,05 USD es un techo ~15x superior.
RESERVA_POR_DEFECTO = 0.05


def dia_actual() -> str:
    return datetime.now(TZ).date().isoformat()


def libro_vacio() -> dict:
    return {"dia": dia_actual(), "gastado_usd": 0.0, "ejecuciones": [],
            "desconocido": False, "exceso": False, "bloqueado_motivo": None}


def cargar_libro(path: Path) -> dict:
    try:
        libro = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        libro = libro_vacio()
    if libro.get("dia") != dia_actual():
        libro = libro_vacio()
    for k, v in libro_vacio().items():
        libro.setdefault(k, v)
    return libro


def guardar_libro(path: Path, libro: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(libro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def reserva(config: dict) -> float:
    return float(config.get("limites", {}).get("reserva_por_intento_usd", RESERVA_POR_DEFECTO))


def coste_de_sesiones_desde(t0: float) -> tuple[float, list[dict], bool]:
    """Coste de TODAS las sesiones de Hermes iniciadas después de `t0`.

    Incluye subagentes y cualquier otra fuente: si Hermes creó una sesión en la
    ventana, se paga con el mismo presupuesto.
    """
    if not STATE_DB.exists():
        return 0.0, [], True
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
        elif (tin or 0) + (tout or 0) > 0:
            desconocido = True
        detalle.append({
            "sesion": sid, "source": source, "model": model,
            "in_tokens": tin, "out_tokens": tout, "coste_usd": valor,
            "cost_status": status, "cost_source": csource,
        })
    return total, detalle, desconocido


def puede_iniciar(libro: dict, limite_usd: float, res: float) -> tuple[bool, str]:
    """Autoriza (o no) el arranque de UN segmento, reservando su techo."""
    if limite_usd is None or limite_usd <= 0:
        return False, "sin presupuesto asignado"
    if libro.get("desconocido"):
        return False, "consumo previo con coste desconocido: no puede acotarse, requiere reconciliación"
    if libro.get("exceso"):
        return False, f"el día quedó bloqueado por exceso: {libro.get('bloqueado_motivo')}"
    gastado = float(libro.get("gastado_usd", 0.0))
    if gastado + res > limite_usd:
        return False, (f"la reserva de {res:.4f} USD no cabe: "
                       f"gastado {gastado:.6f} + reserva {res:.4f} > límite {limite_usd:.2f}")
    return True, f"reserva de {res:.4f} USD autorizada (gastado {gastado:.6f} de {limite_usd:.2f})"


# alias retrocompatible para la batería anterior
def puede_gastar(libro: dict, limite_usd: float, res: float = 0.0) -> tuple[bool, str]:
    return puede_iniciar(libro, limite_usd, res)


def liquidar(libro: dict, t0: float, detalle_segmento: dict, limite_usd: float, res: float) -> dict:
    """Cierra un segmento: suma el coste REAL y detecta exceso sobre la reserva."""
    coste, detalle, desconocido = coste_de_sesiones_desde(t0)
    libro["gastado_usd"] = round(float(libro.get("gastado_usd", 0.0)) + coste, 8)
    if desconocido:
        libro["desconocido"] = True
        libro.setdefault("bloqueado_motivo", "coste desconocido en un segmento")
    exceso = coste > res + 1e-12
    if exceso:
        libro["exceso"] = True
        libro["bloqueado_motivo"] = (f"el segmento costó {coste:.6f} USD y superó su reserva "
                                     f"de {res:.4f} USD; se bloquea el resto del día")
    segmento = {
        "ts": datetime.now(TZ).isoformat(timespec="seconds"),
        "dia": libro["dia"],
        "coste_usd": round(coste, 8),
        "reserva_usd": res,
        "exceso": exceso,
        "acumulado_usd": libro["gastado_usd"],
        "limite_usd": limite_usd,
        "coste_desconocido": desconocido,
        "detalle": detalle_segmento,
        "sesiones": detalle,
    }
    libro.setdefault("ejecuciones", []).append(segmento)
    return segmento


def restante(libro: dict, limite_usd: float) -> float:
    return max(0.0, float(limite_usd) - float(libro.get("gastado_usd", 0.0)))
