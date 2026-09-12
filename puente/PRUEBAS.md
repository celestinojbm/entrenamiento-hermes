# Pruebas del puente — resultados reales

Fichero de evidencia. Todo lo de aquí es salida de ejecución, no descripción.

---

## 1. Batería local

Ejecutable: `python3 puente/pruebas/test_lector.py`

Diseño que respeta los límites del entorno:

- **Todo en un `PUENTE_HOME` temporal** bajo `/tmp/puente-test`. La configuración
  y el estado **instalados** en `~/.hermes/bridge` no se tocan.
- **Sin procesos concurrentes por shell**: el bloqueo exclusivo se prueba
  lanzando el lector como subproceso desde un único proceso Python que mantiene el
  `flock` (nada de `&`, nada de `xargs -P`).
- **Sin publicar en GitHub**: `--dry-run` en las pruebas que podrían escribir.
- **Sin reiniciar servicios compartidos**: la resiliencia se prueba interrumpiendo
  una ejecución del propio lector, no el daemon de cron del sistema.

### Resultado

```
OK    P1 sin novedades -> silencio
      stdout='' exit=0
OK    P2 fichero PAUSA detiene el sondeo
      exit=0; log contiene PAUSA=True
OK    P2b config.pausa=true detiene el sondeo
      exit=0
OK    P3 límite diario bloquea sin ejecutar
      bloqueos=4 ordenes=0
OK    P4 primera pasada fija cursor y no procesa histórico
      inicializados=['celestinojbm/entrenamiento-hermes#3'] ordenes=0 cursor={'celestinojbm/entrenamiento-hermes#3': 5640863507}
OK    P5 bloqueo exclusivo: segunda instancia no hace trabajo
      exit=0; log=True
OK    P6 fallo de API no tumba el lector
      exit=0; log='error consultando celestinojbm/repo-que-no-existe-xyz#999999: gh fallo (1): gh: Not Found (HTTP 404)'
OK    P7 matar la ejecución en curso libera el bloqueo
      exit tras interrupción=0

resumen: 8/8 pruebas OK
```

Qué prueba cada una:

| # | Qué demuestra |
|---|---|
| P1 | Sin novedades el lector **no imprime nada**: es el patrón watchdog que encaja con `hermes cron --no-agent` y con cron del sistema sin ensuciar GitHub |
| P2 / P2b | Las dos formas de pausa (fichero `PAUSA` y `config.pausa`) detienen el sondeo sin desinstalar |
| P3 | Alcanzado el límite diario, la orden **no se ejecuta** y queda bloqueo visible |
| P4 | La primera pasada fija el cursor y **no procesa el histórico** |
| P5 | Con el bloqueo tomado, una segunda instancia sale sin trabajar |
| P6 | Un fallo de la API de GitHub no tumba el proceso (el cron no muere por un 404) |
| P7 | Interrumpir una ejecución en curso libera el `flock` y la siguiente funciona |

### Bug encontrado y corregido durante las pruebas

La primera versión consideraba "primera ejecución" si **no había cursor**. En un
issue **sin comentarios** el cursor no se crea, así que cada arranque se creía el
primero y **se habría saltado la primera orden real**. Se corrigió añadiendo una
marca explícita de inicialización por issue (`estado.inicializados`). Lo detectó la
prueba P1/P4, no una lectura del código.

---

## 2. Circuito de aceptación, con órdenes reales en GitHub

Órdenes publicadas en la issue #3 y procesadas por el lector:

| Caso | Comentario de la orden | Acuse | Resultado | Comportamiento |
|---|---|---|---|---|
| Orden válida | [5640853010](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640853010) | [5640853202](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640853202) | [5640853317](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640853317) | `entregado`; el acuse declara "Origen autenticado: **no**" |
| Duplicado (mismo `id_orden`) | [5640855026](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640855026) | — | — | `ya procesada; duplicado ignorado`. El contador quedó en **1** |
| Orden inválida | [5640863061](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863061) | — | — | `JSON no parseable dentro del bloque hermes-order` → bloqueo registrado |
| Acción no permitida (`shell`) | [5640863181](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863181) | [5640863376](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863376) | [5640863507](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863507) | `pendiente_confirmacion_humana`; **no ejecutada** |

