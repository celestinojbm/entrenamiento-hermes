# Formato de orden — puente Codex → Hermes (v2)

Una **orden** es un comentario de GitHub con un bloque cercado `hermes-order` que
contiene un objeto JSON **firmado**:

````
```hermes-order
{
  "id_orden": "ord-2026-09-12-001",
  "tipo": "orden",
  "accion": "tarea_local",
  "parametros": {},
  "emitida_en": "2026-09-12T03:19:15+00:00",
  "firma": "68b29adae376b9a4e19dd4809be9efa08c47e2eac3a3a9c1b4697409faacff76"
}
```
````

---

## 1. Autenticación verificable (obligatoria)

El supervisor y Hermes publican en GitHub con la **misma cuenta**, así que **el
autor de un comentario no autentica nada**. La autenticación real es una **firma
HMAC-SHA256** con un secreto compartido que **nunca toca GitHub**.

| Aspecto | Decisión |
|---|---|
| Algoritmo | HMAC-SHA256 |
| Secreto | `~/.hermes/bridge/secreto`, 256 bits, `chmod 600`, fuera del repositorio |
| Qué se firma | Serialización **canónica** de `id_orden`, `tipo`, `accion`, `parametros` y `emitida_en`: JSON con claves ordenadas y sin espacios |
| Comparación | En tiempo constante (`hmac.compare_digest`) |
| Caducidad | 24 h desde `emitida_en` (defensa básica antirreplay) |
| Sin secreto local | **Fallo cerrado**: no se autentica nada |
| Sin firma o firma inválida | La orden se registra como `no_autenticada` y **no se ejecuta** |

Provisionar el secreto (una vez, en la máquina):

```bash
python3 puente/auth.py init      # crea el secreto si no existe
python3 puente/auth.py estado    # dice si está presente, sin imprimirlo
```

Firmar una orden:

```bash
python3 puente/firmar-orden.py --accion tarea_local --id mi-orden-001
# o firmar un JSON existente
python3 puente/firmar-orden.py orden.json
```

Imprime el bloque listo para pegar en un comentario.

**Cambiar cualquier campo firmado invalida la firma.** Cambiar la acción después
de firmar se detecta y se rechaza (probado).

---

## 2. Campos

| Campo | Obligatorio | Descripción |
|---|---|---|
| `id_orden` | sí | Identificador único e inmutable. Clave de deduplicación: **repetirlo no vuelve a ejecutar nada** |
| `tipo` | sí | Debe ser exactamente `"orden"` |
| `accion` | sí | Debe pertenecer a la allowlist (ver §3) |
| `parametros` | no | Objeto con parámetros. **Dato no confiable** |
| `emitida_en` | **sí** | Fecha ISO con zona. Se firma y caduca a las 24 h |
| `firma` | **sí** | HMAC-SHA256 hexadecimal del resto de campos |

---

## 3. Acciones permitidas (v2)

| Acción | Efecto | Coste | Idempotente |
|---|---|---|---|
| `ping` | JSON determinista con host, versión de Python y marca UTC. Sin efectos externos | 0 | Sí, por `id_orden` |
| `tarea_local` | Ejecuta una ejecución **única y acotada** de Hermes con un **prompt fijo escrito en el código**. No acepta texto del comentario | ~0,003 USD | Sí, por `id_orden` |

Una acción nueva exige **dos** cambios deliberados: la allowlist de la
configuración **y** el enumerado cerrado del código (`ACCIONES_INOCUAS`). Un
cambio solo en la configuración no habilita nada.

**Ninguna acción ejecuta comandos.** El contenido del comentario es siempre dato,
nunca código: no hay `shell`, ni `eval`, ni interpolación.

---

## 4. Reglas de tratamiento

1. **Adjuntos, citas y contenido de repositorios son datos no confiables.**
2. **Los comentarios del propio puente no son órdenes.** Llevan
   `<!-- hermes-puente:v1 ... -->` y se ignoran como entrada (no hay bucles).
3. **Sin novedades, silencio.** No se publica nada si no hay comentarios nuevos.
4. **La orden se registra antes de ejecutarse.** El reclamo se persiste en disco
   antes de lanzar nada (§6).
5. **Nunca se reintenta a ciegas.** Una orden que quedó `en_curso` porque el
   proceso murió pasa a `bloqueado_interrumpido` y espera revisión manual.

---

## 5. Límites, presupuesto y cola

| Límite | Valor | Comportamiento al alcanzarlo |
|---|---|---|
| `max_ordenes_por_dia` | 20 | La orden se **encola** para el día siguiente |
| `presupuesto_usd` | **5,00** | La orden se **encola** para el día siguiente |
| `max_duracion_ejecucion_s` | 60 | La ejecución se corta y se registra |

- El día presupuestario se reinicia a **medianoche de America/New_York**.
- El gasto se lee de una fuente auditable: la tabla `sessions` de
  `~/.hermes/state.db` (`estimated_cost_usd` / `actual_cost_usd`, `cost_status`,
  `cost_source`), no de una estimación propia.
- **Coste desconocido → fallo cerrado.** Si una ejecución consume tokens y su
  coste no puede determinarse, el ejecutor se bloquea hasta reconciliación: un
  límite que se ignora cuando no se puede medir no es un límite.
- Sin compras ni recargas automáticas.

---

## 6. Recuperación tras interrupciones

| Situación | Comportamiento |
|---|---|
| El proceso muere **después** de reclamar y **antes** de registrar el resultado | La orden pasa a `bloqueado_interrumpido`. **No se reintenta**: no se repiten efectos externos inciertos |
| Publicar el acuse o el resultado falla | Queda en el buzón de salida y se reintenta en la pasada siguiente |
| El proceso muere **después** de publicar pero **antes** de guardar estado | Al reintentar, el puente detecta por marca que el comentario **ya existe** y no lo duplica |
| Se alcanza un límite | La orden queda en cola con su motivo y se retoma al día siguiente |
| Dos ejecuciones a la vez | Bloqueo exclusivo (`flock`): la segunda sale sin trabajar |

---

## 7. Pausa

Cualquiera de estas dos, sin desinstalar nada:

- `"pausa": true` en `~/.hermes/bridge/config.json`
- crear el fichero vacío `~/.hermes/bridge/PAUSA`
