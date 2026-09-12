# Puente local GitHub ↔ Hermes (issue #3)

Permite que el supervisor publique asignaciones y revisiones en GitHub y que
Hermes las recoja **en local** y devuelva el resultado, sin que nadie copie
mensajes a mano.

**No es acceso remoto al PC.** No abre puertos, no expone nada a Internet, no
instala un runner de acciones con acceso general a la máquina y no desactiva
ninguna aprobación de seguridad.

---

## Qué hace y qué no hace (versión 1)

| Sí hace | No hace |
|---|---|
| Sondeo de GitHub cada 5 minutos **sin LLM** y en silencio si no hay novedades | No ejecuta texto arbitrario de un comentario |
| Detecta órdenes en un formato estructurado y cerrado | No autentica el origen (ver abajo) |
| Acusa recibo con ID y publica un resultado verificable | No ejecuta nada fuera de una allowlist inocua |
| Deduplica por ID de comentario y por ID de orden | No procesa el histórico al arrancar |
| Bloqueo exclusivo: dos ejecuciones no se solapan | No reinicia trabajos con efectos externos inciertos |

**El worker de trabajo con LLM queda EN PAUSA** (`limites.worker_llm_habilitado:
false`, `presupuesto_usd: null`). El lector de GitHub no usa modelo: no consume
tokens. No se habilita ejecución LLM recurrente hasta publicar el mecanismo de
límite y recibir un presupuesto explícito (issue #3, punto 8).

---

## El punto delicado: el origen NO está autenticado

El supervisor y Hermes publican con la **misma cuenta de GitHub**
(`celestinojbm`). Por tanto **el autor de un comentario no prueba quién lo
escribió**: cualquiera con acceso a esa cuenta puede escribir lo que parece una
orden.

Consecuencia de diseño, explícita y deliberada: en esta versión solo se reconocen
acciones de un **enumerado cerrado e inocuo** (hoy únicamente `ping`). Cualquier
otra orden se registra como `pendiente_confirmacion_humana` y **no se ejecuta**.
El acuse publicado lo dice con todas las letras: *"Origen autenticado: no"*.

Si más adelante se quiere ejecutar trabajo real de forma automática, hace falta
un mecanismo de autenticación de origen que no dependa de la autoría del
comentario (por ejemplo un HMAC con secreto compartido por fuera de GitHub).
**Mientras eso no exista, este puente es de lectura y notificación.**

---

## Componentes

| Fichero | Función |
|---|---|
| `lector.py` | Proceso de sondeo. Sin LLM. Idempotente y con bloqueo exclusivo |
| `config.example.json` | Configuración: repos/issues permitidos, límites, pausa, allowlist |
| `formato-orden.md` | Formato del bloque `hermes-order` y reglas de tratamiento |
| `instalar.sh` | Instalación local reversible (tres modos) |
| `desinstalar.sh` | Rollback |
| `pruebas/test_lector.py` | Batería de 8 pruebas, aislada en `/tmp` |

Estado y logs en tiempo de ejecución (fuera del repositorio, nunca versionados):

```
~/.hermes/bridge/config.json   # configuración (chmod 600)
~/.hermes/bridge/estado.json   # cursor, deduplicación, registro de órdenes, bloqueos
~/.hermes/bridge/logs/         # log diario + salida de cron
~/.hermes/bridge/.lock         # bloqueo exclusivo
```

---

## Instalación

```bash
# 1) cron del sistema (lo que está instalado aquí; cron.service ya venía activo)
./puente/instalar.sh cron

# 2) alternativa oficial de Hermes (requiere el gateway en marcha para disparar)
./puente/instalar.sh hermes-cron

# 3) solo crear la configuración, sin programar nada
./puente/instalar.sh solo-config
```

Comprobación manual, sin esperar al cron:

```bash
PUENTE_HOME=~/.hermes/bridge python3 puente/lector.py --verbose
```

### Por qué cron del sistema y no `hermes cron` (en esta instalación)

En esta máquina, `hermes cron` **no dispara**: `hermes cron status` informa
`Gateway is not running — cron jobs will NOT fire`. El gateway es el servicio de
mensajería y no estaba en marcha; levantarlo es un cambio mayor y no era
necesario. `cron.service` del sistema **sí** estaba activo, así que el lector se
programó ahí. El modo `hermes-cron` queda disponible para cuando el gateway esté
en marcha. Esto es exactamente lo que pedía la issue: preferir los mecanismos
oficiales **compatibles con la instalación**, sin asumir que tiene todas las
funciones de la documentación.

### Rollback

```bash
./puente/desinstalar.sh             # quita la programación; conserva estado y logs
./puente/desinstalar.sh --completo  # además pregunta si borrar ~/.hermes/bridge
```

### Pausa

Cualquiera de estas dos, sin desinstalar nada:

- crear el fichero vacío `~/.hermes/bridge/PAUSA`
- poner `"pausa": true` en `~/.hermes/bridge/config.json`

---

## Límites

| Límite | Valor por defecto | Dónde |
|---|---|---|
| Órdenes por día | 20 | `limites.max_ordenes_por_dia` |
| Duración máxima de ejecución | 60 s | `limites.max_duracion_ejecucion_s` |
| Presupuesto | `null` → worker LLM deshabilitado | `limites.presupuesto_usd` |
| Worker de trabajo | **pausado** | `limites.worker_llm_habilitado` |
| Acciones ejecutables | `ping` | `acciones_permitidas` ∩ enumerado cerrado del código |

Al alcanzar el límite diario, la orden se registra como bloqueo visible y **no se
ejecuta**. Un fallo repetido deja también bloqueo visible en `estado.json`.

---

## Procedimiento de alta de una orden (lo que hace el supervisor)

Publicar un comentario con:

````
```hermes-order
{
  "id_orden": "ord-2026-09-12-001",
  "tipo": "orden",
  "accion": "ping",
  "parametros": {}
}
```
````

El formato completo y las reglas están en [`formato-orden.md`](formato-orden.md).

---

## Verificación: qué está demostrado y qué no

Detalle con comandos y salidas en [`PRUEBAS.md`](PRUEBAS.md).

**Demostrado con órdenes reales publicadas en GitHub** (issue #3):

| Orden | Comentario | Acuse | Resultado |
|---|---|---|---|
| `ord-aceptacion-2026-09-11-001` | [5640853010](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640853010) | [5640853202](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640853202) | [5640853317](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640853317) |
| duplicado (mismo `id_orden`) | [5640855026](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640855026) | — | ignorado, sin segunda ejecución |
| orden inválida (JSON roto) | [5640863061](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863061) | — | bloqueo registrado |
| acción no permitida (`shell`) | [5640863181](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863181) | [5640863376](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863376) | [5640863507](https://github.com/celestinojbm/entrenamiento-hermes/issues/3#issuecomment-5640863507) — no ejecutada |

**Demostrado además:** el lector dispara desde cron cada 5 minutos por su cuenta
(marcas exactas en `~/.hermes/bridge/logs/`), con `cron.out` vacío — es decir,
**cerrar el chat interactivo no mata el lector**. Ocho pruebas locales OK
(silencio, pausa por fichero y por config, límite diario, no-procesar-histórico,
bloqueo exclusivo, tolerancia a fallo de API, interrupción de una ejecución en
curso).

### NO verificado (declarado, no maquillado)

| Escenario | Estado | Motivo |
|---|---|---|
| PC suspendido, apagado o reinicio de Windows | **No probado** | No se puede provocar sin cortar la sesión del usuario. **No se promete 24/7 en WSL** |
| Sin red | **No probado** | Solo se probó un fallo de API por recurso inexistente, no una caída de red |
| Reinicio del daemon `cron.service` | **No probado a propósito** | Es un servicio **preexistente y compartido**: reiniciarlo habría afectado a otros usos de la máquina. Se probó en su lugar la interrupción de una ejecución del propio lector |
| Dependencia del transporte | **Limitación real** | En WSL no hay `gh`; se usa el `gh.exe` ya autenticado de Windows. Si Windows está apagado o el keyring bloqueado, el lector no puede publicar y lo registra como bloqueo |
| Ejecución de trabajo real con LLM | **Pausada por diseño** | Sin presupuesto explícito y sin mecanismo de límite validado (issue #3, punto 8) |
| Autenticación de origen | **No implementada** | Solo lectura/notificación; ver arriba |
| Escritura del heartbeat único actualizable | **No implementada** | Hoy se publican acuse y resultado por orden; el campo `comentario_estado` existe en la config pero no se usa todavía |

---

## Postura de seguridad

- Sin secretos en el repositorio: la autenticación usa las credenciales de GitHub
  **ya configuradas** en la máquina. El puente no crea, copia ni almacena tokens.
- Config y estado viven fuera del repo (`~/.hermes/bridge`, `chmod 600`).
- Nada de `shell`, `eval` ni interpolación de texto de comentarios.
- Adjuntos, citas y contenido de repositorios se tratan como **datos no
  confiables**.
- Los comentarios del propio puente llevan la marca `<!-- hermes-puente:v1 -->` y
  nunca se procesan como órdenes (no hay bucles de comentarios).
- Una acción nueva requiere **dos** cambios deliberados: la allowlist de la config
  **y** el enumerado cerrado del código.