Registro local resultante:

```json
{
  "inicializados": ["celestinojbm/entrenamiento-hermes#3"],
  "ordenes": ["ord-aceptacion-2026-09-11-001", "ord-noautorizada-001"],
  "contadores": {"2026-09-11": 1},
  "bloqueos": 1
}
```

---

## 3. El lector dispara por su cuenta (cron), sin el chat

Prueba de que **cerrar la conversación no mata el lector**: el proceso no es hijo
de la sesión, es una entrada de cron.

```
$ crontab -l | grep lector.py
*/5 * * * * PUENTE_HOME=/home/celestinojbm/.hermes/bridge /usr/bin/python3 \
  /home/celestinojbm/h014-work/repos/entrenamiento-hermes/puente/lector.py \
  >> /home/celestinojbm/.hermes/bridge/logs/cron.out 2>&1

$ systemctl is-active cron
active
```

Marcas reales en `~/.hermes/bridge/logs/2026-09-11.log`, a intervalos exactos de
cinco minutos (extracto):

```
2026-09-12T01:50:02+00:00 ... 0 comentario(s) nuevo(s) tras cursor=5640863507
2026-09-12T01:55:01+00:00 ... 0 comentario(s) nuevo(s) tras cursor=5640863507
2026-09-12T02:00:02+00:00 ... 0 comentario(s) nuevo(s) tras cursor=5640863507
...
2026-09-12T02:45:02+00:00 ... 0 comentario(s) nuevo(s) tras cursor=5640863507
```

`cron.out` está **vacío** (0 bytes): confirma que el lector no imprime nada cuando
no hay novedades — ni heartbeats ruidosos ni comentarios en GitHub.

---

## 4. Estado del ejecutor automático

```json
{
  "max_ordenes_por_dia": 20,
  "max_duracion_ejecucion_s": 60,
  "presupuesto_usd": null,
  "worker_llm_habilitado": false,
  "worker_pausado_motivo": "El worker de trabajo con LLM queda EN PAUSA hasta publicar
    el mecanismo de límite y recibir un presupuesto explícito (issue #3, punto 8).
    El lector no usa LLM."
}
```

El lector **no consume tokens**: no invoca ningún modelo. El ejecutor de trabajo
con LLM sigue deshabilitado y así se queda hasta que exista presupuesto explícito.

---

## 5. Bloqueo por política de seguridad, registrado

Durante la ejecución de la batería, **una acción fue bloqueada por la política de
seguridad del entorno** y no se reintentó ni se eludió:

- **Acción exacta:** un único comando que (a) creaba y borraba el fichero
  `~/.hermes/bridge/PAUSA`, (b) modificaba `max_ordenes_por_dia` en la
  configuración **instalada**, y (c) lanzaba dos instancias concurrentes con
  `xargs -P2`.
- **Motivo:** la política del entorno denegó el comando (modificación de
  configuración instalada + lanzamiento de procesos por shell).
- **Qué se hizo en su lugar:** las mismas pruebas, **en un `PUENTE_HOME` temporal**
  y sin concurrencia por shell (subproceso único con `flock` mantenido desde
  Python). Resultado: 8/8.
- **Nada se desactivó ni se sorteó.** No se tocó ningún ajuste de seguridad.

---

## 6. Lo que NO se probó (y por qué)

| Escenario | Motivo |
|---|---|
| PC suspendido / apagado, reinicio de Windows | No se puede provocar sin cortar la sesión del usuario. **No se promete 24/7 en WSL** |
| Sin red | Solo se probó un 404 de recurso inexistente, no una caída de conectividad |
| Reinicio del daemon `cron.service` | Servicio **preexistente y compartido**: reiniciarlo afectaría a otros usos de la máquina. Se probó en su lugar la interrupción de una ejecución del lector |
| Ejecución de trabajo real con LLM | Pausada por diseño, sin presupuesto |
| Comentario de estado único actualizable (heartbeat) | No implementado todavía; el campo `comentario_estado` existe en la config sin uso |
| Autenticación de origen | No implementada: es la razón por la que solo hay acciones inocuas |
