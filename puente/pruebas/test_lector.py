#!/usr/bin/env python3
"""Batería de pruebas del lector del puente (issue #3).

Diseño de las pruebas para respetar los límites del entorno:

  * TODO se ejecuta en un PUENTE_HOME temporal bajo /tmp. La configuración y el
    estado instalados en ~/.hermes/bridge NO se tocan.
  * Nada de procesos concurrentes lanzados con `&`/`xargs`: el bloqueo exclusivo
    se prueba lanzando el lector como subproceso desde un único proceso Python
    que mantiene el flock.
  * Nada de publicar en GitHub: se usa --dry-run salvo en las pruebas que solo
    leen.
  * Nada de reiniciar servicios compartidos: la resiliencia se prueba matando
    una instancia del propio lector, no el daemon de cron del sistema.

Uso:  python3 puente/pruebas/test_lector.py
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from presupuesto import dia_actual as dia_presupuesto  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
LECTOR = RAIZ / "puente" / "lector.py"
TMP = Path("/tmp/puente-test")

REPO = "celestinojbm/entrenamiento-hermes"
ISSUE = 3
CLAVE = f"{REPO}#{ISSUE}"

resultados: list[tuple[str, bool, str]] = []


def preparar(nombre: str, config: dict | None = None, estado: dict | None = None) -> Path:
    home = TMP / nombre
    if home.exists():
        shutil.rmtree(home)
    (home / "logs").mkdir(parents=True)
    base_config = {
        "version": 1,
        "pausa": False,
        "intervalo_minutos": 5,
        "repos_vigilados": [REPO],
        "issues_permitidos": {REPO: [ISSUE]},
        "acciones_permitidas": ["ping"],
        "limites": {"max_ordenes_por_dia": 20, "max_duracion_ejecucion_s": 60,
                    "presupuesto_usd": None, "worker_llm_habilitado": False},
    }
    if config:
        base_config.update(config)
    (home / "config.json").write_text(json.dumps(base_config, ensure_ascii=False, indent=2), encoding="utf-8")
    if estado is not None:
        (home / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    return home


def correr(home: Path, extra: list[str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    env = dict(os.environ, PUENTE_HOME=str(home))
    return subprocess.run(
        [sys.executable, str(LECTOR)] + (extra or []),
        capture_output=True, text=True, env=env, timeout=timeout,
    )


def log_hoy(home: Path) -> str:
    p = home / "logs" / f"{date.today().isoformat()}.log"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def registrar(nombre: str, ok: bool, detalle: str) -> None:
    resultados.append((nombre, ok, detalle))
    print(f"{'OK  ' if ok else 'FALLO'}  {nombre}\n      {detalle}")


# ---------------------------------------------------------------- P1 silencio
def p1_silencio() -> None:
    home = preparar("p1")
    correr(home)                             # primera pasada: inicializa
    c = correr(home)                         # segunda: sin novedades
    registrar("P1 sin novedades -> silencio", c.stdout.strip() == "",
              f"stdout={c.stdout.strip()!r} exit={c.returncode}")


# ------------------------------------------------------------------ P2 pausa
def p2_pausa() -> None:
    home = preparar("p2")
    correr(home)
    (home / "PAUSA").touch()
    c = correr(home, ["--verbose"])
    ok = "PAUSA" in log_hoy(home) and c.returncode == 0
    registrar("P2 fichero PAUSA detiene el sondeo", ok,
              f"exit={c.returncode}; log contiene PAUSA={'PAUSA' in log_hoy(home)}")

    home2 = preparar("p2b", config={"pausa": True})
    c2 = correr(home2, ["--verbose"])
    registrar("P2b config.pausa=true detiene el sondeo",
              "PAUSA" in log_hoy(home2) and c2.returncode == 0,
              f"exit={c2.returncode}")


# ----------------------------------------------------------- P3 límite diario
def p3_limite() -> None:
    # Estado sembrado: el issue ya inicializado y el cursor justo ANTES de la
    # orden de aceptación (id 5640853010), con el contador de hoy ya al tope.
    home = preparar(
        "p3",
        config={"limites": {"max_ordenes_por_dia": 1, "presupuesto_usd": None,
                            "worker_llm_habilitado": False},
                # Se desactiva la firma SOLO en esta prueba para poder aislar la
                # rama del límite diario: en el flujo real la autenticación se
                # comprueba antes y una orden sin firma se rechaza antes de llegar
                # aquí (lo cubre la prueba A2/A3 de la batería del ejecutor).
                "auth": {"requerida": False}},
        estado={"ultimo_comentario_id": {CLAVE: 5640853000},
                "inicializados": [CLAVE], "procesados": [],
                "ordenes": {}, "contadores": {dia_presupuesto(): 1},
                "bloqueos": []},
    )
    c = correr(home, ["--verbose", "--dry-run"])
    est = json.loads((home / "estado.json").read_text(encoding="utf-8"))
    bloqueado = any("límite diario" in b.get("motivo", "") for b in est["bloqueos"])
    # En v2 una orden que supera el límite NO se descarta: queda en cola y por
    # tanto SÍ aparece en `ordenes` (con estado `pendiente`). El criterio correcto
    # de "no se ejecutó" es que ninguna haya llegado a `entregado`.
    no_ejecutada = not any(o.get("estado") == "entregado" for o in est["ordenes"].values())
    encoladas = len(est.get("cola", {}))
    registrar("P3 límite diario bloquea sin ejecutar y encola",
              bloqueado and no_ejecutada and encoladas > 0,
              f"bloqueos={len(est['bloqueos'])} entregadas=0 encoladas={encoladas}")


# ---------------------------------------------------- P4 no procesa histórico
def p4_sin_historico() -> None:
    home = preparar("p4")
    ejecucion = correr(home, ["--verbose"])
    est = json.loads((home / "estado.json").read_text(encoding="utf-8"))
    ok = est["inicializados"] == [CLAVE] and len(est["ordenes"]) == 0
    registrar("P4 primera pasada fija cursor y no procesa histórico", ok,
              f"inicializados={est['inicializados']} ordenes={len(est['ordenes'])} "
              f"cursor={est['ultimo_comentario_id']}")


# ------------------------------------------------------ P5 bloqueo exclusivo
def p5_bloqueo_exclusivo() -> None:
    home = preparar("p5")
    correr(home)  # inicializa
    lock_path = home / ".lock"
    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Con el lock tomado, el lector debe salir en silencio sin sondear.
        c = correr(home, ["--verbose"])
        fcntl.flock(fh, fcntl.LOCK_UN)
    ok = c.returncode == 0 and "otra ejecución está en curso" in log_hoy(home)
    registrar("P5 bloqueo exclusivo: segunda instancia no hace trabajo", ok,
              f"exit={c.returncode}; log={'otra ejecución' in log_hoy(home)}")


# ----------------------------------------------- P6 tolerancia a fallo de API
def p6_fallo_api() -> None:
    home = preparar("p6", config={
        "repos_vigilados": ["celestinojbm/repo-que-no-existe-xyz"],
        "issues_permitidos": {"celestinojbm/repo-que-no-existe-xyz": [999999]},
    })
    c = correr(home, ["--verbose"])
    ok = c.returncode == 0  # no revienta: el cron no debe morir por un fallo de red
    registrar("P6 fallo de API no tumba el lector", ok,
              f"exit={c.returncode}; log={log_hoy(home).strip()[:120]!r}")


# --------------------------------------------- P7 terminar la instancia en curso
def p7_interrupcion() -> None:
    home = preparar("p7")
    correr(home)
    env = dict(os.environ, PUENTE_HOME=str(home))
    # Arrancamos una ejecución y la terminamos a mitad; el flock debe liberarse
    # solo al morir el proceso y la siguiente ejecución debe funcionar.
    p = subprocess.Popen([sys.executable, str(LECTOR), "--verbose"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    time.sleep(0.6)
    p.send_signal(signal.SIGTERM)
    p.wait(timeout=30)
    c2 = correr(home, ["--verbose"])
    ok = c2.returncode == 0
    registrar("P7 matar la ejecución en curso libera el bloqueo", ok,
              f"exit tras interrupción={c2.returncode}")


def main() -> int:
    if not LECTOR.exists():
        print(f"no se encontró el lector en {LECTOR}")
        return 2
    TMP.mkdir(parents=True, exist_ok=True)
    p1_silencio()
    p2_pausa()
    p3_limite()
    p4_sin_historico()
    p5_bloqueo_exclusivo()
    p6_fallo_api()
    p7_interrupcion()

    fallos = [n for n, ok, _ in resultados if not ok]
    print(f"\nresumen: {len(resultados) - len(fallos)}/{len(resultados)} pruebas OK")
    if fallos:
        print("fallos:", ", ".join(fallos))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())