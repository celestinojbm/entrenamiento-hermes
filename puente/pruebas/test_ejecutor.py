#!/usr/bin/env python3
"""Pruebas del ejecutor, la autenticación y el presupuesto (issue #3, v2).

Todo es offline:
  * la firma HMAC se prueba como función pura;
  * el presupuesto se prueba contra una **base de sesiones falsa** con el mismo
    esquema que `~/.hermes/state.db` (así se verifica la lectura de coste real sin
    gastar un céntimo);
  * las publicaciones fallidas se prueban con un **transporte falso** que simula
    fallos y éxitos, sin tocar GitHub.

Uso: python3 puente/pruebas/test_ejecutor.py
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "puente"))

import auth  # noqa: E402
import presupuesto  # noqa: E402

TMP = Path("/tmp/puente-test-ejecutor")
resultados: list[tuple[str, bool, str]] = []


def registrar(nombre: str, ok: bool, detalle: str) -> None:
    resultados.append((nombre, ok, detalle))
    print(f"{'OK  ' if ok else 'FALLO'}  {nombre}\n      {detalle}")


# ------------------------------------------------------------------ firma HMAC
def t_firma() -> None:
    home = TMP / "auth"
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True)
    ruta = auth.ruta_secreto(home)
    creado = auth.init_secreto(ruta)
    secreto = auth.leer_secreto(ruta)
    registrar("A1 init crea el secreto en chmod 600",
              creado and secreto is not None and oct(ruta.stat().st_mode)[-3:] == "600",
              f"creado={creado} permisos={oct(ruta.stat().st_mode)[-3:]}")

    orden = {"id_orden": "o1", "tipo": "orden", "accion": "ping",
             "parametros": {}, "emitida_en": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    valida, motivo = auth.verificar(orden, secreto)
    registrar("A2 orden sin firma -> rechazada", not valida, f"motivo={motivo!r}")

    orden["firma"] = "0" * 64
    valida, motivo = auth.verificar(orden, secreto)
    registrar("A3 firma inválida -> rechazada", not valida, f"motivo={motivo!r}")

    orden["firma"] = auth.firmar(orden, secreto)
    valida, motivo = auth.verificar(orden, secreto)
    registrar("A4 firma válida -> aceptada", valida, f"motivo={motivo!r}")

    # manipulación del contenido tras firmar
    manip = dict(orden, accion="tarea_local")
    valida, motivo = auth.verificar(manip, secreto)
    registrar("A5 cambiar la acción invalida la firma", not valida, f"motivo={motivo!r}")

    # caducidad
    viejo = dict(orden, emitida_en=(datetime.now(timezone.utc) - timedelta(hours=30)).isoformat(timespec="seconds"))
    viejo["firma"] = auth.firmar(viejo, secreto)
    valida, motivo = auth.verificar(viejo, secreto)
    registrar("A6 orden caducada -> rechazada", not valida, f"motivo={motivo!r}")

    # sin secreto provisionado = fallo cerrado
    valida, motivo = auth.verificar(orden, None)
    registrar("A7 sin secreto -> fallo cerrado", not valida, f"motivo={motivo!r}")

    # el orden de las claves del JSON no debe cambiar la firma (serialización canónica)
    reordenado = {k: orden[k] for k in reversed(list(orden.keys()))}
    registrar("A8 serialización canónica estable ante reordenación",
              auth.firmar(reordenado, secreto) == orden["firma"],
              "misma firma con las claves en otro orden")


# --------------------------------------------------------------- presupuesto
def _db_falsa(path: Path, filas: list[dict]) -> None:
    con = sqlite3.connect(path)
    con.execute("""create table sessions (id text, source text, model text, started_at real,
                   input_tokens integer, output_tokens integer, estimated_cost_usd real,
                   actual_cost_usd real, cost_status text, cost_source text)""")
    for f in filas:
        con.execute("insert into sessions values (?,?,?,?,?,?,?,?,?,?)",
                    (f["id"], f.get("source", "cli"), f.get("model", "m"), f["started_at"],
                     f.get("tin", 100), f.get("tout", 10), f.get("est"), f.get("act"),
                     f.get("status"), f.get("csource", "provider_models_api")))
    con.commit()
    con.close()


def t_presupuesto() -> None:
    if TMP.exists() and (TMP / "presupuesto").exists():
        shutil.rmtree(TMP / "presupuesto")
    base = TMP / "presupuesto"
    base.mkdir(parents=True, exist_ok=True)

    db = base / "state.db"
    t0 = time.time() - 60
    _db_falsa(db, [
        {"id": "s1", "started_at": t0, "est": 0.25, "status": "estimated"},
        {"id": "s2", "started_at": t0 + 1, "est": 0.10, "status": "estimated"},
    ])
    presupuesto.STATE_DB = db

    libro = presupuesto.libro_vacio()
    registrar("B1 el día presupuestario usa America/New_York",
              libro["dia"] == datetime.now(presupuesto.TZ).date().isoformat(),
              f"dia={libro['dia']} tz={presupuesto.TZ}")

    coste, detalle, desconocido = presupuesto.coste_de_sesiones_desde(t0)
    registrar("B2 lee el coste real de la base de sesiones",
              abs(coste - 0.35) < 1e-9 and not desconocido,
              f"coste={coste} sesiones={len(detalle)}")

    presupuesto.registrar(libro, t0, {"accion": "tarea_local"}, 5.0)
    registrar("B3 acumula el gasto en el libro", abs(libro["gastado_usd"] - 0.35) < 1e-9,
              f"gastado={libro['gastado_usd']}")

    ok, motivo = presupuesto.puede_gastar(libro, 5.0)
    registrar("B4 con 4.65 USD restantes se puede gastar", ok, motivo)

    libro["gastado_usd"] = 5.0
    ok, motivo = presupuesto.puede_gastar(libro, 5.0)
    registrar("B5 con el presupuesto agotado NO se puede gastar", not ok, motivo)

    # reinicio del día
    guardar = base / "presupuesto.json"
    viejo = {"dia": "2000-01-01", "gastado_usd": 4.99, "ejecuciones": [], "desconocido": False}
    presupuesto.guardar_libro(guardar, viejo)
    recargado = presupuesto.cargar_libro(guardar)
    registrar("B6 el gasto se reinicia al cambiar el día (America/New_York)",
              recargado["gastado_usd"] == 0.0 and recargado["dia"] == presupuesto.dia_actual(),
              f"dia={recargado['dia']} gastado={recargado['gastado_usd']}")

    # coste desconocido -> fallo cerrado
    db2 = base / "state2.db"
    _db_falsa(db2, [{"id": "s9", "started_at": time.time(), "tin": 1000, "tout": 100,
                     "est": None, "act": None, "status": None}])
    presupuesto.STATE_DB = db2
    libro2 = presupuesto.libro_vacio()
    presupuesto.registrar(libro2, time.time() - 10, {"accion": "tarea_local"}, 5.0)
    ok, motivo = presupuesto.puede_gastar(libro2, 5.0)
    registrar("B7 coste desconocido -> fallo cerrado (no se puede acotar)", not ok,
              f"desconocido={libro2['desconocido']} motivo={motivo}")

    # incluido en el plan = coste conocido y cero
    db3 = base / "state3.db"
    _db_falsa(db3, [{"id": "s10", "started_at": time.time(), "est": 0.0, "status": "included", "csource": "none"}])
    presupuesto.STATE_DB = db3
    coste3, _, desc3 = presupuesto.coste_de_sesiones_desde(time.time() - 10)
    registrar("B8 coste 'included' cuenta como 0 conocido", coste3 == 0.0 and not desc3,
              f"coste={coste3} desconocido={desc3}")


# ------------------------------------------- transporte falso para publicaciones
class TransporteFalso:
    def __init__(self, fallar_primeras: int = 0, ya_existe: bool = False):
        self.publicados: list[str] = []
        self.intentos = 0
        self.fallar_primeras = fallar_primeras
        self.ya_existe = ya_existe

    def api(self, endpoint, metodo="GET", cuerpo=None, paginar=False):
        if metodo == "GET":
            if self.ya_existe:
                return [{"id": 1, "body": "algo\n\n<!-- hermes-puente:v1 pub=p1-a -->"}]
            return []
        self.intentos += 1
        if self.intentos <= self.fallar_primeras:
            raise RuntimeError("fallo simulado de red")
        self.publicados.append(cuerpo["body"])
        return {"id": 999}


def t_publicaciones() -> None:
    import lector

    # C1: fallo -> queda pendiente, no se pierde
    estado = {"publicaciones_pendientes": []}
    lector.encolar_publicacion(estado, "r/r", 1, "p1-a", "acuse")
    t = TransporteFalso(fallar_primeras=1)
    lector.vaciar_publicaciones(t, estado, False, False)
    pendiente_tras_fallo = len(estado["publicaciones_pendientes"]) == 1
    # C2: siguiente pasada lo reintenta y lo publica
    t2 = TransporteFalso(fallar_primeras=0)
    lector.vaciar_publicaciones(t2, estado, False, False)
    registrar("C1/C2 publicación fallida se reintenta y no se pierde",
              pendiente_tras_fallo and len(estado["publicaciones_pendientes"]) == 0 and len(t2.publicados) == 1,
              f"pendientes tras fallo={pendiente_tras_fallo} publicados={len(t2.publicados)}")

    # C3: si ya existe en GitHub (marca), NO se vuelve a publicar
    estado3 = {"publicaciones_pendientes": []}
    lector.encolar_publicacion(estado3, "r/r", 1, "p1-a", "acuse")
    t3 = TransporteFalso(ya_existe=True)
    lector.vaciar_publicaciones(t3, estado3, False, False)
    registrar("C3 reconciliación: no duplica una publicación ya presente",
              len(t3.publicados) == 0 and len(estado3["publicaciones_pendientes"]) == 0,
              f"publicados={len(t3.publicados)} pendientes={len(estado3['publicaciones_pendientes'])}")

    # C4: acuse y resultado se encolan ambos
    estado4 = {"publicaciones_pendientes": []}
    lector.encolar_publicacion(estado4, "r/r", 1, "ox-a", "acuse")
    lector.encolar_publicacion(estado4, "r/r", 1, "ox-r", "resultado")
    registrar("C4 acuse y resultado van al buzón de salida",
              len(estado4["publicaciones_pendientes"]) == 2,
              f"encoladas={len(estado4['publicaciones_pendientes'])}")


# ------------------------------------------------ recuperación tras interrupción
def t_interrupcion() -> None:
    import lector

    # D1: una orden reclamada y nunca completada NO se reintenta
    estado = {"ordenes": {"ord-x": {"id_orden": "ord-x", "estado": "en_curso",
                                    "reclamada_ts": "2026-09-11T00:00:00+00:00"}},
              "bloqueos": []}
    salidas: list[str] = []
    lector.reconciliar_interrumpidas(estado, salidas)
    reg = estado["ordenes"]["ord-x"]
    registrar("D1 orden interrumpida queda BLOQUEADA, no se reintenta",
              reg["estado"] == "bloqueado_interrumpido" and len(estado["bloqueos"]) == 1,
              f"estado={reg['estado']} bloqueos={len(estado['bloqueos'])}")

    # D2: el reclamo se persiste ANTES de ejecutar
    src = (RAIZ / "puente" / "lector.py").read_text(encoding="utf-8")
    pos_guardar = src.find("guardar_json_atomico(ESTADO_PATH, estado)          # <-- antes de ejecutar")
    pos_ejecutar = src.find("res = ejecutar_accion(accion, config, libro, estado)")
    registrar("D2 el estado se persiste antes de ejecutar",
              0 < pos_guardar < pos_ejecutar,
              f"posición guardado={pos_guardar} < posición ejecución={pos_ejecutar}")


# ------------------------------------------------------------------- cola
def t_cola() -> None:
    import lector

    orden = {"id_orden": "ord-cola", "tipo": "orden", "accion": "tarea_local", "parametros": {}}
    estado = {"cola": {}, "ordenes": {}, "bloqueos": []}
    salidas: list[str] = []
    lector._encolar(estado, orden, "123", "r/r", 3, "presupuesto agotado", salidas, "2026-09-11T00:00:00+00:00")
    registrar("E1 la orden que supera el límite se ENCOLA (no se descarta)",
              "ord-cola" in estado["cola"] and estado["cola"]["ord-cola"]["repo"] == "r/r",
              f"cola={list(estado['cola'].keys())} repo={estado['cola']['ord-cola']['repo']}")

    # el día cambia -> se retoma
    estado["cola"]["ord-cola"]["dia_cola"] = "2000-01-01"
    procesados: list[str] = []

    class T(TransporteFalso):
        def api(self, endpoint, metodo="GET", cuerpo=None, paginar=False):
            if metodo == "GET":
                return []
            return {"id": 1}

    original = lector.procesar_orden
    lector.procesar_orden = lambda *a, **k: procesados.append(a[4]["id_orden"]) or {}
    try:
        lector.retomar_cola(T(), {"acciones_permitidas": ["ping"]}, estado, presupuesto.libro_vacio(),
                            [], False)
    finally:
        lector.procesar_orden = original
    registrar("E2 al día siguiente la orden encolada se retoma",
              procesados == ["ord-cola"] and "ord-cola" not in estado["cola"],
              f"retomadas={procesados} cola_restante={list(estado['cola'].keys())}")


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PUENTE_HOME", str(TMP))
    t_firma()
    t_presupuesto()
    t_publicaciones()
    t_interrupcion()
    t_cola()
    fallos = [n for n, ok, _ in resultados if not ok]
    print(f"\nresumen: {len(resultados) - len(fallos)}/{len(resultados)} pruebas OK")
    if fallos:
        print("fallos:", ", ".join(fallos))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
