#!/usr/bin/env python3
"""Pruebas del control de gasto DURANTE la ejecución (issue #3, v3).

Lo que hay que demostrar no es "leo el coste al terminar", sino que **ninguna
combinación de intentos, reintentos y sesiones auxiliares puede rebasar el
techo**.

Método: se coloca en el PATH un `hermes` **falso** que escribe en una base de
sesiones falsa (mismo esquema que la real) el coste que le indiquemos y termina
con el código que le pidamos. Así se ejercita el bucle real del lector
—autorización por segmento, liquidación, reintentos— sin gastar dinero.

Uso: python3 puente/pruebas/test_presupuesto.py
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "puente"))

TMP = Path("/tmp/puente-test-presupuesto")
resultados: list[tuple[str, bool, str]] = []

FAKE_HERMES = """#!/usr/bin/env python3
import os, sqlite3, time
db = os.environ["HERMES_STATE_DB"]
coste = float(os.environ.get("FAKE_COSTE", "0.01"))
estado = os.environ.get("FAKE_ESTADO", "estimated")
con = sqlite3.connect(db)
con.execute("insert into sessions (id, source, model, started_at, input_tokens, output_tokens,"
            " estimated_cost_usd, actual_cost_usd, cost_status, cost_source) values (?,?,?,?,?,?,?,?,?,?)",
            (f"s{time.time_ns()}", os.environ.get("FAKE_SOURCE", "cli"), "modelo-falso", time.time(),
             int(os.environ.get("FAKE_IN", "1000")), int(os.environ.get("FAKE_OUT", "100")),
             coste if estado != "none" else None, None, None if estado == "none" else estado, "fake"))
