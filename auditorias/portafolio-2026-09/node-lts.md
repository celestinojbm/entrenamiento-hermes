# Runtime de Node: decisión y alcance real del cambio (punto 5)

Responde al punto 5 de la revisión 5185022108. **La revisión tiene razón en los
dos extremos**: la propuesta anterior era incorrecta y, además, cambiar
`package.json` no cambia el runtime desplegado.

## 1. La propuesta anterior era incorrecta

`plan-90-dias.md` §2.6 y `backlog-priorizado.md` M2 proponían `node:22→25`. Según
la tabla oficial (<https://nodejs.org/en/about/previous-releases>, consultada para
esta ronda):

| Node | Estado oficial |
|---|---|
| v26 | **Current** |
| **v25** | **EOL** |
| **v24** | **LTS** (Krypton) |
| **v22** | **LTS** (Jod) |
| v20 | **EOL** |

La propia fuente recomienda: *"only use Active LTS or Maintenance LTS releases"*.
Proponer **25** era proponer una versión ya muerta. **Corregido.**

## 2. Decisión propuesta

**Adoptar Node 24 LTS**, no 25, y **no** como salto inmediato.

| Decisión | Valor |
|---|---|
| Objetivo | **Node 24 LTS** |
| Rango de `engines` | **`">=24 <25"`** — no `">=22"` |
| Motivo del rango acotado | `">=22"` **permite versiones impares ya EOL** (23, 25) y mayores futuras no probadas. Un rango abierto no es una política de runtime, es una ausencia de política |
| Cuándo | **Después** del camino mínimo a ingresos, no antes (§4) |
| Qué NO es | Node 24 no arregla el bug de `origin`/CSRF de Fluvia ni desbloquea cobrar |

**Condición que invalida la decisión:** si las suites de Fluvia, EvolveOS o Nova
no pasan en 24, el objetivo baja a **22 LTS** (que ya es LTS y es el runtime
declarado por Nova). Es una comprobación, no un supuesto: hay que ejecutarla.

## 3. Inventario: dónde vive el runtime de verdad

Cambiar solo `package.json` **no actualiza nada de lo desplegado**. Esto es lo que
hay que tocar, medido en los clones:

| Repo | `engines` hoy | Dockerfile | CI (`node-version`) |
|---|---|---|---|
| Dona-agent | *(sin `engines`)* | `node:22-slim@sha256:53ada149…` — **pineado por digest** | 22 (y matrices `[18,20,22]`, `[18.x,20.x,22.x]`, un `'10'`) |
| Fluvia | `">=20"` | Dockerfile propio (base `denoland/deno` + `python:3.12-slim`); no trae imagen `node:` | 22 y `'24'` en distintos workflows |
| EvolveOS | `">=20"` | sin Dockerfile propio | `app-ci`, `spec-consistency` |
| nova-context | `">=22"` | sin Dockerfile propio | `ci.yml` |
| Donalabs | *(sin `engines`)* | solo `services/ytdlp/Dockerfile` (python/deno) | — |

**Consecuencia práctica:** en Dona-agent el runtime está **fijado por digest de
imagen**, así que un cambio de `engines` sin tocar el Dockerfile no cambia nada en
producción. Y en CI hay **matrices con Node 18 y hasta un `'10'`**: son EOL y hay
que retirarlos, no solo subir el principal.

**Alcance real del cambio, por repo:** `package.json` (`engines`) + Dockerfile con
digest + workflow(s) de CI + configuración de hosting. Cuatro sitios, no uno.

## 4. Por qué va fuera del camino mínimo a ingresos

Node 20 está EOL desde 2026-04-30 (hecho, no opinión), pero **no bloquea cobrar con
Dona** — Dona es Python y su `engines` está vacío. Node 20 afecta a Fluvia,
EvolveOS y Donalabs, que **no son la ruta de ingreso de las próximas semanas**.
Queda por tanto en **seguridad/mantenimiento**, con una excepción: si Fluvia entra
en la ruta crítica de demo, se adelanta para Fluvia solo.

## 5. Lo que NO está verificado

- **No se ha ejecutado ninguna suite en Node 24 ni 22**: no hay una medición que
  respalde que el salto sea seguro. Solo hay la política oficial de soporte y la
  compatibilidad declarada. **Es un supuesto, no un resultado.**
- No se inventarió la configuración de hosting (Vercel, Railway u otra): no estaba
  en los clones.