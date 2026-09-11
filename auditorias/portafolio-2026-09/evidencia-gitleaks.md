# Evidencia — gate de secretos de Dona (gitleaks)

Responde a la nota de seguridad de la revisión: *"Para gitleaks, evitar una
allowlist amplia por archivo: usar exclusiones mínimas/específicas y demostrar
que un secreto real sembrado intencionadamente sigue fallando el gate."*

**La revisión tenía razón y la primera propuesta fue rechazada por su propia
prueba.** Se documenta el proceso completo, incluido el intento fallido.

---

## 1. Estado de partida (medido)

`gitleaks 8.30.1` sobre el árbol de trabajo de Dona-agent con su `.gitleaks.toml`
actual:

| Origen | Hallazgos |
|---|---|
| `tests/test_automation_audit.py:31` | `generic-api-key` |
| `tests/test_logging.py:63` | `generic-api-key` |
| `tests/test_logging.py:68` | `generic-api-key` |
| `tests/test_welcome_premium.py:96` | `generic-api-key` |
| `tests/test_welcome_premium.py:112` | `generic-api-key` |
| `landing/.next/dev/*` y `tests/__pycache__/*` | 6 más — **artefactos generados, no versionados** |

Precisión importante: `.next/` y `__pycache__/` están en `.gitignore` y **no
están trackeados** (`git ls-files` no los lista). Aparecen solo porque esta
auditoría ejecutó `next dev` y `pytest` sobre el árbol. El CI escanea el
historial/diff de git, así que **no los ve**. No se les atribuye ningún defecto
del repositorio.

Valores de los fixtures (ya públicos en el repo público): `dona-secret123`,
`sk-AAA...2345`, `whsec_AAAABBBBCCCC1234567890`, `dona-abc123def456`,
`dona-fedcba987654`.

**Por qué la config actual no arregla esto:** sus `regexes` apuntan a formas que
los hallazgos no tienen (`sk-ant-...`), así que **no suprimen nada**; y sus
patrones genéricos (`(?i)dummy[_-]?(secret|key|token|auth)`) suprimen **por
forma**, no por valor, en cualquier archivo del repo. Es a la vez ineficaz y
demasiado amplia.

---

## 2. Intento 1 — rechazado por la propia prueba

Primera propuesta: una allowlist con `condition = "AND"`, `paths` a los tres
archivos de test y `regexes` con los valores literales. La hipótesis era que
`paths` + `regexes` se combinarían (ambos deben coincidir).

**Medición sobre el fixture aislado:**

| Config | Hallazgos |
|---|---|
| Ruleset por defecto | 6 (4 fixtures + 2 secretos sembrados) |
| Config actual de Dona | 6 (no suprime nada) |
| **Intento 1** | **0 — también silenció los secretos sembrados** |

`gitleaks` aplicó `paths` como allowlist de **archivo completo**: el `condition`
no tuvo el efecto esperado. **Gate ciego. Propuesta descartada.**

Este es exactamente el riesgo que la revisión advertía, y por eso la prueba con
secreto sembrado es imprescindible: sin ella, el intento 1 habría pasado como
"arreglo".

---

## 3. Diseño final — supresión por valor literal

`propuestas/gitleaks-dona.toml`: **cinco cadenas literales, sin `paths` y sin
patrones de forma.**

```toml
[extend]
useDefault = true

[[allowlists]]
description = "Fixtures sinteticos no explotables ..."
regexTarget = "line"
regexes = [
  '''dona-secret123''',
  '''sk-AAA\.\.\.2345''',
  '''whsec_AAAABBBBCCCC1234567890''',
  '''dona-abc123def456''',
  '''dona-fedcba987654''',
]
```

Lo que hace que sea mínima **en el sentido que importa**: suprime **valores
concretos**, no archivos ni formas. Un secreto nuevo —aunque viva en el mismo
archivo y se llame `test_…`— sigue fallando.

Deliberadamente **no** se añade allowlist por ruta para `.next/` ni
`__pycache__/`: introducir una supresión por ruta que podría llegar a ocultar
contenido versionado es peor que reportar ruido de artefactos no versionados.

---

## 4. Prueba del diente (en directorio aislado, sin tocar el repo auditado)

Para no modificar el repositorio auditado, se generó un fixture equivalente en
`~/h014-work/gitleaks-test/` con las mismas rutas relativas
(`tests/test_logging.py`, `landing/.next/dev/x.json`, `tests/__pycache__/`),
construido por script (`evidencia-visual/scripts/generar-fixture-gitleaks.py`)
para no escribir literales con forma de secreto.

Contiene: los 4 fixtures reales **y** dos secretos sembrados con forma válida
para su regla y valor nuevo:

- `SEEDED_AWS`: `AKIA` + 16 caracteres alfanuméricos → debe disparar `aws-access-token`
- `SEEDED_PAT`: `ghp_` + 36 caracteres alfanuméricos → debe disparar `github-pat`

### Medición

| Config | Hallazgos | Detalle |
|---|---|---|
| Ruleset por defecto | 6 | 4 fixtures + **`aws-access-token`** + **`github-pat`** |
| Config actual de Dona | 6 | Igual: no suprime nada |
| Config de Dona v1 (rechazada) | 0 | **Gate ciego**: tampoco detectó los sembrados |
| **Config propuesta (v2)** | **3** | Solo `aws-access-token` + `github-pat` + el artefacto `.next/` no versionado |

**Resultado:** los 4 fixtures sintéticos quedan suprimidos y **los 2 secretos
sembrados dentro del mismo archivo siguen fallando el gate**. El artefacto
`.next/` sigue reportándose, y se explica arriba por qué es correcto que lo haga.

Comandos reproducibles (el fixture se genera con el script incluido):

```bash
GL=/ruta/a/gitleaks-8.30.1
cd ~/h014-work/gitleaks-test && python3 generar.py

# línea base (sin allowlist)
$GL detect --no-git --source . --report-format json --report-path /tmp/a.json

# config actual del repositorio
$GL detect --no-git --source . --config <repo>/.gitleaks.toml --report-format json --report-path /tmp/b.json

# config propuesta
$GL detect --no-git --source . --config .../propuestas/gitleaks-dona.toml --report-format json --report-path /tmp/c.json
```

---

## 5. Lo que esta evidencia NO demuestra

- No se ejecutó el workflow real de GitHub Actions con la config propuesta: la
  verificación es local con la misma versión mayor de gitleaks (8.30.1) sobre un
  fixture equivalente, no sobre el repositorio en CI.
- No se auditó el histórico completo de commits (`--no-git` escanea el árbol).
  Un secreto real borrado en el pasado seguiría en el historial y **no** está
  cubierto por esta medición.
- La decisión de aplicar el cambio corresponde a Dona-agent: esta auditoría no
  modifica repositorios auditados.
