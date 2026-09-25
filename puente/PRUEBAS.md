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

---

# v3 — control del gasto DURANTE la ejecución y autenticación asimétrica

## Batería 3 — el techo no se rebasa, ni con reintentos ni con tareas auxiliares

Método: en el PATH se coloca un `hermes` **falso** que escribe en una base de
sesiones falsa (mismo esquema que la real) el coste indicado y termina con el
código pedido. Así se ejercita el bucle real del lector —autorización por
segmento, liquidación, reintentos— sin gastar dinero.

```
OK    F1 la reserva se comprueba antes de cada intento
      gastado=0.01 <= limite=0.08, intentos=1
OK    F2 los reintentos se detienen antes de rebasar el techo
      gastado=0.0160 <= 0.0250 | intentos=3 autorizados=2 | último bloqueado: la reserva de 0.0100 USD no cabe: gastado 0.016000 + reserva
OK    F3 las sesiones auxiliares de la ventana se atribuyen al segmento
      gastado=0.31 (0.01 + 0.30 auxiliar) sesiones=2
OK    F4 el exceso sobre la reserva bloquea el día
      exceso=True motivo=el segmento costó 0.400000 USD y superó su reserva de 0.0500 USD; se b
OK    F4b con exceso registrado no se autoriza ningún intento más
      el día quedó bloqueado por exceso: el segmento costó 0.400000 USD y superó su re
OK    F5 coste desconocido → fallo cerrado
      desconocido=True | consumo previo con coste desconocido: no puede acotarse, requiere reco
OK    F6 sin margen para la reserva no se lanza ni un intento
      intentos=1 autorizado=False gastado=0.0
OK    F7 tope de turnos + plazo + corte duro del grupo de procesos
      HERMES_MAX_ITERATIONS, HERMES_AGENT_TIMEOUT, start_new_session, killpg presentes

resumen: 8/8 pruebas OK
```

## Batería 4 — autenticación asimétrica del supervisor

```
OK    S1 se genera el par de claves del supervisor
      privada=hermes_orden publica=hermes_orden.pub
OK    S2 el allowlist contiene SOLO la clave pública
      supervisor ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINUtw9ZzENwrm…
OK    S3 la orden se firma y se empaqueta para el comentario
      firmante=supervisor firma=U1NIU0lHAAAAAQAAADMAAAALc3NoLWVk…
OK    S4 la firma se verifica con la clave pública
      firma SSH válida de 'supervisor'
OK    S5 cambiar la acción invalida la firma
      firma SSH rechazada: Signature verification failed: incorrect signature
OK    S6 otra clave pública no puede validar la orden
      firma SSH rechazada: Could not verify signature.
OK    S7 sin allowlist → fallo cerrado
      no existe el allowlist de claves públicas: /tmp/puente-test-ssh/no-existe
OK    S8 ninguna clave privada en el repositorio
      archivos con 'PRIVATE KEY': ninguno

resumen: 8/8 pruebas OK
```

## Demostraciones en vivo

**Demo A — sin margen para la reserva, cero gasto.** Orden real publicada en la
issue #3, procesada con un límite (0,004 USD) inferior a la reserva por intento
(0,05 USD):

```
la reserva de 0.0500 USD no cabe: gastado 0.000000 + reserva 0.0500 > límite 0.004
→ orden ENCOLADA para el próximo día
libro: {"gastado_usd": 0.0, "ejecuciones": []}
```

**Demo B — reserva autorizada antes y coste liquidado después**, con el
presupuesto real de 5 USD/día:

```json
{"intentos": [{"intento": 1, "autorizado": true, "exit": 0,
                "coste_usd": 0.00027361, "exceso": false, "sesiones": 1}],
  "coste_usd": 0.00027361, "acumulado_dia_usd": 0.00369391,
  "limite_dia_usd": 5.0, "reserva_por_intento_usd": 0.05,
  "restante_usd": 4.99630609, "dia_presupuesto": "2026-09-12"}
```

## Lo que NO se puede garantizar (medido, no supuesto)

**En Hermes no existe hoy un tope duro de gasto ni de iteraciones por ejecución
que pueda imponerse desde fuera.** Se comprobó:

| Intento de tope | Resultado medido |
|---|---|
| `HERMES_MAX_ITERATIONS=1` | **No acota.** El agente hizo 3 llamadas de herramienta. Hay un test en el propio Hermes (`tests/gateway/test_config_env_bridge_authority.py`) que confirma que `config.yaml` gana sobre esa variable |
| `agent.max_turns: 1` en un `HERMES_HOME` sellado | **No acota.** También 3 llamadas de herramienta |
| `-t ""` / toolsets vacíos | No impide el uso de herramientas |

Por tanto la garantía del puente es **condicional y declarada**:

1. La suma de gasto **autorizado** nunca supera el techo: se reserva antes de
   arrancar cada intento y no se arranca si la reserva no cabe (probado).
2. Un intento concreto puede costar más que su reserva. Cuando eso ocurre, el
   puente lo **detecta** (`exceso`), **bloquea el resto del día** y lo reporta
   (probado). Pero ese gasto ya se produjo: por eso la reserva debe ser un techo
   medido, no un número inventado.
3. **Corte duro por plazo**: si un intento se pasa del plazo, se mata el grupo de
   procesos completo (no solo el padre). Un desbocado no puede correr indefinidamente.
4. **Coste desconocido → fallo cerrado** (probado).

Referencia medida de coste por ejecución acotada del ejecutor: entre **0,00027361**
y **0,007121994** USD. La reserva de 0,05 USD es ~7 veces el máximo observado.
No se compran ni recargan créditos automáticamente en ningún caso.

## Propuesta de autenticación del supervisor: firma asimétrica

Con HMAC hay que provisionar un secreto compartido, lo que obliga a moverlo entre
máquinas. La propuesta viable **sin exportar ningún secreto** usa firmas SSH de
OpenSSH, ya disponibles en ambas máquinas (Linux 10.2p1, Windows 9.5p2 — este
último ya presente en `msi`, que además ya tiene `authorized_keys`).

```
Supervisor (msi)                        Hermes (WSL2)
─────────────────                       ──────────────
ssh-keygen -t ed25519 -f hermes_orden
  → la clave PRIVADA nunca sale
  → solo viaja la pública ───────────►  puente/allowed_signers
                                        supervisor ssh-ed25519 AAAAC3Nz…
ssh-keygen -Y sign -n hermes-order
  → orden firmada en el comentario ──►  ssh-keygen -Y verify -f allowed_signers
                                        -n hermes-order
```

Ventajas: no hay secreto compartido que provisionar ni rotar, no se puede
suplantar al supervisor desde la máquina de Hermes (solo tiene la pública), y la
revocación es borrar una línea. El namespace `hermes-order` separa estas firmas
de cualquier otra cosa que esa clave firme.

**Estado:** mecanismo **implementado y probado** (`puente/auth_ssh.py`, batería 4:
firma válida aceptada · manipulación rechazada · otra clave rechazada · sin
allowlist, fallo cerrado). **No está activado para el supervisor real porque
todavía no hay una clave pública suya provisionada**, y no declaramos conexión
por esto: existe el mecanismo, no el firmante.

Activar cuando el propietario decida: en `config.json`,
`"auth": {"esquema": "ssh-signature", "allowed_signers": "~/.hermes/bridge/allowed_signers"}`.
