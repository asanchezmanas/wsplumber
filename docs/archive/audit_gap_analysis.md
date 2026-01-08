# Audit: Log Gap Analysis (Negativo)

Este documento identifica las piezas faltantes entre la especificación teórica y la implementación real, que causan ambigüedad durante el backtesting.

## 1. Gaps de Visibilidad (Missing Logs)

| Ref     | Gap de Lógica / Visibilidad                                                                                                    | Impacto                                                                      |
| :------ | :----------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------- |
| **G01** | **Razón de Rechazo de Apertura**: Si la estrategia retorna `NO_ACTION`, el orquestador no loguea por qué (ej: spread alto).    | Difícil saber por qué un backtest no abre operaciones en periodos volátiles. |
| **G02** | **Confirmación de Neutralización**: No se informa explícitamente cuándo una `MAIN_BUY` queda neutralizada por su `HEDGE_SELL`. | No sabemos si la deuda FIFO se ha calculado correctamente en ese instante.   |
| **G03** | **Cálculo de Deuda FIFO**: No se loguea el coste (20/40 pips) en el momento de la neutralización, solo en el cierre.           | Imposible verificar la salud del "Accounting" durante el vuelo.              |
| **G04** | **Motivo de Señales**: Los logs de "Signal received" son genéricos. Deberían incluir el campo `reason` de la señal.            | Ambigüedad en múltiples señales seguidas.                                    |

## 2. Ambigüedades en Transiciones de Estado

- **PENDING ↔ ACTIVE**: El paso de ciclos a ACTIVE ocurre en el primer tick que toca una orden, pero no confirmamos si es por la BUY o la SELL.
- **Recursos Insuficientes**: Si el `RiskManager` deniega una apertura, el log es `WARNING`, pero en un backtest masivo esto podría perderse. Debería ser un evento de auditoría clave.

## 3. Próximos Pasos para Resolución

1.  **Enriquecer Logs de Orquestación**: Añadir el campo `reason` a los logs de señales.
2.  **Loguear Neutralización**: Añadir un log de "Operation neutralized, adding {cost} pips to debt".
3.  **Auditoría de Errores Silenciosos**: Asegurar que cada `return` temprano en el orquestador tenga un log de nivel `DEBUG` o `INFO`.
