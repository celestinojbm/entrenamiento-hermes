# Gitleaks: estado real, corrección de las cifras y criterio de cierre (punto 7)

Responde al punto 7 de la revisión 5185022108: *"La evidencia dice «cinco cadenas»
pero la medición del fixture habla de «4 fixtures»; debe explicarse la diferencia.
La prueba se realizó con `--no-git` en un fixture aislado y no ejecutó el workflow
real ni el historial de Dona. Por tanto S1 no puede considerarse cerrado."*

**La revisión tiene razón en todo.** Y al volver a medir, **una de mis cifras
anteriores era incorrecta**. Esta es la medición nueva, hecha para esta ronda.

## 1. La diferencia entre "cinco cadenas" y "cuatro fixtures", explicada

La allowlist de `propuestas/gitleaks-dona.toml` contiene **5 valores literales**:

```
dona-secret123 · sk-AAA...2345 · whsec_AAAABBBBCCCC1234567890
dona-abc123def456 · dona-fedcba987654
```

De esos 5, **sólo 3 corresponden a hallazgos** del ruleset por defecto. Los otros 2
(`sk-AAA...2345` y `dona-fedcba987654`) son valores que aparecen en los tests del
repo pero que el ruleset actual **no marca**: se dejan por robustez ante cambios de
ruleset, no porque supriman algo hoy.

Medición con el ruleset por defecto sobre el fixture (`6 hallazgos`):

| Detector | Valor | Origen |
|---|---|---|
| `aws-access-token` | `AKIA…PW3A` | **sembrado** (debe detectarse) |
| `github-pat` | `ghp_…` | **sembrado** (debe detectarse) |
| `generic-api-key` | `whsec_AAAABBBBCCCC1234567890` | fixture sintético |
| `generic-api-key` | `dona-secret123` | fixture sintético |
| `generic-api-key` | `dona-abc123def456` | fixture sintético |
| `generic-api-key` | `JOTY38dinsxCHMRW16bglqvAFKPUZ49e` | **artefacto generado** (`landing/.next/dev/x.json`) |

**Corrección de mi cifra anterior: la config suprime 3 hallazgos, no 4.**

- De los 6, **2 son los secretos sembrados** (correcto que sigan saliendo).
- De los 4 no sembrados, **3 los cubren los literales** y **el 4.º es un artefacto
  generado** que la propuesta **no suprime a propósito**: se decidió no usar
  allowlist por ruta (`paths`) porque eso cegaría el gate para todo ese directorio.
  Decir "4 fixtures suprimidos" era impreciso. Lo correcto: **3 suprimidos, 1
  artefacto dejado visible por diseño.**

## 2. Verificación con la configuración propuesta (medida)

```
ruleset por defecto              → 6 hallazgos
config propuesta de Dona        → 3 hallazgos
  · JOTY38… content.json        → visible (artefacto generado, a propósito)
  · aws-access-token (sembrado) → DETECTADO  ✓
  · github-pat (sembrado)       → DETECTADO  ✓
secretos sembrados aún detectados: 2 de 2
```

El gate **no queda ciego**: los dos secretos sembrados siguen fallando. Eso es lo
que la prueba demuestra.

## 3. Qué NO demuestra esta prueba (por eso S1 sigue abierta)

| Límite | Consecuencia |
|---|---|
| Se ejecutó con `--no-git` sobre un **fixture aislado**, no sobre el repositorio de Dona | No se ha escaneado el **historial** real |
| No se ejecutó el **workflow real** de CI | No está probado que el gate funcione donde tiene que funcionar |
| No se ha abierto un PR en Dona con esta configuración | Nada está aplicado: sigue siendo una **propuesta** |
| No se midió el alcance real de CI (qué rutas escanea, con qué flags) | Una config que funciona en un fixture puede comportarse distinto en el pipeline |

## 4. Criterio de cierre de S1 (falsable, todavía no cumplido)

S1 sólo se cierra cuando, **en un PR de Dona**, el workflow demuestre las tres cosas
a la vez:

1. los fixtures sintéticos **no** hacen fallar el gate;
2. un secreto sembrado **sí** lo hace fallar;
3. el escaneo cubre el **alcance real** de CI (no un fixture).

Hasta entonces, **`gitleaks` está en estado de propuesta**, y así debe figurar en la
tabla canónica y en el backlog. Lo que sí está resuelto es la **contradicción de
cifras**, que era lo que la revisión pedía explicar.

## 5. Nota de método

El fixture se regenera con
`evidencia-visual/scripts/generar-fixture-gitleaks.py`, que emula la estructura
relativa de Dona (`tests/`, `landing/.next/dev/`) sin tocar el repositorio auditado
— la regla de no mutar los repos auditados se mantiene. El artefacto generado
(`landing/.next/dev/x.json` y `tests/`) **se regenera con ese script** y no se
versiona: contiene cadenas con forma de credencial y no tiene sentido guardar
señuelos en el repositorio de la auditoría.