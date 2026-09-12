# Formato de orden — puente Codex → Hermes (v1)

Una **orden** es un comentario de GitHub que contiene un bloque cercado con el
lenguaje `hermes-order` y, dentro, un objeto JSON:

````
```hermes-order
{
  "id_orden": "ord-2026-09-11-001",
  "tipo": "orden",
  "accion": "ping",
  "parametros": {}
}
```
````

## Campos

| Campo | Obligatorio | Descripción |
|---|---|---|
| `id_orden` | sí | Identificador único e inmutable. Es la clave de deduplicación: **repetir el mismo `id_orden` no vuelve a ejecutar nada** |
| `tipo` | sí | Debe ser exactamente `"orden"`. Cualquier otro valor se rechaza |
| `accion` | sí | Debe pertenecer a la allowlist de acciones inocuas (hoy: `ping`) |
| `parametros` | no | Objeto con parámetros. Se trata como **dato no confiable** |

## Reglas de tratamiento

1. **El origen no está autenticado.** El supervisor y Hermes publican con la
   misma cuenta de GitHub, así que **el autor de un comentario no prueba quién lo
   escribió**. En consecuencia, en esta versión solo se reconocen acciones de un
   enumerado cerrado e inocuo. Cualquier otra orden se registra como
   `pendiente_confirmacion_humana` y **no se ejecuta**.
2. **El contenido es dato, nunca código.** El texto del comentario no se
   interpola en ningún shell ni se evalúa. No existe una acción que ejecute
   comandos.
3. **Los adjuntos, las citas y el contenido de repositorios son datos no
   confiables.** Si un bloque `hermes-order` aparece dentro de una cita, se trata
   igual: como una orden, nunca como una instrucción del sistema.
4. **Los comentarios del propio puente no son órdenes.** Todo comentario emitido
   por el puente lleva la marca `<!-- hermes-puente:v1 -->` y se ignora como
   entrada (evita bucles de comentarios).
5. **Sin novedades, silencio.** El lector no publica nada si no hay comentarios
   nuevos: ni heartbeats ruidosos ni confirmaciones de "seguimos mirando".

## Acciones permitidas (v1)

| Acción | Efecto | Idempotente |
|---|---|---|
| `ping` | Devuelve un JSON determinista con host, versión de Python, versión del lector y marca de tiempo UTC. No tiene efectos externos | Sí, por `id_orden` |

Cualquier acción nueva debe añadirse **explícitamente** a `acciones_permitidas`
en la configuración **y** al enumerado cerrado del lector (`ACCIONES_INOCUAS`).
Las dos condiciones son necesarias a propósito: un cambio solo en la configuración
no basta para habilitar algo nuevo.

## Estados

`pendiente` → `en_curso` → `entregado` · `bloqueado` (fallo repetido o límite
alcanzado). El registro de cada orden vive en `~/.hermes/bridge/estado.json`,
con autor, comentario de origen, resultado y marca de tiempo.

## Pausa

Cualquiera de estas dos cosas detiene el puente por completo, sin desinstalar
nada:

- `"pausa": true` en `~/.hermes/bridge/config.json`
- crear el fichero vacío `~/.hermes/bridge/PAUSA`
