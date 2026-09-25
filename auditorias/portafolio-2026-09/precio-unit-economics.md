# Piso económico por cuenta y por acción (punto 8, parte 2 de 2)

Sin esto, un experimento de precio puede "validar" demanda a un precio que pierde
dinero. **Es la pieza que la revisión echaba de menos.**

## Advertencia de honestidad

**Ninguna cifra de esta tabla está medida todavía.** Los costes de proveedor
(modelos, WhatsApp, Stripe, hosting) requieren las tarifas reales de las cuentas
en uso, que no están en los repositorios. Por tanto aquí **no se inventan importes**:
se fija la **estructura** del cálculo, qué hay que medir, y la **regla** que decide
si un precio es viable.

Marcarlo así es el punto: la revisión pedía unit economics *antes* de recomendar
precios, no números plausibles sin fuente.

## Coste por cuenta

```
coste_por_cuenta(mes) =
      modelos      (tokens consumidos × tarifa por token del proveedor)
    + whatsapp     (mensajes de plantilla × tarifa + conversaciones facturables)
    + stripe       (comisión por transacción + cuota fija)
    + hosting      (reparto del coste de infraestructura entre cuentas activas)
    + soporte      (minutos × coste/hora ÷ cuentas atendidas)
    + coste_de_pago_fallido (reintentos y disputas × tarifa)
```

## Coste por acción

Aplica al Action Center de Dona, donde cada acción tiene nivel de riesgo y coste:

```
coste_por_accion = coste_de_la_ejecucion + coste_del_canal_de_aprobacion
```

Lo que hay que medir por acción, no por cuenta: acciones de WhatsApp con plantilla,
llamadas a modelos en ejecuciones largas, y reintentos.

## Los tres números que hay que sacar antes de fijar precio

| # | Número | Cómo se obtiene |
|---|---|---|
| 1 | **Coste marginal por cuenta activa al mes** | Sumar la fórmula anterior sobre una muestra de cuentas reales de un mes completo |
| 2 | **Coste marginal por acción de riesgo** | Media de las acciones ejecutadas en ese mes, separadas por tipo |
| 3 | **Margen bruto por cuenta** = precio − coste 1 | Con el precio candidato |

## Regla de decisión (sin zonas grises)

| Margen bruto por cuenta | Decisión |
|---|---|
| **≥ 70 %** | El precio es viable; se puede pasar al experimento de H-D1/H-N1 |
| **50–70 %** | Viable con vigilancia: hay que fijar un techo de consumo por plan antes de vender |
| **< 50 %** | **El precio no se lanza.** Se rediseña el plan (límite de uso) o se sube el precio |
| **Negativo** | Se detiene el experimento de inmediato, sin esperar la muestra |

## Por qué esto va antes que el precio

Un plan con margen del 20 % que convierte muy bien es un negocio que crece hacia la
quiebra. Y un experimento de precio **no puede detectar** ese problema: mide
demanda, no rentabilidad. Por eso el orden es obligatorio:

1. medir los tres números;
2. aplicar la regla de margen;
3. **sólo entonces** ejecutar los experimentos de la parte 1.

## Lo que falta, explícitamente

- Las **tarifas reales** de los proveedores en uso (modelos, WhatsApp, Stripe) y el
  coste de hosting y soporte.
- Un **mes de consumo por cuenta** de Dona para calcular el coste 1.
- Confirmar si las cuentas actuales de Dona ya tienen tráfico suficiente para que la
  muestra sea alcanzable.

Nada de esto se resuelve con más auditoría de código: hace falta acceso a las
facturas y a los datos de uso. Es, por tanto, una tarea del propietario, no del
auditor — y está registrada como tal en el backlog.