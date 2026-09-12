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

---

# v2 — autenticación, presupuesto, recuperación y cola

Baterías completas: `puente/pruebas/test_lector.py` y `puente/pruebas/test_ejecutor.py`.
Salidas crudas en `puente/pruebas/salidas/`.

## Batería 1 — lector (regresión v2)

```
OK    P1 sin novedades -> silencio
      stdout='' exit=0
OK    P2 fichero PAUSA detiene el sondeo
      exit=0; log contiene PAUSA=True
OK    P2b config.pausa=true detiene el sondeo
      exit=0
OK    P3 límite diario bloquea sin ejecutar y encola
      bloqueos=4 entregadas=0 encoladas=3
OK    P4 primera pasada fija cursor y no procesa histórico
      inicializados=['celestinojbm/entrenamiento-hermes#3'] ordenes=0 cursor={'celestinojbm/entrenamiento-hermes#3': 5643112774}
OK    P5 bloqueo exclusivo: segunda instancia no hace trabajo
      exit=0; log=True
OK    P6 fallo de API no tumba el lector
      exit=0; log='2026-09-12T03:21:14+00:00 error consultando celestinojbm/repo-que-no-existe-xyz#999999: gh fallo (1): gh: Not Found (HTT'
OK    P7 matar la ejecución en curso libera el bloqueo
      exit tras interrupción=0

resumen: 8/8 pruebas OK
```

## Batería 2 — firma, presupuesto, recuperación y cola (offline)

```
OK    A1 init crea el secreto en chmod 600
      creado=True permisos=600
OK    A2 orden sin firma -> rechazada
      motivo='la orden no trae firma'
OK    A3 firma inválida -> rechazada
      motivo='firma inválida'
OK    A4 firma válida -> aceptada
      motivo='firma válida'
OK    A5 cambiar la acción invalida la firma
      motivo='firma inválida'
OK    A6 orden caducada -> rechazada
      motivo='orden caducada (más de 24 h)'
OK    A7 sin secreto -> fallo cerrado
      motivo='no hay secreto local provisionado: no puede autenticarse el origen'
OK    A8 serialización canónica estable ante reordenación
      misma firma con las claves en otro orden
OK    B1 el día presupuestario usa America/New_York
      dia=2026-09-11 tz=America/New_York
OK    B2 lee el coste real de la base de sesiones
      coste=0.35 sesiones=2
OK    B3 acumula el gasto en el libro
      gastado=0.35
OK    B4 con 4.65 USD restantes se puede gastar
      restante 4.650000 USD de 5.00
OK    B5 con el presupuesto agotado NO se puede gastar
      presupuesto diario agotado (5.000000 de 5.00 USD)
OK    B6 el gasto se reinicia al cambiar el día (America/New_York)
      dia=2026-09-11 gastado=0.0
OK    B7 coste desconocido -> fallo cerrado (no se puede acotar)
      desconocido=True motivo=hay consumo previo con coste desconocido: no puede acotarse, requiere reconciliación
OK    B8 coste 'included' cuenta como 0 conocido
      coste=0.0 desconocido=False
2026-09-12T03:21:16+00:00 publicación p1-a falló (intento 1): fallo simulado de red
OK    C1/C2 publicación fallida se reintenta y no se pierde
      pendientes tras fallo=True publicados=1
OK    C3 reconciliación: no duplica una publicación ya presente
      publicados=0 pendientes=0
OK    C4 acuse y resultado van al buzón de salida
      encoladas=2
OK    D1 orden interrumpida queda BLOQUEADA, no se reintenta
      estado=bloqueado_interrumpido bloqueos=1
OK    D2 el estado se persiste antes de ejecutar
      posición guardado=14252 < posición ejecución=14406
OK    E1 la orden que supera el límite se ENCOLA (no se descarta)
      cola=['ord-cola'] repo=r/r
OK    E2 al día siguiente la orden encolada se retoma
      retomadas=['ord-cola'] cola_restante=[]

resumen: 23/23 pruebas OK
```

Detalle de lo que cubre la batería 2:

| # | Qué demuestra |
|---|---|
| A1–A8 | Firma HMAC: sin firma se rechaza · firma inválida se rechaza · firma válida se acepta · **cambiar la acción invalida la firma** · orden caducada se rechaza · sin secreto → fallo cerrado · serialización canónica estable |
| B1–B8 | Presupuesto: día por America/New_York · lee el **coste real** de la base de sesiones · acumula · agotado → no se puede gastar · **el gasto se reinicia al cambiar el día** · **coste desconocido → fallo cerrado** · coste `included` cuenta como 0 conocido |
| C1–C4 | Recuperación de publicaciones: un fallo no pierde el envío · se reintenta · **no duplica una publicación ya presente** · acuse y resultado van al buzón |
| D1–D2 | Recuperación: una orden interrumpida queda **bloqueada y no se reintenta** · el estado **se persiste antes de ejecutar** (comprobado por posición en el código) |
| E1–E2 | Cola: la orden que supera el límite **se encola, no se descarta** · al día siguiente **se retoma** |

## Dos fallos de aserción que las propias pruebas destaparon

1. **P3 (límite diario).** Al añadir la firma, la autenticación pasa a comprobarse
   **antes** que el límite, así que la prueba ya no alcanzaba su rama. Se aisló
   desactivando la firma solo en esa prueba, y se documenta el orden real de
   comprobaciones: **autenticación → límite → ejecución**.
2. **P3 (criterio de "no ejecutada").** En v2 una orden que supera el límite **sí
   se registra** (queda en cola con estado `pendiente`), así que "no hay órdenes"
   dejó de ser el criterio correcto. Se cambió a "ninguna llegó a `entregado`".

## Circuito real en vivo, con orden firmada (v2)

Orden **firmada** con HMAC-SHA256 y publicada en la issue #3, ejecutada por el
lector y con el gasto registrado en el libro de presupuesto:

| Paso | Evidencia |
|---|---|
| Orden emitida y firmada | [comentario 5643111166](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5643111166) |
| Acuse de recibo | [comentario 5643112678](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5643112678) — *Origen autenticado: **sí** (firma HMAC válida)*, coste 0,00337860 USD |
| Resultado | [comentario 5643112774](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5643112774) — salida, `exit_code: 0`, coste y límite del día |

Registro local de la orden:

```json
{"estado": "entregado", "origen_autenticado": true, "coste_usd": 0.0033786}
```

**Libro de presupuesto** (`~/.hermes/bridge/presupuesto.json`), con el gasto
leído de la base de sesiones de Hermes, no estimado por el puente:

```json
{
  "dia": "2026-09-11",
  "gastado_usd": 0.0033786,
  "limite_usd": 5.0,
  "coste_desconocido": false,
  "sesiones": [
    {
      "sesion": "20260911_231922_99e99c",
      "model": "deepseek/deepseek-v4.1-flash",
      "in_tokens": 21648,
      "out_tokens": 219,
      "coste_usd": 0.0033786,
      "cost_status": "estimated",
      "cost_source": "provider_models_api"
    }
  ]
}
```

El modelo y el proveedor son los configurados por el usuario
(`openrouter` / `deepseek/deepseek-v4.1-flash`): el puente no los cambia.
