# Precio: de hipótesis a experimentos (punto 8, parte 1 de 2)

Responde al punto 8 de la revisión 5185022108. La crítica era: las hipótesis de
precio no eran experimentos — dejaban zonas grises, aceptaban "intención
declarada" como señal principal, y **faltaba el piso económico**. Todo eso era
cierto.

Regla de esta parte: **cada hipótesis se convierte en un experimento con cohorte,
evento, denominador, muestra mínima y regla de decisión sin zonas grises.**
Ninguna se aprueba con intención declarada sola. El piso económico está en la
parte 2.

---

## H-D1 · Precio del plan de Dona (antes: "entre 15 % y 25 %")

**Zona gris que se elimina:** "entre 15 % y 25 %" no es una decisión, es un rango
sin dueño. Se sustituye por un precio concreto por cohorte.

| Elemento | Definición |
|---|---|
| Cohorte | Cuentas nuevas de Dona durante 4 semanas, asignadas al azar a uno de 3 precios (no el mismo usuario viendo varios) |
| Precios a probar | P1, P2, P3 con 25 % de separación (los valores concretos salen del piso de la parte 2) |
| Evento primario | **Primer pago cobrado**, no "empezó el checkout" |
| Denominador | Cuentas que llegaron al muro de pago en la cohorte |
| Métrica de decisión | **Ingreso por cuenta del grupo** = (tasa de conversión × precio). No la conversión sola: bajar el precio casi siempre sube la conversión y puede bajar el ingreso |
| Muestra mínima | Calculada para detectar una diferencia de 20 % en ingreso por cuenta con potencia 80 %; si el tráfico no la alcanza, el experimento **no es concluyente** y se declara así |
| Regla de decisión | Se adopta el precio con mayor ingreso por cuenta **y** cuyo margen bruto por cuenta sea positivo según la parte 2. Empate dentro del margen de error → se mantiene el precio actual |
| Corte anticipado | Si el margen bruto por cuenta sale negativo, se detiene **sin** esperar la muestra |

**Exposición y asignación por plan:** faltaba. Se define así: cada plan declara su
precio y su límite de uso (créditos o mensajes incluidos) en la misma tabla, y el
ingreso se atribuye a **una** cuenta, no se reparte entre planes.

## H-D2 · Recargas (antes: llamadas "ingreso recurrente")

**Error corregido:** una recarga es **ingreso variable**, no recurrente. Se deja de
llamar recurrente.

| Elemento | Definición |
|---|---|
| Cohorte | Cuentas con al menos una recarga en 60 días |
| Evento primario | **Segunda recarga dentro de 60 días** (una recarga sola no prueba recurrencia) |
| Denominador | Cuentas que hicieron la primera recarga |
| Muestra mínima | La que permita distinguir "recurrencia ≥ 40 %" de "recurrencia ≤ 20 %" |
| Regla de decisión | Si la segunda recarga supera el 40 %, se puede usar en la proyección **etiquetada como variable, nunca como MRR**. Si queda por debajo del 20 %, no se proyecta |

## H-N1 · Disposición a pagar de Nova (antes: "lo pagaría")

**Error corregido:** la intención declarada sobreestima el pago real. Se sustituye
por señales **con coste real**.

| Elemento | Definición |
|---|---|
| Cohorte | Usuarios de la alpha privada, invitados a una página de precio real |
| Evento primario | **Pago, depósito reembolsable o reserva de piloto pagado.** No el clic, no una encuesta, no un "me interesa" |
| Denominador | Usuarios invitados a la página de precio |
| Muestra mínima | La alpha entera (25 usuarios) es **suficiente para desmentir, no para confirmar**: con 25 usuarios sólo se detectan diferencias grandes. Se declara ese límite |
| Regla de decisión | Con 25 usuarios: si **menos de 2** pagan o reservan, la hipótesis de precio se rechaza. Si pagan 5 o más, se pasa a la cohorte siguiente. Entre 2 y 4, **no concluyente** y se amplía la muestra |

## H-F1 · Estructura de precios de Fluvia (antes: "tres conversaciones")

**Error corregido:** tres conversaciones **no validan** una estructura de precios;
describen expectativas, no pagos.

| Elemento | Definición |
|---|---|
| Cohorte | Comercios a los que se ofrece un piloto pagado con precio explícito |
| Evento primario | **Contrato firmado o pago del piloto** |
| Denominador | Comercios a los que se presentó la oferta |
| Muestra mínima | 12 comercios presentados. Con menos, no se concluye |
| Regla de decisión | Si menos de 2 de 12 firman piloto, la estructura se descarta y se rediseña. Si 4 o más firman, se usa como base de la Fase 5 |

---

## Regla transversal (la que faltaba)

**Ninguna hipótesis se da por validada con intención declarada.** Toda señal válida
tiene coste para quien la emite: dinero pagado, depósito, contrato o reserva. Una
respuesta afirmativa en una conversación es **material para diseñar el experimento**,
no resultado del experimento.

Y el orden es obligatorio: **primero el piso económico (parte 2), después el
precio.** Un experimento de precio ejecutado antes del piso puede "validar" demanda
a un precio que pierde dinero en cada venta.