# Puente local GitHub ↔ Hermes (issue #3)

Permite que el supervisor publique asignaciones y revisiones en GitHub y que
Hermes las recoja **en local** y devuelva el resultado, sin que nadie copie
mensajes a mano.

**No es acceso remoto al PC.** No abre puertos, no expone nada a Internet, no
instala un runner de acciones con acceso general a la máquina y no desactiva
ninguna aprobación de seguridad.

---

## Qué hace y qué no hace (versión 2)

| Sí hace | No hace |
|---|---|
| Sondeo de GitHub cada 5 minutos **sin LLM** y en silencio si no hay novedades | No ejecuta texto arbitrario de un comentario |
| **Autentica el origen** con firma HMAC-SHA256 y secreto fuera de GitHub | No ejecuta nada fuera de una allowlist cerrada |
| Acusa recibo con ID y publica un resultado verificable | No procesa el histórico al arrancar |
| **Aplica un presupuesto diario** leyendo el gasto real de `state.db` | No reintenta a ciegas tras una interrupción |
| **Reconcilia publicaciones fallidas** sin duplicar comentarios | No compra ni recarga nada automáticamente |
| **Encola** las órdenes que superan un límite, para retomarlas al día siguiente | No cambia el modelo ni el proveedor configurados |
| Deduplica por ID de comentario y por ID de orden; bloqueo exclusivo | No abre puertos ni expone nada a Internet |

**Presupuesto autorizado: US$5,00 diarios**, con reinicio del día según
**America/New_York** y sin compras ni recargas automáticas. El lector de GitHub no
usa modelo: no consume tokens. Solo la acción `tarea_local` gasta, y solo si el
presupuesto lo permite.

---

## El origen se autentica con firma, no con autoría

El supervisor y Hermes publican con la **misma cuenta de GitHub**
(`celestinojbm`), así que **el autor de un comentario no prueba quién lo
escribió**. La autenticación real es una **firma HMAC-SHA256** sobre la
serialización canónica de la orden, con un secreto de 256 bits que vive solo en
`~/.hermes/bridge/secreto` (`chmod 600`) y **nunca toca GitHub**.

Sin firma válida **no se ejecuta nada**: la orden se registra como
`no_autenticada` y se publica el motivo. Sin secreto local, **fallo cerrado**. Las
órdenes caducan a las 24 h, y cambiar cualquier campo firmado (por ejemplo la
acción) invalida la firma — ambas cosas están probadas.

Aun con firma válida, el alcance sigue siendo cerrado: solo `ping` y
`tarea_local`, y `tarea_local` ejecuta una única pasada de Hermes con un **prompt
fijo escrito en el código**, no con texto del comentario.

---

## Componentes

| Fichero | Función |
|---|---|
| `lector.py` | Proceso de sondeo. Sin LLM. Idempotente y con bloqueo exclusivo |
| `auth.py` | Firma y verificación HMAC-SHA256 de las órdenes; provisiona el secreto |
| `presupuesto.py` | Presupuesto diario verificable, con día America/New_York |
| `firmar-orden.py` | Ayuda para firmar una orden y publicarla |
| `config.example.json` | Configuración: repos/issues permitidos, límites, pausa, allowlist |
| `formato-orden.md` | Formato del bloque `hermes-order` y reglas de tratamiento |
| `instalar.sh` | Instalación local reversible (tres modos) |
| `desinstalar.sh` | Rollback |
| `pruebas/test_lector.py` | Batería de 8 pruebas, aislada en `/tmp` |
| `pruebas/test_ejecutor.py` | Batería de 23 pruebas: firma, presupuesto, recuperación y cola |

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
| Presupuesto | **5,00 USD/día**, reinicio a medianoche de America/New_York | `limites.presupuesto_usd`, `limites.zona_presupuesto` |
| Worker de trabajo | habilitado solo con presupuesto asignado | `limites.worker_llm_habilitado` |
| Acciones ejecutables | `ping`, `tarea_local` | `acciones_permitidas` ∩ enumerado cerrado del código |
| Compras / recargas automáticas | **desactivadas** | `limites.sin_compras_ni_recargas_automaticas` |

Al alcanzar el límite diario, la orden se registra como bloqueo visible y **no se
ejecuta**: **queda en cola** y se retoma al día siguiente. Un fallo repetido deja
también bloqueo visible en `estado.json`.

### Cómo se aplica el presupuesto (no es decoración)

1. **Antes** de ejecutar: `puede_gastar()` compara el gasto acumulado del día con
   el límite. Si no queda margen, la ejecución **no ocurre** y la orden se encola.
2. **Después** de ejecutar: se lee el coste real de la sesión recién creada en la
   tabla `sessions` de `~/.hermes/state.db` (`estimated_cost_usd` /
   `actual_cost_usd`, con `cost_status` y `cost_source`) y se suma al libro.
3. **Coste desconocido → fallo cerrado**: si una ejecución consumió tokens y su
   coste no puede determinarse, el ejecutor se bloquea hasta reconciliación.
   Un límite que se salta cuando no se puede medir no es un límite.
4. El día se reinicia según **America/New_York**, no según la hora local del
   sistema.

El libro queda en `~/.hermes/bridge/presupuesto.json`, con una entrada por
ejecución: sesión, modelo, tokens, coste, acumulado y límite.

---

## Procedimiento de alta de una orden (lo que hace el supervisor)

```bash
python3 puente/firmar-orden.py --accion tarea_local --id ord-2026-09-12-001
```

Imprime el bloque firmado listo para pegar:

````
```hermes-order
{
  "id_orden": "ord-2026-09-12-001",
  "tipo": "orden",
  "accion": "tarea_local",
  "parametros": {},
  "emitida_en": "2026-09-12T03:19:15+00:00",
  "firma": "68b29ada…ff76"
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
| Ejecución de trabajo real con LLM | **Acotada a `tarea_local`** | Una única pasada de Hermes con prompt fijo, bajo presupuesto de 5 USD/día. Trabajo abierto (varios pasos, herramientas, escritura) **no implementado** |
| Autenticación de origen | **Implementada (HMAC-SHA256)** | Ver arriba; queda pendiente provisionar el secreto en la máquina de quien firma |
| Escritura del heartbeat único actualizable | **No implementada** | Hoy se publican acuse y resultado por orden; el campo `comentario_estado` existe en la config pero no se usa todavía |
| Recarga/compra automática | **Desactivada por diseño** | El puente no compra ni recarga nada; el límite solo bloquea y encola |

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