con.commit(); con.close()
print("salida falsa del ejecutor")
raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))
"""


def registrar(nombre: str, ok: bool, detalle: str) -> None:
    resultados.append((nombre, ok, detalle))
    print(f"{'OK  ' if ok else 'FALLO'}  {nombre}\n      {detalle}")


def montar(nombre: str, limite: float, reserva: float, max_intentos: int = 3) -> tuple[Path, Path, Path]:
    """Prepara HOME del puente, binario hermes falso y base de sesiones falsa."""
    base = TMP / nombre
    if base.exists():
        shutil.rmtree(base)
    (base / "home").mkdir(parents=True)
    (base / "bin").mkdir()
    db = base / "state.db"
    con = sqlite3.connect(db)
    con.execute("""create table sessions (id text, source text, model text, started_at real,
                   input_tokens integer, output_tokens integer, estimated_cost_usd real,
                   actual_cost_usd real, cost_status text, cost_source text)""")
    con.commit()
    con.close()

    fake = base / "bin" / "hermes"
    fake.write_text(FAKE_HERMES, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

    config = {
        "version": 3,
        "acciones_permitidas": ["ping", "tarea_local"],
        "auth": {"requerida": False},
        "limites": {
            "presupuesto_usd": limite,
            "reserva_por_intento_usd": reserva,
            "max_intentos_por_orden": max_intentos,
            "max_turns_ejecucion": 2,
            "max_duracion_ejecucion_s": 30,
            "worker_llm_habilitado": True,
        },
    }
    (base / "home" / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return base / "home", fake.parent, db


def ejecutar(base: Path, bin_dir: Path, db: Path, extra_env: dict | None = None) -> tuple[dict, dict]:
    """Ejecuta la acción `tarea_local` del lector con el entorno falso."""
    import importlib

    import presupuesto as p_mod
    # El orden importa: el módulo lee HERMES_STATE_DB en su nivel superior, así
    # que hay que fijar el entorno ANTES de recargarlo. Recargar después lo
    # reseteaba a la ruta por defecto y las pruebas leían la base real.
    os.environ["HERMES_STATE_DB"] = str(db)
    importlib.reload(p_mod)
    import lector
    lector.presupuesto = p_mod

    os.environ["PATH"] = f"{bin_dir}:{os.environ['PATH']}"
    for k, v in (extra_env or {}).items():
        os.environ[k] = str(v)

    libro = p_mod.libro_vacio()
    config = json.loads((base / "config.json").read_text(encoding="utf-8"))
    estado = {"ordenes": {}, "bloqueos": [], "cola": {}}
    res = lector.ejecutar_accion("tarea_local", config, libro, estado)
    return res, libro


# --------------------------------------------------------------- pruebas
def f1_reserva_no_cabe() -> None:
    base, bin_dir, db = montar("f1", limite=0.08, reserva=0.05)
    os.environ.update(FAKE_COSTE="0.01", FAKE_EXIT="0")
    res, libro = ejecutar(base, bin_dir, db)
    # 1er intento: 0 + 0.05 <= 0.08 → autorizado. Gasta 0.01. 2º: 0.01+0.05 <= 0.08 → autorizado.
    # pero el 1º tiene exit 0 → termina. Lo que se comprueba es que no se lanzó más de lo autorizado.
    ok = res["ejecutada"] and libro["gastado_usd"] <= 0.08
    registrar("F1 la reserva se comprueba antes de cada intento",
              ok, f"gastado={libro['gastado_usd']} <= limite=0.08, intentos={len(res['resultado']['intentos'])}")


def f2_reintentos_no_rebasan() -> None:
    """Con reintentos forzados, el total autorizado nunca pasa del techo."""
    base, bin_dir, db = montar("f2", limite=0.025, reserva=0.01, max_intentos=5)
    os.environ.update(FAKE_COSTE="0.008", FAKE_EXIT="1")   # siempre falla → reintenta
    res, libro = ejecutar(base, bin_dir, db)
    intentos = res["resultado"]["intentos"]
    autorizados = [i for i in intentos if i.get("autorizado")]
    ok = (not res["ejecutada"] and libro["gastado_usd"] <= 0.025
          and len(autorizados) < 5 and any(not i.get("autorizado") for i in intentos))
    registrar("F2 los reintentos se detienen antes de rebasar el techo", ok,
              f"gastado={libro['gastado_usd']:.4f} <= 0.0250 | intentos={len(intentos)} "
              f"autorizados={len(autorizados)} | último bloqueado: "
              f"{intentos[-1].get('motivo', 'n/a')[:60]}")


def f3_sesiones_auxiliares() -> None:
    """Una sesión de subagente creada en la ventana cuenta contra el presupuesto."""
    base, bin_dir, db = montar("f3", limite=1.0, reserva=0.05)
    # el hermes falso inserta DOS filas: la suya y una auxiliar (subagente)
    fake = (bin_dir / "hermes")
    fake.write_text(FAKE_HERMES.replace(
        'print("salida falsa del ejecutor")',
        'c2 = sqlite3.connect(db); c2.execute("insert into sessions (id, source, model, started_at,'
        ' input_tokens, output_tokens, estimated_cost_usd, actual_cost_usd, cost_status, cost_source)'
        ' values (?,?,?,?,?,?,?,?,?,?)", ("aux-"+str(time.time_ns()), "subagent", "modelo-falso",'
        ' time.time(), 5000, 500, 0.30, None, "estimated", "fake")); c2.commit(); c2.close()\n'
        'print("salida falsa del ejecutor")'), encoding="utf-8")
    fake.chmod(0o755)
    os.environ.update(FAKE_COSTE="0.01", FAKE_EXIT="0")
    res, libro = ejecutar(base, bin_dir, db)
    sesiones = libro["ejecuciones"][0]["sesiones"] if libro["ejecuciones"] else []
    ok = abs(libro["gastado_usd"] - 0.31) < 1e-9 and any(s["source"] == "subagent" for s in sesiones)
    registrar("F3 las sesiones auxiliares de la ventana se atribuyen al segmento", ok,
              f"gastado={libro['gastado_usd']} (0.01 + 0.30 auxiliar) sesiones={len(sesiones)}")


def f4_exceso_bloquea() -> None:
    """Si un segmento supera su reserva, el día queda bloqueado."""
    base, bin_dir, db = montar("f4", limite=5.0, reserva=0.05)
    os.environ.update(FAKE_COSTE="0.40", FAKE_EXIT="1")   # supera la reserva de 0.05
    res, libro = ejecutar(base, bin_dir, db)
    ok = libro["exceso"] is True and libro.get("bloqueado_motivo")
    registrar("F4 el exceso sobre la reserva bloquea el día", ok,
              f"exceso={libro['exceso']} motivo={str(libro.get('bloqueado_motivo'))[:70]}")

    # y con el día bloqueado, no se autoriza nada más
    import presupuesto as p
    autorizado, motivo = p.puede_iniciar(libro, 5.0, 0.05)
    registrar("F4b con exceso registrado no se autoriza ningún intento más",
              not autorizado, motivo[:80])


def f5_coste_desconocido() -> None:
    base, bin_dir, db = montar("f5", limite=5.0, reserva=0.05)
    os.environ.update(FAKE_COSTE="0.01", FAKE_ESTADO="none", FAKE_EXIT="0")
    res, libro = ejecutar(base, bin_dir, db)
    import presupuesto as p
    autorizado, motivo = p.puede_iniciar(libro, 5.0, 0.05)
    registrar("F5 coste desconocido → fallo cerrado", not autorizado and libro["desconocido"],
              f"desconocido={libro['desconocido']} | {motivo[:70]}")
    os.environ.pop("FAKE_ESTADO", None)


def f6_presupuesto_agotado_no_lanza() -> None:
    """Con el presupuesto ya consumido, el ejecutor ni siquiera arranca."""
    base, bin_dir, db = montar("f6", limite=0.02, reserva=0.05)
    os.environ.update(FAKE_COSTE="0.01", FAKE_EXIT="0")
    res, libro = ejecutar(base, bin_dir, db)
    intentos = res["resultado"]["intentos"]
    ok = (not res["ejecutada"] and len(intentos) == 1 and not intentos[0].get("autorizado")
          and libro["gastado_usd"] == 0.0)
    registrar("F6 sin margen para la reserva no se lanza ni un intento", ok,
              f"intentos={len(intentos)} autorizado={intentos[0].get('autorizado')} gastado={libro['gastado_usd']}")


def f7_tope_estructural() -> None:
    """El ejecutor pasa tope de turnos y de tiempo al proceso hijo."""
    src = (RAIZ / "puente" / "lector.py").read_text(encoding="utf-8")
    ok = ("HERMES_MAX_ITERATIONS" in src and "HERMES_AGENT_TIMEOUT" in src
          and "killpg" in src and "start_new_session=True" in src)
    registrar("F7 tope de turnos + plazo + corte duro del grupo de procesos", ok,
              "HERMES_MAX_ITERATIONS, HERMES_AGENT_TIMEOUT, start_new_session, killpg presentes")


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    original = dict(os.environ)
    try:
        f1_reserva_no_cabe()
        f2_reintentos_no_rebasan()
        f3_sesiones_auxiliares()
        f4_exceso_bloquea()
        f5_coste_desconocido()
        f6_presupuesto_agotado_no_lanza()
        f7_tope_estructural()
    finally:
        for k in ("FAKE_COSTE", "FAKE_EXIT", "FAKE_ESTADO", "FAKE_SOURCE", "FAKE_IN", "FAKE_OUT"):
            os.environ.pop(k, None)
        os.environ.clear()
        os.environ.update(original)

    fallos = [n for n, ok, _ in resultados if not ok]
    print(f"\nresumen: {len(resultados) - len(fallos)}/{len(resultados)} pruebas OK")
    if fallos:
        print("fallos:", ", ".join(fallos))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
