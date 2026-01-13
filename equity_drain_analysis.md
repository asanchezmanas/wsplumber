# Análisis de Estancamiento de Equity y Fuga de Pips

## 🔍 Observación del Problema
Durante el backtest, se observa que:
1. El **Balance** sube constantemente (indicando que se cierran operaciones en profit).
2. El **Equity** permanece estancado o baja (indicando que la pérdida flotante está creciendo).
3. El número de **Ciclos Cerrados** sube, pero el beneficio real no se refleja en el patrimonio.

## 🔬 Hipótesis Principal: "Fuga por Teoría"
El sistema de contabilidad (`CycleAccounting`) utiliza valores **teóricos** para decidir cuándo un ciclo está sano:
- **Deuda inicial**: 20 pips fijos.
- **Fallo de recovery**: 40 pips fijos.
- **Beneficio por TP**: 80 pips fijos.

### El Error de Acumulación
Los logs de "Shadow Accounting" confirman la discrepancia:
`"real_debt": 12.0, "theoretical": 20.0, "difference": -8.0`

**Escenario de fallo:**
1. El sistema registra una deuda de **20 pips**.
2. Una operación de recovery toca TP y gana **78 pips** reales (debido a spread/slippage).
3. La contabilidad teórica dice: `Recuperado 80 (teóricos) - Deuda 20 (teóricos) = Excedente 60`.
4. El sistema **cree** que ha limpiado la deuda y tiene beneficio.
5. **Realidad del Broker**: Gaste 12 pips de deuda real, gane 78 de profit = Neto +66. 

**¿Por qué baja la equity entonces?**
Si el error fuera siempre a favor del profit real (ganar 78 vs 80 teóricos), la equity subiría menos de lo esperado, pero subiría. 

El problema real ocurre cuando la **deuda real es MAYOR** que la teórica:
- Si el stop out real de una operación neutralizada cuesta **45 pips**, pero el sistema solo registra **40 pips** de deuda.
- El sistema cierra el ciclo pensando que ha recuperado todo.
- **Resultado**: Quedan **5 pips de pérdida real** que no se han cerrado en el broker o que se han "olvidado" en el cálculo del surplus.

### 🧟 Escenario 2: Operaciones Huérfanas ("Zombie Operations")
He descubierto un fallo arquitectónico en `_close_cycle_operations_final` y evidencia masiva en los logs.

**Evidencia Técnica (Smoking Gun):**
1. **Pérdida Descontrolada:** En la cola del log he encontrado operaciones en estado `neutralized` con **870 pips de pérdida flotante** (Ticket `1001` aprox).
2. **Incapacidad de Cierre:** El contador `MTP` (Main Take Profits) marca **642 victorias**, pero `Clo` (Cycles Closed) marca **0**. Esto significa que el sistema ha ganado 642 veces pero **ningún ciclo se ha resuelto jamás**. 
3. **Versión Desactualizada:** El backtest actual está ejecutando una versión antigua del código (usa logs como `target_reached` que ya no existen en el código actual), lo que indica que el proceso lleva 1.5h corriendo con lógica buggeada que ya hemos intentado corregir en disco.

**El Problema:**
Cuando un ciclo principal (Main) se resuelve o hit TP, el sistema debería transicionar y cerrar. Sin embargo, si entra en `IN_RECOVERY`, se queda atrapado en un bucle donde los sub-ciclos de Recovery hijos tienen su propio `recovery_cycle.id` y **NUNCA son buscados ni cerrados** por el padre.

**Consecuencia:**
1. El Ciclo Main se mantiene abierto o en recovery perpetuo.
2. Las operaciones "neutralizadas" **permanecen ABIERTAS** en el broker. Al estar neutralizadas, no tienen TP/SL propio (se supone que el orquestador las cerrará).
3. Como el orquestador no las cierra, la pérdida flotante de estas posiciones sigue creciendo con la tendencia (llegando a >800 pips), mientras que el balance solo sube de 10 en 10 pips por los TPs sueltos.
4. **Resultado**: La Equity cae en picado mientras el Balance sube lentamente.

---

## 🛠️ Solución Propuesta: Contabilidad Dinámica y Cierre Recursivo (Phase 5)

Para solucionar esto, debemos eliminar los valores hardcoded y usar los **precios de ejecución reales**.

### 1. Registrar Deuda Real
En lugar de `debt_units.append(40.0)`, debemos calcular la distancia real entre el precio de entrada de la Main y el precio de entrada de la Hedge.

### 2. Registrar Profit Real
En `_handle_recovery_tp`, pasar el `op.realized_pips` real a `process_recovery_tp` en lugar del valor fijo `80.0`.

### 3. Ajustar Criterio de Cierre
El cierre automático del ciclo debe basarse en el **Equity real del ciclo** (calculado por el broker) y no solo en la suma de pips teóricos.

---

## 📝 Plan de Acción
1. **Activar `USE_DYNAMIC_DEBT = True`** en `_params.py` (necesita ser implementado completamente).
2. **Modificar `CycleAccounting.add_recovery_failure_unit`** para aceptar la pérdida real.
3. **Modificar `CycleOrchestrator`** para inyectar los pips reales al cerrar operaciones.
4. **Validar** con un test de 20k ticks antes de lanzar el de 500k.

