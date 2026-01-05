# El Fontanero de Wall Street
## Estrategia de Trading con Coberturas: Lógica y Filosofía Completa

---

> *"Mientras los grandes mueven millones de un lado a otro, siempre caen gotas. No competimos por el recipiente, solo ponemos el cazo debajo."*

---

## Filosofía Central

### La Metáfora del Fontanero

En el sistema financiero global, billones se mueven constantemente de un recipiente a otro. Instituciones, fondos, algoritmos... todos compitiendo por los grandes flujos. Pero en cada trasvase, inevitablemente, caen gotas.

**Nosotros no somos traders. Somos fontaneros.**

- No predecimos hacia dónde va el agua
- No luchamos por controlar el grifo
- Simplemente colocamos el cazo donde las gotas caen
- Pequeñas gotas constantes llenan el cubo

Esta estrategia representa un cambio paradigmático en el trading, basándose en principios que invierten la lógica tradicional de gestión de pérdidas y generación de ingresos. Su filosofía se fundamenta en tres pilares que trabajan en sinergia.

### Principios Fundamentales

- El sistema opera **sin Stop Loss tradicional**
- Usa **coberturas de continuación**: las pérdidas de un sell se neutralizan colocando un buy, encapsulando la pérdida a la separación en pips entre estas operaciones
- El sistema tiene tres tipos de operaciones: **principales**, **de cobertura** y **de recuperación (recovery)**

---

## Estructura de Operaciones

### Operaciones Principales
- Se colocan a **5 pips del precio**
- Take Profit de **10 pips**
- Genera un bloque de operaciones separadas entre ellas por 10 pips

### Operaciones de Cobertura
- Se activan para neutralizar la pérdida cuando una operación principal toca TP y la otra queda en contra
- Son **buy stop** para el buy stop principal y **sell stop** para sell stop principal
- Precio de entrada al nivel del TP de la operación principal opuesta

### Operaciones de Recovery
- Se colocan a **20 pips del precio**
- Take Profit de **80 pips**
- Separadas entre ellas por **40 pips**

---

## Flujo Operativo Detallado

### Escenario 1: Resolución Simple
1. Se abren dos operaciones principales (buy stop y sell stop)
2. Una se activa y llega a TP (+10 pips)
3. Se cierra la otra pendiente
4. Se reinicia otro ciclo principal

### Escenario 2: Ambas Operaciones se Activan
1. Cuando ambas principales se activan, aparecen las operaciones de cobertura
2. Buy stop con precio de entrada al nivel del TP de la operación principal
3. Sell stop con nivel de entrada en el TP del sell principal
4. Cuando una de las dos principales toque TP, se activará la operación que neutraliza las pérdidas a **20 pips** (10 de separación + 10 hasta el TP)
5. La cobertura no activada se elimina
6. Se abre un ciclo recovery para recuperar los 20 pips neutralizados

### Escenario 3: Recovery Exitoso (Primer Intento)
1. Estamos en el momento en que una operación principal (ej: buy) ha tocado TP
2. Se abre recovery: sell stop y buy stop a 20 pips del precio actual
3. El precio se mueve y toca TP (+80 pips)
4. Se elimina la orden pendiente recovery
5. Se eliminan el sell principal y el buy de cobertura
6. **Beneficio neto: +60 pips**

### Escenario 4: Recovery con Reintento
1. Se abre ciclo recovery tras TP de principal
2. El precio se mueve en dirección contraria y activa el segundo recovery
3. Se neutraliza el primer recovery activado
4. **Contabilidad actualizada:** -20 pips (ciclo inicial) + -40 pips (recovery) = -60 pips
5. Se coloca nuevo ciclo recovery adaptado al precio actual
6. El proceso se repite hasta resolución

### Cierre de Ciclos Recovery
- **Si es el primero:** Se borran la cobertura y la operación principal restantes (-20 pips)
- **Si es el segundo o mayor:** Los 80 pips de beneficio se usan para cerrar ciclos recovery antiguos (por fecha o numeración), liberando margen

---

## Consideraciones Importantes de Implementación

### Gestión de Ciclos Recovery
- **Dos formas de abrir recovery:**
  1. Específica para el primero: cuando la principal toca TP
  2. Cuando ya hay al menos un recovery en marcha: al activarse la segunda operación

### Etiquetado y Relación de Operaciones
Es crítico relacionar las operaciones entre ellas para:
- Ordenarlas correctamente
- Encontrarlas y eliminarlas conjuntamente
- No romper la lógica del sistema

**Relaciones necesarias:**
- Operación principal activada ↔ su cobertura
- Operaciones de cada ciclo recovery entre ellas
- Ciclos completos identificables para cierre conjunto

---

## Los Tres Pilares del Sistema

### 1. Flujo Continuo de Ingresos sobre Operaciones Puntuales
- **Principio:** Mantener siempre ciclos principales activos generando pequeños ingresos constantes
- **Fundamento:** La consistencia de pequeñas ganancias (10 pips) supera la volatilidad de grandes movimientos
- **Implementación:** Cuando un ciclo principal toca TP, inmediatamente se abre otro nuevo
- **Ventaja:** Flujo de caja constante independiente del estado de las Recovery

### 2. Separación Operativa: Ingresos vs Recuperación
- **Principio:** Los ciclos principales generan dinero, las Recovery recuperan pérdidas
- **Fundamento:** Cada sistema tiene su función específica y no interfieren entre sí
- **Gestión dual:** Operar nuevos ciclos mientras se gestionan Recovery pendientes
- **Resultado:** Ingresos continuos mientras se resuelven situaciones comprometidas

### 3. Neutralización Matemática Inteligente
- **Principio:** Un Recovery exitoso (80 pips) neutraliza dos niveles de Recovery perdidos
- **Fundamento:** Ratio 2:1 que permite absorber errores múltiples con una sola operación exitosa
- **Eficiencia:** El sistema se auto-balancea matemáticamente

---

## Sistema Principal: Generación de Ingresos

### Características
- **Objetivo:** 10 pips de beneficio por operación
- **Función:** Motor de ingresos constante del sistema
- **Renovación automática:** Al tocar TP, se abre inmediatamente el siguiente ciclo
- **Independencia:** Opera sin importar cuántas Recovery estén activas

### Flujo Operativo
1. **Apertura inicial:** Dos operaciones simultáneas (compra/venta) con TP a 10 pips
2. **Resolución:** Una toca TP (+10 pips), la otra requiere cobertura
3. **Renovación inmediata:** Se abre nuevo ciclo principal desde niveles actuales
4. **Continuidad:** El proceso se repite indefinidamente

### Filosofía
> *"Pequeños ingresos constantes construyen grandes fortunas"*

- Enfoque en volumen de operaciones exitosas, no en tamaño de ganancias
- Capitalización de la predictibilidad a corto plazo
- Generación de flujo de caja que sostiene toda la estrategia

---

## Sistema Recovery: Gestión de Pérdidas

### Características
- **Objetivo:** 80 pips de beneficio por operación
- **Función:** Recuperar pérdidas de ciclos principales que requirieron cobertura
- **Separación:** 40 pips entre niveles para evitar activación simultánea
- **Paciencia:** Pueden permanecer abiertas días o semanas

### Mecánica de Recovery
1. **Activación:** Cuando un ciclo principal requiere cobertura, se programa Recovery
2. **Posicionamiento:** Se coloca a 20 pips del precio actual
3. **Gestión:** Se mantiene hasta que el mercado la ejecute favorablemente
4. **Neutralización:** Al ejecutarse con éxito, cancela dos niveles de pérdidas

### Filosofía
> *"El tiempo cura las heridas del trading"*

- Los mercados no permanecen en una dirección indefinidamente
- La paciencia convierte pérdidas temporales en oportunidades de recuperación
- 80 pips de movimiento ocurren naturalmente en todos los marcos temporales

---

## Gestión Integral de Ambos Sistemas

### Operativa Simultánea

**Mientras Recovery están activas:**
- Ciclos principales continúan operando normalmente
- Generación de ingresos no se detiene por Recovery pendientes
- Se monitorean ambos sistemas independientemente
- Los ingresos principales compensan el capital comprometido en Recovery

**Cuando Recovery se ejecutan:**
- Eliminación por prioridad: primero Recovery perdidas, después la principal si es rentable
- Limpieza progresiva: Recovery acumuladas se eliminan sistemáticamente por equivalencia
- Posible cierre total si el beneficio lo permite
- Liberación optimizada de margen cuando se cierran ciclos completos

### Control de Exposición
- **Medición:** Porcentaje del capital total comprometido en Recovery
- **Umbral de pausa:** Cuando la exposición es excesiva, se pausan nuevos ciclos principales
- **Reactivación:** Al cerrarse Recovery exitosas, se libera capacidad
- **Recalibración:** Nuevos niveles se calculan desde precios actuales (±20 pips)

---

## Comportamiento Según Condiciones de Mercado

### Mercados Trending (Condición Ideal)

**Impacto en Recovery:**
- Resolución rápida de Recovery existentes
- Nuevas Recovery se resuelven en 1-2 intentos
- Liberación rápida de capital
- Sistema entra en modo de máxima eficiencia

**Impacto en ciclos principales:**
- Alta frecuencia de apertura/cierre
- Mayor probabilidad de acierto direccional
- Flujo de 10 pips se multiplica

### Mercados Laterales (Tolerancia Estructural)

**Protección de Recovery en límites:**
- Separación de 40 pips protege Recovery en extremos del rango
- No se activan por volatilidad interna del lateral
- Esperan que el mercado rompa el rango

**Gestión de Recovery centrales:**
- Acumulación controlada: pueden activarse ambas direcciones
- Recolocación desde nuevos niveles al activarse ambas
- Daño limitado matemáticamente
- Sistema diseñado para tolerar acumulación

**Continuidad de ciclos principales:**
- Los laterales también generan movimientos de 10 pips
- Flujo de caja continúa
- Ingresos principales sostienen Recovery acumuladas

### Asunción Fundamental
> *"Los mercados NO permanecen laterales indefinidamente"*

- Los rangos son condiciones temporales, no permanentes
- Estadísticamente, los mercados desarrollan tendencias que resuelven Recovery
- El tiempo trabaja a favor del sistema

---

## Matemática de la Sostenibilidad

### Ratio Riesgo/Recompensa 2:1

**En Recovery:**
- Ganancia: 80 pips por Recovery exitosa
- Pérdida acumulada: ~40 pips promedio por dos niveles neutralizados
- Resultado: cada Recovery exitosa supera matemáticamente dos fallidas

**Implicaciones:**
- Objetivo de ciclo: +20 pips netos mínimos por ciclo completo
- Primer nivel de Recovery exitoso: 80 - 20 = **+60 pips netos**
- Tasa de acierto requerida: solo **33.3%** para superar breakeven
- Tolerancia a errores: puede fallar múltiples Recovery y recuperar con una exitosa

### Estadística Operativa
- **70-80%** de Recovery se resuelven en 1-2 intentos (condiciones normales)
- Situaciones de acumulación: solo 20-30% de los casos
- Duración promedio: días o semanas, no meses

---

## Gestión Dinámica del Capital

### Métricas Clave a Monitorear
- Porcentaje de cuenta comprometida en Recovery activas
- Número de Recovery simultáneas por par
- Flujo de ingresos de ciclos principales
- Tiempo promedio de resolución de Recovery

### Decisiones Operativas Automáticas

**Pausa de nuevos ciclos:**
- Trigger: compromiso de cuenta supera umbral definido
- Acción: suspender apertura de nuevos ciclos
- Mantenimiento: continuar gestionando Recovery activas

**Reactivación:**
- Trigger: cierre exitoso de Recovery que libera margen
- Recalibración desde precio actual ±20 pips
- Reanudación de ciclos principales

---

## Análisis de Riesgos y Contraargumentos

### Objeción 1: "La neutralización congela pérdidas, no las elimina"

**Preocupación:** El capital queda comprometido, se acumulan swaps, el margen no se libera.

**Respuesta:**
- Los swaps y comisiones están incluidos en el cálculo de los 80 pips de TP del recovery
- El flujo continuo de ciclos principales (5-15 operaciones diarias = 5-15€) compensa el tiempo de espera
- La neutralización permite que una pérdida flotante no crezca mientras se espera la resolución

**Estado:** ✅ Resuelto

---

### Objeción 2: "Acumulación progresiva en mercado lateral"

**Preocupación:** En un rango oscilante, podrían activarse múltiples niveles de recovery sin que ninguno toque los 80 pips de TP.

**Respuesta:**
- La separación de **40 pips** entre recovery limita las activaciones
- En un rango típico de 60 pips, solo se activarían 1-2 niveles, no una cascada
- Posible implementación de **trailing stop** para detectar rangos y anular errores antes de entrar en coberturas
- Solo se activan recovery si **ambas** operaciones principales se activan; en rango, las de los extremos quedan protegidas

**Estado:** ✅ Resuelto

---

### Objeción 3: "Movimientos fuertes de 400+ pips"

**Preocupación:** Un movimiento brusco podría activar todos los niveles de recovery en una dirección.

**Respuesta:**
- En mercados tendenciales, **solo se activan operaciones en una dirección**
- Los buy stops no se tocan si el mercado cae; los sell stops no se tocan si sube
- Las operaciones "atrapadas" en la dirección contraria se van resolviendo con las coberturas
- No hay cascada de recovery porque no se activan ambos lados
- Los movimientos fuertes **favorecen** al sistema: resuelven recovery pendientes y los ciclos principales en la dirección correcta tocan TP rápidamente

**Estado:** ✅ Resuelto

---

### Objeción 4: "¿Son asumibles las pérdidas potenciales?"

**Preocupación:** 40€ comprometidos, ¿es mucho?

**Respuesta:**
- **Cálculo de capacidad:** Con 2.000€ de cuenta por par, hay margen para ~300 operaciones comprometidas
- **Escenario conservador:** 100 operaciones = 400€ comprometidos sobre 1.000€, manejable
- **Recovery de 80 pips = 8€** de beneficio cada una
- **No usa martingala:** el crecimiento de exposición es lineal, no exponencial
- **Comparativa:** Bots tradicionales con martingala habrían arruinado la cuenta en escenarios similares

**Estado:** ✅ Resuelto

---

### Objeción 5: Correlación entre pares

**Preocupación:** Si se operan varios pares simultáneamente (EUR/USD, GBP/USD), un movimiento del dólar puede activar recovery en todos a la vez.

**Respuesta:**
- Seleccionar **pares descorrelacionados entre sí**
- Calcular la **correlación del portfolio total** antes de añadir nuevos pares
- Evitar que un evento único (ej: movimiento del USD) afecte a todos los pares simultáneamente
- Diversificación real: si un par sufre, los otros no necesariamente

**Estado:** ✅ Resuelto

---

### Objeción 6: Eventos de alta volatilidad

**Preocupación:** NFP, decisiones de tipos de interés, etc. pueden generar gaps que salten los 40 pips de separación y activen ambos lados instantáneamente.

**Respuesta:**
- Los eventos de volatilidad están **contemplados en el backtest**
- **Pausar nuevas operaciones principales** durante eventos
- **Mantener los recovery activos**: los eventos de volatilidad ayudan a romper rangos y resolver recovery pendientes
- Los movimientos bruscos son aliados del sistema recovery, no enemigos

**Estado:** ✅ Resuelto

---

### Objeción 7: Variables del broker

**Preocupación:** Spreads variables, slippage, ejecución... ¿Cuánto margen de los 10 pips de TP se come el spread en condiciones reales?

**Respuesta:**
- Uso de **brokers ECN** (Darwinex, etc.) para mejor ejecución y spreads ajustados
- Implementar **controlador de spreads**: no abrir operaciones cuando el spread supere un umbral definido
- Evita entrar en momentos de baja liquidez o alta volatilidad con spreads inflados

**Estado:** ✅ Resuelto

---

### Objeción 8: Gaps de fin de semana

**Preocupación:** El mercado cierra el viernes y abre el lunes con un gap que salta niveles programados.

**Respuesta:**
- **Aceptar los gaps como parte del sistema**
- Tratarlos como **recovery adicionales**: si un gap activa una operación, se gestiona con la misma lógica
- Implementar **fondo de reserva** (ver sección Money Management) para absorber impactos
- Los gaps también pueden ser favorables y resolver recovery pendientes

**Estado:** ✅ Resuelto

---

## Money Management: Fondo de Reserva

### Principio
No todo el beneficio es ganancia inmediata. Una parte se destina a fortalecer el sistema contra eventos imprevistos.

### Regla del 20%
**El 20% de los beneficios de recovery se destina a un fondo de reserva.**

### Destino del Fondo
- Cubrir **gaps de fin de semana**
- Absorber **drawdowns temporales**
- Proteger contra **eventos inesperados** (declaraciones políticas, cisnes negros, etc.)
- Mantener la cuenta con **drawdown controlado**

### Acumulación
- **Semanal o mensual**, según preferencia
- El fondo crece mientras el sistema opera normalmente
- No se toca salvo eventos extraordinarios

### Matemática del Fondo

**Ejemplo con 10 recovery/semana:**
| Período   | Recovery | Beneficio bruto | 20% a reserva | Fondo acumulado |
| --------- | -------- | --------------- | ------------- | --------------- |
| Semana 1  | 10 × 8€  | 80€             | 16€           | 16€             |
| Semana 2  | 10 × 8€  | 80€             | 16€           | 32€             |
| Semana 3  | 10 × 8€  | 80€             | 16€           | 48€             |
| Semana 4  | 10 × 8€  | 80€             | 16€           | 64€             |
| **Mes 1** |          | **320€**        |               | **64€**         |
| **Mes 3** |          | **960€**        |               | **~200€**       |

### Beneficio Neto Real
- Beneficio bruto recovery: 80€/semana
- Menos 20% reserva: -16€
- **Beneficio neto: 64€/semana** + ciclos principales (5-15€/día)

### Ventaja Psicológica
- Operas sabiendo que hay un colchón
- Los gaps no generan pánico
- Permite mantener la estrategia sin decisiones emocionales

---

## Gestión de Correlación del Portfolio

### Principio
Un portfolio diversificado no depende de un único factor de riesgo.

### Implementación
1. **Calcular correlación** entre pares antes de añadirlos
2. **Evitar pares altamente correlacionados** (ej: EUR/USD y GBP/USD tienen correlación positiva alta)
3. **Buscar descorrelación** o correlación negativa
4. **Revisar periódicamente**: las correlaciones cambian con el tiempo

### Pares Típicamente Descorrelacionados
- EUR/USD vs USD/JPY (correlación variable)
- GBP/USD vs AUD/USD (moderada)
- EUR/JPY vs USD/CAD (baja)

*Nota: Verificar correlaciones actuales antes de implementar*

### Beneficio
- Un evento que afecta al USD no destruye todo el portfolio
- Las recovery de un par pueden compensar drawdown de otro
- Mayor estabilidad general del sistema

---

## Resultados de Pruebas Manuales

### Condiciones de Prueba
- **Pares:** GBP/USD y EUR/USD
- **Modalidad:** Manual
- **Observaciones:** Las operaciones se acumulan pero también se van recuperando

### Resultados
- **TPs diarios:** Entre 5-15 operaciones
- **Beneficio diario:** 5-15€ (con lotaje de 0.01)
- **Comportamiento:** Flujo constante de pequeños beneficios mientras se gestionan recovery pendientes

---

## Ventajas Competitivas

### 1. Doble Flujo de Ingresos
- **Primario:** Ingresos constantes de ciclos principales (10 pips)
- **Secundario:** Recovery que neutralizan pérdidas acumuladas (80 pips)
- Ambos sistemas se complementan sin interferir

### 2. Resistencia a Condiciones Adversas
- **Trending:** Condición ideal para ambos sistemas
- **Lateral:** Tolerancia estructural con continuidad de ingresos
- **Volatilidad:** Los 40 pips de separación proporcionan cushion natural

### 3. Escalabilidad Inteligente
- Crecimiento lineal, no exponencial como martingala
- Adaptable a cuentas pequeñas y grandes
- Matemática que permite crecimiento sostenible

### 4. Gestión Emocional Superior
- Separación mental: ingresos vs recuperación son procesos independientes
- Flujo positivo: ingresos constantes mantienen moral alta
- Paciencia estructurada: recovery no generan presión de cierre inmediato

---

## Implementación Práctica

### Fase 1: Inicio
1. Abrir primer ciclo principal: dos operaciones (compra/venta) con TP a 10 pips
2. Monitorear ejecución
3. Gestionar la no ejecutada: si requiere cobertura, programar Recovery

### Fase 2: Operativa Normal
1. Renovación automática: cada TP genera nuevo ciclo
2. Gestión de Recovery: monitorear sin intervenir, esperar ejecución natural
3. Control de exposición: vigilar porcentaje comprometido

### Fase 3: Gestión Avanzada
1. Pausa inteligente cuando exposición es alta
2. Neutralización al ejecutarse Recovery
3. Reactivación desde condiciones actuales

### Fase 4: Optimización
1. Análisis de patrones: identificar condiciones favorables
2. Ajuste de parámetros según experiencia
3. Expansión controlada según resultados

---

## Conclusión

Esta estrategia convierte la imperfección natural del mercado en un generador constante de ingresos mediante:

1. **Los errores son oportunidades estructuradas**, no fracasos
2. **Pequeños ingresos constantes** superan grandes ganancias esporádicas
3. **El tiempo es un aliado**, no un enemigo
4. **La paciencia es una herramienta operativa**, no solo una virtud

> *Es trading simbiótico con el mercado en lugar de trading combativo contra el mercado*

### La Filosofía del Fontanero

No hace falta ser el más listo, el más rápido ni el mejor capitalizado. Solo hace falta:
- **Estar posicionado** donde el flujo es inevitable
- **Ser paciente** mientras las gotas caen
- **Mantener el cazo** en su sitio, sin moverlo por ansiedad
- **Vaciar el cubo** regularmente (tomar beneficios)

Los grandes seguirán moviendo sus millones. Nosotros seguiremos recogiendo gotas.

**Gota a gota, se llena el cubo.**

---

## Base de Datos: Supabase (PostgreSQL)

### Por qué Supabase

- **Zero gestión**: Fully managed, backups automáticos, escalado automático
- **Real-time incluido**: WebSockets para dashboard sin código adicional
- **API REST automática**: Reduce código de infraestructura
- **JSONB nativo**: Flexibilidad para datos que evolucionan
- **Auth incluido**: Si necesitas multi-usuario en el futuro
- **Edge Functions**: Para lógica serverless si necesitas

### Esquema de Base de Datos

```sql
-- ============================================
-- ESQUEMA PRINCIPAL: El Fontanero de Wall Street
-- ============================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLA: cycles (Ciclos principales y recovery)
-- ============================================
CREATE TABLE cycles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(50) UNIQUE NOT NULL,  -- "EURUSD_001"
    pair VARCHAR(10) NOT NULL,
    cycle_type VARCHAR(20) NOT NULL,  -- 'main', 'recovery'
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    parent_cycle_id UUID REFERENCES cycles(id),
    recovery_level INTEGER DEFAULT 0,
    
    -- Contabilidad
    pips_locked DECIMAL(10,2) DEFAULT 0,
    total_cost DECIMAL(10,2) DEFAULT 0,
    realized_profit DECIMAL(10,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    
    -- Metadata flexible (JSONB)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Índices para búsquedas frecuentes
    CONSTRAINT valid_cycle_type CHECK (cycle_type IN ('main', 'recovery')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'hedged', 'in_recovery', 'closed', 'paused'))
);

-- Índices optimizados
CREATE INDEX idx_cycles_pair_status ON cycles(pair, status);
CREATE INDEX idx_cycles_created ON cycles(created_at DESC);
CREATE INDEX idx_cycles_parent ON cycles(parent_cycle_id) WHERE parent_cycle_id IS NOT NULL;

-- ============================================
-- TABLA: operations (Todas las operaciones)
-- ============================================
CREATE TABLE operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(50) UNIQUE NOT NULL,  -- "EURUSD_001_BUY"
    cycle_id UUID NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    
    -- Identificación
    pair VARCHAR(10) NOT NULL,
    op_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Precios
    entry_price DECIMAL(10,5) NOT NULL,
    tp_price DECIMAL(10,5) NOT NULL,
    actual_entry_price DECIMAL(10,5),  -- Precio real de ejecución
    actual_close_price DECIMAL(10,5),
    
    -- Tamaño
    lot_size DECIMAL(5,2) NOT NULL,
    pips_target INTEGER NOT NULL,
    
    -- Resultado
    profit_pips DECIMAL(10,2) DEFAULT 0,
    profit_eur DECIMAL(10,2) DEFAULT 0,
    
    -- Costos
    commission_open DECIMAL(10,2) DEFAULT 0,
    commission_close DECIMAL(10,2) DEFAULT 0,
    swap_total DECIMAL(10,2) DEFAULT 0,
    slippage_pips DECIMAL(5,2) DEFAULT 0,
    
    -- Broker
    broker_ticket VARCHAR(50),
    broker_response JSONB,
    
    -- Relaciones
    linked_operation_id UUID REFERENCES operations(id),
    recovery_id VARCHAR(50),  -- "REC_EURUSD_001_001"
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT valid_op_type CHECK (op_type IN (
        'main_buy', 'main_sell',
        'hedge_buy', 'hedge_sell', 
        'recovery_buy', 'recovery_sell'
    )),
    CONSTRAINT valid_op_status CHECK (status IN (
        'pending', 'active', 'tp_hit', 'neutralized', 'closed', 'cancelled'
    ))
);

-- Índices optimizados
CREATE INDEX idx_operations_cycle ON operations(cycle_id);
CREATE INDEX idx_operations_status ON operations(status) WHERE status IN ('pending', 'active');
CREATE INDEX idx_operations_pair_type ON operations(pair, op_type);
CREATE INDEX idx_operations_broker_ticket ON operations(broker_ticket) WHERE broker_ticket IS NOT NULL;
CREATE INDEX idx_operations_created ON operations(created_at DESC);

-- ============================================
-- TABLA: checkpoints (Estado del sistema)
-- ============================================
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Estado completo en JSONB (flexible, versionable)
    state JSONB NOT NULL,
    
    -- Metadata
    version VARCHAR(10) NOT NULL,
    config_hash VARCHAR(64),
    trigger_reason VARCHAR(50),  -- 'periodic', 'before_order', 'manual'
    
    -- Validación
    cycles_count INTEGER,
    operations_count INTEGER,
    checksum VARCHAR(64)
);

CREATE INDEX idx_checkpoints_created ON checkpoints(created_at DESC);

-- ============================================
-- TABLA: reconciliation_log
-- ============================================
CREATE TABLE reconciliation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Resultados
    local_operations INTEGER,
    broker_operations INTEGER,
    matched INTEGER,
    discrepancies JSONB,
    actions_taken JSONB,
    
    -- Status
    success BOOLEAN,
    error_message TEXT
);

CREATE INDEX idx_reconciliation_created ON reconciliation_log(created_at DESC);

-- ============================================
-- TABLA: metrics_daily (Métricas agregadas)
-- ============================================
CREATE TABLE metrics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    pair VARCHAR(10),  -- NULL = total
    
    -- Ciclos
    cycles_opened INTEGER DEFAULT 0,
    cycles_closed INTEGER DEFAULT 0,
    recovery_created INTEGER DEFAULT 0,
    
    -- Resultado
    main_tps_hit INTEGER DEFAULT 0,
    recovery_tps_hit INTEGER DEFAULT 0,
    pips_gross DECIMAL(10,2) DEFAULT 0,
    pips_net DECIMAL(10,2) DEFAULT 0,
    profit_eur DECIMAL(10,2) DEFAULT 0,
    
    -- Costos
    total_commissions DECIMAL(10,2) DEFAULT 0,
    total_swaps DECIMAL(10,2) DEFAULT 0,
    total_slippage DECIMAL(10,2) DEFAULT 0,
    
    -- Reserva
    to_reserve_fund DECIMAL(10,2) DEFAULT 0,
    
    -- Riesgo
    max_drawdown_pips DECIMAL(10,2) DEFAULT 0,
    max_concurrent_operations INTEGER DEFAULT 0,
    max_exposure_percent DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(date, pair)
);

CREATE INDEX idx_metrics_date ON metrics_daily(date DESC);

-- ============================================
-- TABLA: reserve_fund (Fondo de reserva)
-- ============================================
CREATE TABLE reserve_fund (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    transaction_type VARCHAR(20) NOT NULL,  -- 'deposit', 'withdrawal', 'gap_coverage'
    amount DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2) NOT NULL,
    
    -- Referencia
    source_operation_id UUID REFERENCES operations(id),
    reason TEXT,
    
    CONSTRAINT valid_transaction_type CHECK (transaction_type IN (
        'deposit', 'withdrawal', 'gap_coverage', 'drawdown_coverage', 'adjustment'
    ))
);

CREATE INDEX idx_reserve_fund_created ON reserve_fund(created_at DESC);

-- ============================================
-- TABLA: alerts (Sistema de alertas)
-- ============================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    severity VARCHAR(20) NOT NULL,  -- 'info', 'warning', 'critical'
    alert_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    
    -- Contexto
    pair VARCHAR(10),
    cycle_id UUID REFERENCES cycles(id),
    operation_id UUID REFERENCES operations(id),
    metadata JSONB,
    
    -- Estado
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100)
);

CREATE INDEX idx_alerts_unacknowledged ON alerts(created_at DESC) 
    WHERE acknowledged = FALSE;

-- ============================================
-- TABLA: config_history (Historial de configuración)
-- ============================================
CREATE TABLE config_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    config_hash VARCHAR(64) NOT NULL,
    config JSONB NOT NULL,
    
    -- Quién/por qué
    changed_by VARCHAR(100),
    change_reason TEXT
);

CREATE INDEX idx_config_history_created ON config_history(created_at DESC);

-- ============================================
-- TABLA: outbox (Patrón Outbox para consistencia)
-- ============================================
CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_type VARCHAR(50) NOT NULL,  -- 'place_order', 'cancel_order', 'close_position'
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,
    error_message TEXT,
    
    CONSTRAINT valid_outbox_status CHECK (status IN (
        'pending', 'processing', 'completed', 'failed', 'dead_letter'
    ))
);

CREATE INDEX idx_outbox_pending ON outbox(created_at) 
    WHERE status = 'pending';
CREATE INDEX idx_outbox_dead_letter ON outbox(created_at)
    WHERE status = 'dead_letter';
CREATE INDEX idx_outbox_next_retry ON outbox(next_retry_at)
    WHERE status = 'pending' AND next_retry_at IS NOT NULL;

-- ============================================
-- TABLA: error_log (Registro de errores)
-- ============================================
CREATE TABLE error_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    severity VARCHAR(20) NOT NULL,  -- 'warning', 'error', 'critical'
    component VARCHAR(50),          -- 'broker', 'database', 'trading_engine'
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    
    -- Contexto
    correlation_id VARCHAR(50),
    operation_id VARCHAR(50),
    cycle_id UUID REFERENCES cycles(id),
    operation_ref_id UUID REFERENCES operations(id),
    
    -- Metadata
    metadata JSONB,
    
    -- Resolución
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX idx_error_log_unresolved ON error_log(created_at DESC) 
    WHERE resolved = FALSE;
CREATE INDEX idx_error_log_severity ON error_log(severity, created_at DESC);
CREATE INDEX idx_error_log_component ON error_log(component, created_at DESC);

-- ============================================
-- TABLA: connection_status (Estado de conexiones)
-- ============================================
CREATE TABLE connection_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component VARCHAR(50) NOT NULL UNIQUE,  -- 'broker_mt5', 'broker_darwinex', 'supabase'
    status VARCHAR(20) NOT NULL,            -- 'connected', 'disconnected', 'reconnecting'
    last_connected TIMESTAMPTZ,
    last_disconnected TIMESTAMPTZ,
    reconnect_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    latency_ms INTEGER,
    metadata JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLA: circuit_breaker_status
-- ============================================
CREATE TABLE circuit_breaker_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    state VARCHAR(20) NOT NULL,  -- 'closed', 'open', 'half_open'
    failures INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    total_blocked INTEGER DEFAULT 0,
    last_failure_at TIMESTAMPTZ,
    last_state_change TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLA: system_events (Eventos del sistema)
-- ============================================
CREATE TABLE system_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    metadata JSONB,
    
    -- Tipos: 'startup', 'shutdown', 'reconnection', 'circuit_breaker_change', 
    --        'reconciliation', 'emergency_stop', 'config_change'
    
    CONSTRAINT valid_event_type CHECK (event_type IN (
        'startup', 'shutdown', 'graceful_shutdown', 'emergency_stop',
        'reconnection_started', 'reconnection_success', 'reconnection_failed',
        'circuit_breaker_open', 'circuit_breaker_close',
        'reconciliation_started', 'reconciliation_completed', 'reconciliation_failed',
        'config_change', 'checkpoint_created', 'state_recovered',
        'dead_letter_added', 'dead_letter_resolved'
    ))
);

CREATE INDEX idx_system_events_type ON system_events(event_type, created_at DESC);
CREATE INDEX idx_system_events_recent ON system_events(created_at DESC);

-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Vista: Estado actual del sistema
CREATE VIEW v_system_status AS
SELECT 
    (SELECT COUNT(*) FROM cycles WHERE status = 'active') as active_cycles,
    (SELECT COUNT(*) FROM cycles WHERE status = 'in_recovery') as cycles_in_recovery,
    (SELECT COUNT(*) FROM operations WHERE status = 'active') as active_operations,
    (SELECT COUNT(*) FROM operations WHERE status = 'pending') as pending_operations,
    (SELECT SUM(pips_locked) FROM cycles WHERE status != 'closed') as total_pips_locked,
    (SELECT balance_after FROM reserve_fund ORDER BY created_at DESC LIMIT 1) as reserve_fund_balance,
    (SELECT created_at FROM checkpoints ORDER BY created_at DESC LIMIT 1) as last_checkpoint;

-- Vista: Resumen por par
CREATE VIEW v_pair_summary AS
SELECT 
    pair,
    COUNT(*) FILTER (WHERE status = 'active') as active_cycles,
    COUNT(*) FILTER (WHERE status = 'in_recovery') as in_recovery,
    SUM(pips_locked) FILTER (WHERE status != 'closed') as pips_locked,
    COUNT(*) FILTER (WHERE status = 'closed' AND closed_at > NOW() - INTERVAL '24 hours') as closed_today
FROM cycles
GROUP BY pair;

-- Vista: Operaciones activas con detalle
CREATE VIEW v_active_operations AS
SELECT 
    o.external_id,
    o.pair,
    o.op_type,
    o.status,
    o.entry_price,
    o.tp_price,
    o.lot_size,
    o.created_at,
    o.activated_at,
    c.external_id as cycle_id,
    c.cycle_type,
    c.recovery_level
FROM operations o
JOIN cycles c ON o.cycle_id = c.id
WHERE o.status IN ('pending', 'active')
ORDER BY o.created_at DESC;

-- Vista: Errores sin resolver
CREATE VIEW v_unresolved_errors AS
SELECT 
    id,
    created_at,
    severity,
    component,
    error_type,
    error_message,
    correlation_id,
    operation_id,
    metadata
FROM error_log
WHERE resolved = FALSE
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'error' THEN 2 
        WHEN 'warning' THEN 3 
        ELSE 4 
    END,
    created_at DESC;

-- Vista: Estado de conexiones
CREATE VIEW v_connection_health AS
SELECT 
    component,
    status,
    last_connected,
    last_disconnected,
    reconnect_attempts,
    latency_ms,
    CASE 
        WHEN status = 'connected' AND latency_ms < 1000 THEN 'healthy'
        WHEN status = 'connected' AND latency_ms >= 1000 THEN 'degraded'
        WHEN status = 'reconnecting' THEN 'recovering'
        ELSE 'unhealthy'
    END as health,
    updated_at
FROM connection_status;

-- Vista: Dead letter queue pendiente
CREATE VIEW v_dead_letter_queue AS
SELECT 
    id,
    operation_type,
    payload,
    attempts,
    created_at,
    error_message
FROM outbox
WHERE status = 'dead_letter'
ORDER BY created_at DESC;

-- Vista: Dashboard de salud del sistema
CREATE VIEW v_system_health_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM cycles WHERE status = 'active') as active_cycles,
    (SELECT COUNT(*) FROM operations WHERE status IN ('pending', 'active')) as active_operations,
    (SELECT COUNT(*) FROM error_log WHERE resolved = FALSE AND severity = 'critical') as critical_errors,
    (SELECT COUNT(*) FROM error_log WHERE resolved = FALSE AND severity = 'error') as errors,
    (SELECT COUNT(*) FROM outbox WHERE status = 'dead_letter') as dead_letters,
    (SELECT COUNT(*) FROM circuit_breaker_status WHERE state = 'open') as open_circuit_breakers,
    (SELECT COUNT(*) FROM connection_status WHERE status != 'connected') as disconnected_components,
    (SELECT balance_after FROM reserve_fund ORDER BY created_at DESC LIMIT 1) as reserve_fund_balance,
    (SELECT created_at FROM checkpoints ORDER BY created_at DESC LIMIT 1) as last_checkpoint;

-- ============================================
-- FUNCIONES
-- ============================================

-- Función: Calcular balance de un ciclo
CREATE OR REPLACE FUNCTION calculate_cycle_balance(p_cycle_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_balance DECIMAL;
BEGIN
    SELECT COALESCE(SUM(profit_pips - commission_open - commission_close - swap_total), 0)
    INTO v_balance
    FROM operations
    WHERE cycle_id = p_cycle_id;
    
    RETURN v_balance;
END;
$$ LANGUAGE plpgsql;

-- Función: Obtener siguiente ID de ciclo
CREATE OR REPLACE FUNCTION get_next_cycle_id(p_pair VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) + 1 INTO v_count
    FROM cycles
    WHERE pair = p_pair;
    
    RETURN p_pair || '_' || LPAD(v_count::TEXT, 3, '0');
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY (opcional, para multi-usuario)
-- ============================================
-- ALTER TABLE cycles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE operations ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can only see their own data" ON cycles
--     FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger: Actualizar métricas diarias al cerrar operación
CREATE OR REPLACE FUNCTION update_daily_metrics()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'closed' AND OLD.status != 'closed' THEN
        INSERT INTO metrics_daily (date, pair, cycles_closed, pips_net, profit_eur)
        VALUES (CURRENT_DATE, NEW.pair, 0, NEW.profit_pips, NEW.profit_eur)
        ON CONFLICT (date, pair) DO UPDATE SET
            pips_net = metrics_daily.pips_net + NEW.profit_pips,
            profit_eur = metrics_daily.profit_eur + NEW.profit_eur;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_metrics
AFTER UPDATE ON operations
FOR EACH ROW EXECUTE FUNCTION update_daily_metrics();

-- Trigger: Crear alerta si drawdown alto
CREATE OR REPLACE FUNCTION check_drawdown_alert()
RETURNS TRIGGER AS $$
DECLARE
    v_total_locked DECIMAL;
BEGIN
    SELECT SUM(pips_locked) INTO v_total_locked
    FROM cycles WHERE status != 'closed';
    
    IF v_total_locked > 300 THEN
        INSERT INTO alerts (severity, alert_type, message, metadata)
        VALUES (
            'warning',
            'high_drawdown',
            'Pips locked alto: ' || v_total_locked,
            jsonb_build_object('pips_locked', v_total_locked)
        );
    END IF;
    
    IF v_total_locked > 500 THEN
        INSERT INTO alerts (severity, alert_type, message, metadata)
        VALUES (
            'critical',
            'critical_drawdown',
            'CRÍTICO: Pips locked muy alto: ' || v_total_locked,
            jsonb_build_object('pips_locked', v_total_locked)
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_drawdown
AFTER INSERT OR UPDATE ON cycles
FOR EACH ROW EXECUTE FUNCTION check_drawdown_alert();
```

---

### Repositorio con Supabase

```python
# infrastructure/persistence/supabase_repo.py
from supabase import create_client, Client
from typing import List, Optional, Dict
from datetime import datetime
import os

class SupabaseRepository:
    """Repositorio usando Supabase (PostgreSQL)"""
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        self.client: Client = create_client(url, key)
    
    # ==================
    # CYCLES
    # ==================
    
    async def save_cycle(self, cycle: Cycle) -> str:
        """Guarda o actualiza un ciclo"""
        data = {
            'external_id': cycle.id,
            'pair': cycle.pair,
            'cycle_type': cycle.cycle_type.value,
            'status': cycle.status.value,
            'parent_cycle_id': cycle.parent_cycle_id,
            'recovery_level': cycle.recovery_level,
            'pips_locked': cycle.pips_locked,
            'metadata': cycle.metadata or {}
        }
        
        result = self.client.table('cycles').upsert(
            data, 
            on_conflict='external_id'
        ).execute()
        
        return result.data[0]['id']
    
    async def get_cycle(self, external_id: str) -> Optional[Cycle]:
        """Obtiene un ciclo por ID externo"""
        result = self.client.table('cycles').select('*').eq(
            'external_id', external_id
        ).execute()
        
        if not result.data:
            return None
        
        return self._row_to_cycle(result.data[0])
    
    async def get_active_cycles(self, pair: str = None) -> List[Cycle]:
        """Obtiene ciclos activos"""
        query = self.client.table('cycles').select('*').in_(
            'status', ['active', 'hedged', 'in_recovery']
        )
        
        if pair:
            query = query.eq('pair', pair)
        
        result = query.order('created_at', desc=True).execute()
        return [self._row_to_cycle(row) for row in result.data]
    
    # ==================
    # OPERATIONS
    # ==================
    
    async def save_operation(self, operation: Operation) -> str:
        """Guarda o actualiza una operación"""
        data = {
            'external_id': operation.id,
            'cycle_id': await self._get_cycle_uuid(operation.cycle_id),
            'pair': operation.pair,
            'op_type': operation.op_type.value,
            'status': operation.status.value,
            'entry_price': float(operation.entry_price),
            'tp_price': float(operation.tp_price),
            'lot_size': float(operation.lot_size),
            'pips_target': operation.pips_target,
            'broker_ticket': operation.broker_ticket,
            'linked_operation_id': operation.linked_operation_id,
            'recovery_id': operation.recovery_id
        }
        
        result = self.client.table('operations').upsert(
            data,
            on_conflict='external_id'
        ).execute()
        
        return result.data[0]['id']
    
    async def get_pending_operations(self, pair: str = None) -> List[Operation]:
        """Obtiene operaciones pendientes"""
        query = self.client.table('operations').select('*').eq('status', 'pending')
        
        if pair:
            query = query.eq('pair', pair)
        
        result = query.execute()
        return [self._row_to_operation(row) for row in result.data]
    
    async def get_active_operations(self, pair: str = None) -> List[Operation]:
        """Obtiene operaciones activas"""
        query = self.client.table('operations').select('*').eq('status', 'active')
        
        if pair:
            query = query.eq('pair', pair)
        
        result = query.execute()
        return [self._row_to_operation(row) for row in result.data]
    
    # ==================
    # CHECKPOINTS
    # ==================
    
    async def save_checkpoint(self, state: Dict) -> str:
        """Guarda checkpoint del estado"""
        data = {
            'state': state,
            'version': '2.0',
            'trigger_reason': state.get('trigger_reason', 'periodic'),
            'cycles_count': len(state.get('cycles', [])),
            'operations_count': len(state.get('operations', []))
        }
        
        result = self.client.table('checkpoints').insert(data).execute()
        return result.data[0]['id']
    
    async def get_latest_checkpoint(self) -> Optional[Dict]:
        """Obtiene último checkpoint"""
        result = self.client.table('checkpoints').select('*').order(
            'created_at', desc=True
        ).limit(1).execute()
        
        if not result.data:
            return None
        
        return result.data[0]['state']
    
    # ==================
    # METRICS
    # ==================
    
    async def get_daily_metrics(self, days: int = 30) -> List[Dict]:
        """Obtiene métricas de los últimos N días"""
        result = self.client.table('metrics_daily').select('*').order(
            'date', desc=True
        ).limit(days).execute()
        
        return result.data
    
    async def get_system_status(self) -> Dict:
        """Obtiene estado actual del sistema (vista)"""
        result = self.client.table('v_system_status').select('*').execute()
        return result.data[0] if result.data else {}
    
    # ==================
    # RESERVE FUND
    # ==================
    
    async def add_to_reserve(self, amount: float, source_op_id: str = None, reason: str = None):
        """Añade al fondo de reserva"""
        # Obtener balance actual
        current = self.client.table('reserve_fund').select('balance_after').order(
            'created_at', desc=True
        ).limit(1).execute()
        
        current_balance = current.data[0]['balance_after'] if current.data else 0
        new_balance = current_balance + amount
        
        self.client.table('reserve_fund').insert({
            'transaction_type': 'deposit',
            'amount': amount,
            'balance_after': new_balance,
            'source_operation_id': source_op_id,
            'reason': reason
        }).execute()
    
    async def get_reserve_balance(self) -> float:
        """Obtiene balance actual del fondo de reserva"""
        result = self.client.table('reserve_fund').select('balance_after').order(
            'created_at', desc=True
        ).limit(1).execute()
        
        return result.data[0]['balance_after'] if result.data else 0
    
    # ==================
    # REAL-TIME (Supabase feature)
    # ==================
    
    def subscribe_to_operations(self, callback):
        """Suscribe a cambios en operaciones (real-time)"""
        return self.client.table('operations').on('*', callback).subscribe()
    
    def subscribe_to_alerts(self, callback):
        """Suscribe a nuevas alertas"""
        return self.client.table('alerts').on('INSERT', callback).subscribe()
```

---

### Configuración Supabase

```python
# config/supabase_config.py
SUPABASE_CONFIG = {
    # Conexión
    'url': 'https://xxxxx.supabase.co',  # Tu URL de Supabase
    'anon_key': 'eyJ...',                 # Tu anon key
    'service_role_key': 'eyJ...',         # Para operaciones admin
    
    # Opciones
    'schema': 'public',
    'auto_refresh_token': True,
    'persist_session': True,
    
    # Real-time
    'realtime': {
        'enabled': True,
        'channels': ['operations', 'alerts', 'cycles']
    }
}
```

```bash
# .env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
```

---

### Real-time Dashboard con Supabase

```python
# api/websockets/realtime_supabase.py
from fastapi import WebSocket
from supabase import create_client

class RealtimeDashboard:
    """Dashboard real-time usando Supabase Realtime"""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self.subscribers = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.subscribers.append(websocket)
        
        # Suscribir a cambios
        self.client.table('operations').on('*', 
            lambda payload: self._broadcast(payload)
        ).subscribe()
        
        self.client.table('alerts').on('INSERT',
            lambda payload: self._broadcast_alert(payload)
        ).subscribe()
    
    async def _broadcast(self, payload):
        """Envía actualización a todos los clientes"""
        message = {
            'type': 'operation_update',
            'data': payload
        }
        for ws in self.subscribers:
            await ws.send_json(message)
    
    async def _broadcast_alert(self, payload):
        """Envía alerta a todos los clientes"""
        message = {
            'type': 'alert',
            'severity': payload['new']['severity'],
            'data': payload['new']
        }
        for ws in self.subscribers:
            await ws.send_json(message)
```

---

## Protección de Propiedad Intelectual

### Filosofía de Protección

> **"El código puede verse, pero la estrategia debe permanecer opaca"**

La arquitectura separa:
- **Core Strategy** (SECRETO): La lógica de decisión, parámetros, fórmulas
- **Engine** (PRIVADO): Ejecución, pero sin revelar el "por qué"
- **Infrastructure** (PÚBLICO): Conexiones, persistencia, API

---

### Arquitectura de Capas Protegidas

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CAPA PÚBLICA                                  │
│         (Puede verse, no revela estrategia)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  api/          → Endpoints REST, WebSockets                             │
│  infrastructure/                                                        │
│    ├── brokers/     → Adaptadores MT5, Darwinex                        │
│    ├── persistence/ → Supabase, repositorios                           │
│    └── resilience/  → Retry, Circuit Breaker, etc.                     │
├─────────────────────────────────────────────────────────────────────────┤
│                           CAPA PRIVADA                                  │
│         (Código visible, lógica abstracta)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  application/                                                           │
│    ├── use_cases/   → Orquestación (sin decisiones de estrategia)      │
│    └── services/    → Servicios de aplicación                          │
│  domain/                                                                │
│    ├── entities/    → Operación, Ciclo (estructuras de datos)          │
│    └── interfaces/  → Contratos abstractos                             │
├─────────────────────────────────────────────────────────────────────────┤
│                      💎 CAPA SECRETA (CORE) 💎                          │
│         (Protegida, ofuscada, compilada)                                │
├─────────────────────────────────────────────────────────────────────────┤
│  core/                                                                  │
│    ├── strategy/        → LA LÓGICA DE DECISIÓN                        │
│    │   ├── _engine.py   → Motor de decisiones (compilar con Cython)   │
│    │   ├── _params.py   → Parámetros secretos                          │
│    │   └── _formulas.py → Fórmulas de cálculo                          │
│    ├── signals/         → Generación de señales                        │
│    └── risk/            → Gestión de riesgo propietaria                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Estructura de Carpetas Protegida

```
fontanero/
├── src/
│   └── fontanero/
│       │
│       │   ┌──────────────────────────────────────┐
│       │   │  💎 CORE SECRETO (compilar/ofuscar) │
│       │   └──────────────────────────────────────┘
│       ├── core/                          # ⛔ NUNCA SUBIR A GIT PÚBLICO
│       │   ├── __init__.py
│       │   ├── strategy/
│       │   │   ├── __init__.py
│       │   │   ├── _decision_engine.py    # Compilar con Cython
│       │   │   ├── _entry_logic.py        # Lógica de entrada
│       │   │   ├── _exit_logic.py         # Lógica de salida
│       │   │   ├── _recovery_logic.py     # Lógica de recovery
│       │   │   └── _parameters.py         # Parámetros (cifrados)
│       │   ├── signals/
│       │   │   ├── __init__.py
│       │   │   └── _signal_generator.py
│       │   └── risk/
│       │       ├── __init__.py
│       │       └── _risk_calculator.py
│       │
│       │   ┌──────────────────────────────────────┐
│       │   │  DOMAIN (estructuras, sin lógica)    │
│       │   └──────────────────────────────────────┘
│       ├── domain/
│       │   ├── entities/
│       │   │   ├── operation.py           # Solo dataclasses
│       │   │   ├── cycle.py
│       │   │   └── portfolio.py
│       │   ├── value_objects/
│       │   │   ├── price.py
│       │   │   ├── pips.py
│       │   │   └── money.py
│       │   ├── events/
│       │   │   ├── cycle_events.py        # Eventos de dominio
│       │   │   └── operation_events.py
│       │   └── interfaces/
│       │       ├── strategy.py            # Interface abstracta
│       │       ├── broker.py
│       │       └── repository.py
│       │
│       │   ┌──────────────────────────────────────┐
│       │   │  APPLICATION (orquestación)          │
│       │   └──────────────────────────────────────┘
│       ├── application/
│       │   ├── use_cases/
│       │   │   ├── execute_strategy.py    # Llama al core, no sabe qué hace
│       │   │   ├── process_market_tick.py
│       │   │   └── handle_order_fill.py
│       │   └── services/
│       │       ├── cycle_orchestrator.py
│       │       └── position_manager.py
│       │
│       │   ┌──────────────────────────────────────┐
│       │   │  INFRASTRUCTURE (público)            │
│       │   └──────────────────────────────────────┘
│       ├── infrastructure/
│       │   ├── brokers/
│       │   ├── persistence/
│       │   ├── resilience/
│       │   └── logging/
│       │       └── safe_logger.py         # Logger que sanitiza
│       │
│       └── api/
│           ├── routers/
│           └── schemas/
│
├── core_compiled/                         # Core compilado (distribuir esto)
│   ├── strategy.cpython-311-x86_64-linux-gnu.so
│   └── ...
│
└── .gitignore                             # Ignorar /src/fontanero/core/
```

---

### Interface Abstracta del Core

```python
# domain/interfaces/strategy.py
"""
Interface pública del core.
Nadie fuera del core sabe CÓMO se toman las decisiones.
Solo saben QUÉ pueden preguntar.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    """Tipos de señal - nombres genéricos, no revelan lógica"""
    NO_ACTION = "no_action"
    OPEN_CYCLE = "open_cycle"
    ACTIVATE_HEDGE = "activate_hedge"
    OPEN_RECOVERY = "open_recovery"
    CLOSE_OPERATIONS = "close_operations"
    PAUSE = "pause"

@dataclass
class StrategySignal:
    """Señal emitida por el core - no revela el por qué"""
    signal_type: SignalType
    pair: str
    direction: Optional[str] = None  # 'buy' o 'sell'
    operations_to_close: List[str] = None
    metadata: dict = None  # Datos opacos para el core

class IStrategy(ABC):
    """
    Interface del motor de estrategia.
    El código externo solo ve estos métodos.
    """
    
    @abstractmethod
    def process_tick(
        self,
        pair: str,
        bid: float,
        ask: float,
        timestamp: datetime
    ) -> StrategySignal:
        """
        Procesa un tick y retorna señal.
        
        NO REVELAR:
        - Cómo se decide
        - Qué parámetros usa
        - Qué condiciones evalúa
        """
        pass
    
    @abstractmethod
    def process_order_fill(
        self,
        operation_id: str,
        fill_price: float,
        timestamp: datetime
    ) -> StrategySignal:
        """Procesa ejecución de orden."""
        pass
    
    @abstractmethod
    def process_tp_hit(
        self,
        operation_id: str,
        profit_pips: float,
        timestamp: datetime
    ) -> StrategySignal:
        """Procesa TP tocado."""
        pass
    
    @abstractmethod
    def get_current_state(self) -> dict:
        """
        Estado actual (sanitizado).
        Solo expone lo necesario para monitoreo.
        """
        pass
    
    @abstractmethod
    def load_state(self, state: dict) -> None:
        """Carga estado desde checkpoint."""
        pass


class IRiskManager(ABC):
    """Interface del gestor de riesgo."""
    
    @abstractmethod
    def can_open_position(
        self,
        pair: str,
        current_exposure: float
    ) -> tuple[bool, str]:
        """Retorna (puede_abrir, razón)"""
        pass
    
    @abstractmethod
    def calculate_lot_size(
        self,
        pair: str,
        account_balance: float
    ) -> float:
        """Calcula tamaño de posición."""
        pass
```

---

### Implementación del Core (SECRETO)

```python
# core/strategy/_decision_engine.py
"""
⛔ ARCHIVO SECRETO - NO DISTRIBUIR CÓDIGO FUENTE
Compilar con Cython antes de distribuir.
"""

from typing import Optional
from datetime import datetime
from domain.interfaces.strategy import IStrategy, StrategySignal, SignalType
from ._parameters import StrategyParameters
from ._entry_logic import EntryLogic
from ._exit_logic import ExitLogic
from ._recovery_logic import RecoveryLogic

class DecisionEngine(IStrategy):
    """
    Motor de decisiones - EL CORAZÓN DE LA ESTRATEGIA.
    
    Este código:
    1. NUNCA se sube a repositorios públicos
    2. Se compila con Cython para distribución
    3. Los parámetros se cargan cifrados
    """
    
    def __init__(self, params: StrategyParameters = None):
        self._params = params or StrategyParameters.load_encrypted()
        self._entry = EntryLogic(self._params)
        self._exit = ExitLogic(self._params)
        self._recovery = RecoveryLogic(self._params)
        
        # Estado interno (no exponer)
        self._active_cycles: dict = {}
        self._pending_signals: list = []
    
    def process_tick(
        self,
        pair: str,
        bid: float,
        ask: float,
        timestamp: datetime
    ) -> StrategySignal:
        """
        Lógica de decisión principal.
        
        ESTO ES LO QUE PROTEGEMOS:
        - Las condiciones exactas
        - Los parámetros
        - La secuencia de evaluación
        """
        # [LÓGICA SECRETA AQUÍ]
        
        # Ejemplo simplificado (la real es más compleja):
        if self._should_open_cycle(pair, bid, ask):
            return StrategySignal(
                signal_type=SignalType.OPEN_CYCLE,
                pair=pair,
                direction=self._determine_direction(bid, ask)
            )
        
        if self._should_activate_hedge(pair, bid):
            return StrategySignal(
                signal_type=SignalType.ACTIVATE_HEDGE,
                pair=pair
            )
        
        return StrategySignal(signal_type=SignalType.NO_ACTION, pair=pair)
    
    def _should_open_cycle(self, pair: str, bid: float, ask: float) -> bool:
        """
        ⛔ SECRETO: Condiciones de apertura
        """
        return self._entry.evaluate(pair, bid, ask, self._active_cycles)
    
    def _should_activate_hedge(self, pair: str, price: float) -> bool:
        """
        ⛔ SECRETO: Condiciones de cobertura
        """
        return self._exit.should_hedge(pair, price, self._active_cycles)
    
    def get_current_state(self) -> dict:
        """
        Estado SANITIZADO - solo lo necesario.
        NO incluye parámetros ni lógica interna.
        """
        return {
            'active_cycles_count': len(self._active_cycles),
            'pairs_active': list(self._active_cycles.keys()),
            # NO incluir: parámetros, umbrales, fórmulas
        }
```

---

### Compilación con Cython

```python
# setup_core.py
"""
Script para compilar el core con Cython.
El código compilado no es fácilmente reversible.
"""

from setuptools import setup
from Cython.Build import cythonize
import os

# Archivos a compilar (el core secreto)
CORE_FILES = [
    "src/fontanero/core/strategy/_decision_engine.py",
    "src/fontanero/core/strategy/_entry_logic.py",
    "src/fontanero/core/strategy/_exit_logic.py",
    "src/fontanero/core/strategy/_recovery_logic.py",
    "src/fontanero/core/strategy/_parameters.py",
    "src/fontanero/core/signals/_signal_generator.py",
    "src/fontanero/core/risk/_risk_calculator.py",
]

setup(
    name="fontanero-core",
    ext_modules=cythonize(
        CORE_FILES,
        compiler_directives={
            'language_level': "3",
            'boundscheck': False,
            'wraparound': False,
        },
        # Opciones de ofuscación
        annotate=False,  # No generar HTML de análisis
    ),
)

# Uso:
# python setup_core.py build_ext --inplace
# 
# Esto genera archivos .so (Linux) o .pyd (Windows)
# que no revelan el código fuente
```

```bash
# .gitignore - CRÍTICO
# Nunca subir el código fuente del core
/src/fontanero/core/strategy/_*.py
/src/fontanero/core/signals/_*.py
/src/fontanero/core/risk/_*.py

# Sí subir los archivos compilados (si quieres)
!/core_compiled/*.so
!/core_compiled/*.pyd
```

---

## Sistema de Logging Seguro

### Filosofía de Logging

> **"Los logs deben ayudar a debuggear sin revelar la estrategia"**

### Niveles de Información

```python
# infrastructure/logging/log_levels.py
from enum import Enum

class LogVisibility(Enum):
    """Niveles de visibilidad de información"""
    
    PUBLIC = "public"       # Puede verse en cualquier log
    INTERNAL = "internal"   # Solo logs internos, no exponer externamente
    SECRET = "secret"       # NUNCA loguear, solo en memoria para debug
```

### Glosario de Términos (Público vs Interno)

```python
# infrastructure/logging/terminology.py
"""
GLOSARIO DE NOMENCLATURA

Usa términos PÚBLICOS en logs, API, y código visible.
Los términos INTERNOS solo aparecen en el core.

Esto dificulta que alguien entienda la estrategia
leyendo logs o código público.
"""

TERMINOLOGY = {
    # ============================================
    # ENTIDADES
    # ============================================
    'public': {
        'cycle': 'position_group',         # Un ciclo = "grupo de posiciones"
        'main_cycle': 'primary_group',
        'recovery_cycle': 'secondary_group',
        'hedge': 'balance_position',       # Cobertura = "posición de balance"
        'recovery': 'correction',          # Recovery = "corrección"
    },
    'internal': {
        'position_group': 'cycle',
        'primary_group': 'main_cycle',
        'secondary_group': 'recovery_cycle',
        'balance_position': 'hedge',
        'correction': 'recovery',
    },
    
    # ============================================
    # ACCIONES
    # ============================================
    'public': {
        'open_cycle': 'init_group',
        'activate_hedge': 'balance',
        'open_recovery': 'correct',
        'close_cycle': 'finalize_group',
        'neutralize': 'offset',
    },
    'internal': {
        'init_group': 'open_cycle',
        'balance': 'activate_hedge',
        'correct': 'open_recovery',
        'finalize_group': 'close_cycle',
        'offset': 'neutralize',
    },
    
    # ============================================
    # MÉTRICAS
    # ============================================
    'public': {
        'pips_locked': 'units_pending',
        'recovery_ratio': 'correction_frequency',
        'tp_hit': 'target_reached',
        'drawdown': 'temporary_variance',
    },
    
    # ============================================
    # ESTADOS
    # ============================================
    'public': {
        'in_recovery': 'correcting',
        'hedged': 'balanced',
        'neutralized': 'offset',
    },
}

def to_public(internal_term: str) -> str:
    """Convierte término interno a público"""
    return TERMINOLOGY.get('public', {}).get(internal_term, internal_term)

def to_internal(public_term: str) -> str:
    """Convierte término público a interno"""
    return TERMINOLOGY.get('internal', {}).get(public_term, public_term)
```

---

### Safe Logger (Sanitización Automática)

```python
# infrastructure/logging/safe_logger.py
"""
Logger que sanitiza automáticamente información sensible.
"""

import logging
import json
import re
from typing import Any, Dict, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from contextvars import ContextVar
from .terminology import to_public

# Context variables para tracing
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')
operation_context: ContextVar[str] = ContextVar('operation_context', default='')

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class SanitizerConfig:
    """Configuración de sanitización"""
    
    # Campos a NUNCA loguear (se reemplazan por ***)
    secret_fields: Set[str] = field(default_factory=lambda: {
        'password', 'api_key', 'secret', 'token',
        'entry_threshold', 'exit_threshold',  # Parámetros de estrategia
        'recovery_formula', 'pip_calculation',
        'strategy_params', 'decision_factors',
    })
    
    # Campos a ofuscar parcialmente
    partial_mask_fields: Set[str] = field(default_factory=lambda: {
        'account_id', 'ticket', 'broker_response',
    })
    
    # Campos numéricos a redondear (ocultar precisión exacta)
    round_fields: Dict[str, int] = field(default_factory=lambda: {
        'entry_price': 3,      # Solo 3 decimales en logs
        'tp_price': 3,
        'balance': 0,          # Sin decimales
        'profit': 0,
    })
    
    # Términos a reemplazar (interno → público)
    use_public_terms: bool = True


class SafeLogger:
    """
    Logger que sanitiza información sensible automáticamente.
    
    Features:
    - Reemplaza campos secretos por ***
    - Usa terminología pública
    - Redondea números para ocultar precisión
    - Formato JSON estructurado
    - Correlation IDs para tracing
    """
    
    def __init__(
        self, 
        name: str, 
        config: SanitizerConfig = None,
        output_json: bool = True
    ):
        self.name = name
        self.config = config or SanitizerConfig()
        self.output_json = output_json
        self._logger = logging.getLogger(name)
    
    def _sanitize_value(self, key: str, value: Any) -> Any:
        """Sanitiza un valor según su tipo y configuración"""
        
        # Campos secretos → ***
        if key.lower() in self.config.secret_fields:
            return "***REDACTED***"
        
        # Campos parcialmente enmascarados
        if key.lower() in self.config.partial_mask_fields:
            if isinstance(value, str) and len(value) > 4:
                return value[:2] + "***" + value[-2:]
            return "***"
        
        # Campos numéricos a redondear
        if key.lower() in self.config.round_fields:
            if isinstance(value, (int, float)):
                decimals = self.config.round_fields[key.lower()]
                return round(value, decimals)
        
        return value
    
    def _sanitize_dict(self, data: Dict) -> Dict:
        """Sanitiza un diccionario recursivamente"""
        sanitized = {}
        
        for key, value in data.items():
            # Convertir key a terminología pública si está configurado
            public_key = to_public(key) if self.config.use_public_terms else key
            
            if isinstance(value, dict):
                sanitized[public_key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[public_key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[public_key] = self._sanitize_value(key, value)
        
        return sanitized
    
    def _build_log_entry(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Construye entrada de log estructurada y sanitizada"""
        
        # Sanitizar kwargs
        sanitized_data = self._sanitize_dict(kwargs) if kwargs else {}
        
        # Convertir mensaje a terminología pública
        public_message = message
        if self.config.use_public_terms:
            for internal, public in [
                ('cycle', 'position_group'),
                ('recovery', 'correction'),
                ('hedge', 'balance'),
                ('neutralize', 'offset'),
            ]:
                public_message = public_message.replace(internal, public)
        
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'logger': self.name,
            'message': public_message,
            'correlation_id': correlation_id.get() or None,
            'context': operation_context.get() or None,
        }
        
        if sanitized_data:
            entry['data'] = sanitized_data
        
        return entry
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """Método interno de logging"""
        entry = self._build_log_entry(level.value, message, **kwargs)
        
        if self.output_json:
            log_str = json.dumps(entry, default=str)
        else:
            log_str = f"[{entry['timestamp']}] {level.value} - {entry['message']}"
            if entry.get('data'):
                log_str += f" | {entry['data']}"
        
        getattr(self._logger, level.value.lower())(log_str)
    
    # Métodos públicos de logging
    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        if exception:
            # NO incluir stack trace completo (puede revelar lógica)
            kwargs['error_type'] = type(exception).__name__
            kwargs['error_message'] = self._sanitize_error_message(str(exception))
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, exception: Exception = None, **kwargs):
        if exception:
            kwargs['error_type'] = type(exception).__name__
            kwargs['error_message'] = self._sanitize_error_message(str(exception))
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _sanitize_error_message(self, message: str) -> str:
        """Sanitiza mensajes de error para no revelar lógica interna"""
        # Eliminar paths de archivos del core
        message = re.sub(r'/.*?/core/.*?\.py', '[core]', message)
        # Eliminar valores numéricos específicos
        message = re.sub(r'threshold=[\d.]+', 'threshold=***', message)
        return message
    
    # Métodos de logging específicos (ya sanitizados por diseño)
    def order_sent(self, operation_id: str, **kwargs):
        """Log de orden enviada - info pública solamente"""
        self.info(
            "Order sent",
            event="order_sent",
            operation_id=operation_id[:8] + "***",  # ID parcial
            **kwargs
        )
    
    def position_opened(self, group_id: str, direction: str, **kwargs):
        """Log de posición abierta - términos públicos"""
        self.info(
            "Position group initialized",
            event="group_init",
            group_id=group_id[:8] + "***",
            direction=direction,
            **kwargs
        )
    
    def correction_started(self, group_id: str, **kwargs):
        """Log de recovery - término público 'correction'"""
        self.info(
            "Correction sequence started",
            event="correction_start",
            group_id=group_id[:8] + "***",
            **kwargs
        )


# Instancia global preconfigurada
def get_safe_logger(name: str) -> SafeLogger:
    """Factory para obtener logger seguro"""
    return SafeLogger(name)
```

---

### Ejemplo de Logs Sanitizados

```python
# Código interno (con términos reales)
logger.info(
    "Opening main cycle with recovery enabled",
    cycle_id="EURUSD_001",
    entry_price=1.12345678,
    tp_pips=10,
    strategy_params={'threshold': 0.0015, 'multiplier': 2.5},
    account_balance=5432.10
)

# Log resultante (sanitizado)
{
    "timestamp": "2025-01-05T10:30:00.000Z",
    "level": "INFO",
    "logger": "trading_engine",
    "message": "Opening primary position_group with correction enabled",
    "correlation_id": "abc123",
    "data": {
        "position_group_id": "EU***01",
        "entry_price": 1.123,
        "tp_pips": 10,
        "strategy_params": "***REDACTED***",
        "account_balance": 5432
    }
}
```

---

### Configuración de Logging por Entorno

```python
# config/logging_config.py
from infrastructure.logging.safe_logger import SanitizerConfig

LOGGING_CONFIGS = {
    'development': SanitizerConfig(
        # En desarrollo, ser más permisivo para debug
        secret_fields={'password', 'api_key', 'token'},
        partial_mask_fields=set(),
        round_fields={},
        use_public_terms=False,  # Usar términos reales en dev
    ),
    
    'staging': SanitizerConfig(
        # En staging, sanitización parcial
        secret_fields={
            'password', 'api_key', 'token',
            'strategy_params', 'decision_factors',
        },
        partial_mask_fields={'account_id', 'ticket'},
        round_fields={'entry_price': 4, 'balance': 0},
        use_public_terms=True,
    ),
    
    'production': SanitizerConfig(
        # En producción, máxima sanitización
        secret_fields={
            'password', 'api_key', 'secret', 'token',
            'entry_threshold', 'exit_threshold',
            'recovery_formula', 'pip_calculation',
            'strategy_params', 'decision_factors',
            'internal_state', 'calculation_result',
        },
        partial_mask_fields={
            'account_id', 'ticket', 'broker_response',
            'operation_id', 'cycle_id',
        },
        round_fields={
            'entry_price': 3,
            'tp_price': 3,
            'balance': 0,
            'profit': 0,
        },
        use_public_terms=True,
    ),
}
```

---

## Type Hints y Código Debuggeable

### Convenciones de Type Hints

```python
# domain/types.py
"""
Tipos centralizados para type hints consistentes.
"""

from typing import (
    TypeVar, Generic, Optional, Union, 
    List, Dict, Tuple, Callable, Awaitable,
    NewType, Literal
)
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass

# ============================================
# Type Aliases para claridad
# ============================================

# IDs
OperationId = NewType('OperationId', str)      # "EURUSD_001_BUY"
CycleId = NewType('CycleId', str)              # "EURUSD_001"
RecoveryId = NewType('RecoveryId', str)        # "REC_EURUSD_001_001"
BrokerTicket = NewType('BrokerTicket', str)    # "12345678"

# Valores monetarios/trading
Pips = NewType('Pips', float)
Price = NewType('Price', Decimal)
LotSize = NewType('LotSize', float)
Money = NewType('Money', Decimal)

# Pair
CurrencyPair = NewType('CurrencyPair', str)    # "EURUSD"

# Direcciones
Direction = Literal['buy', 'sell']

# Timestamps
Timestamp = NewType('Timestamp', datetime)


# ============================================
# Generic Results
# ============================================

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Result(Generic[T]):
    """
    Result type para operaciones que pueden fallar.
    Evita excepciones para control de flujo.
    """
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def ok(cls, value: T) -> 'Result[T]':
        return cls(success=True, value=value)
    
    @classmethod
    def fail(cls, error: str, code: str = None) -> 'Result[T]':
        return cls(success=False, error=error, error_code=code)
    
    def unwrap(self) -> T:
        """Obtiene el valor o lanza excepción"""
        if not self.success:
            raise ValueError(self.error)
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        """Obtiene el valor o retorna default"""
        return self.value if self.success else default


@dataclass
class AsyncResult(Generic[T]):
    """Result para operaciones async"""
    success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    
    @classmethod
    async def from_awaitable(cls, awaitable: Awaitable[T]) -> 'AsyncResult[T]':
        try:
            value = await awaitable
            return cls(success=True, value=value)
        except Exception as e:
            return cls(success=False, error=str(e))
```

---

### Ejemplo de Código con Type Hints Completos

```python
# application/use_cases/execute_strategy.py
"""
Use case con type hints completos para fácil debug.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List
from dataclasses import dataclass
from datetime import datetime

from domain.types import (
    Result, CurrencyPair, Price, Pips, 
    OperationId, CycleId, Direction, Timestamp
)
from domain.interfaces.strategy import IStrategy, StrategySignal, SignalType
from domain.entities.operation import Operation, OperationType, OperationStatus
from domain.entities.cycle import Cycle, CycleStatus

if TYPE_CHECKING:
    from domain.interfaces.broker import IBroker
    from domain.interfaces.repository import IRepository
    from infrastructure.logging.safe_logger import SafeLogger


@dataclass
class TickData:
    """Datos de un tick de mercado"""
    pair: CurrencyPair
    bid: Price
    ask: Price
    timestamp: Timestamp
    spread_pips: Pips


@dataclass 
class ExecutionResult:
    """Resultado de ejecutar la estrategia"""
    signal: StrategySignal
    operations_created: List[OperationId]
    operations_closed: List[OperationId]
    errors: List[str]


class ExecuteStrategyUseCase:
    """
    Ejecuta la estrategia para un tick de mercado.
    
    Responsabilidades:
    - Recibir tick
    - Pasar al core (strategy)
    - Ejecutar señales recibidas
    - NO saber la lógica de decisión
    """
    
    def __init__(
        self,
        strategy: IStrategy,
        broker: IBroker,
        repository: IRepository,
        logger: SafeLogger,
    ) -> None:
        self._strategy = strategy
        self._broker = broker
        self._repo = repository
        self._logger = logger
    
    async def execute(self, tick: TickData) -> Result[ExecutionResult]:
        """
        Ejecuta la estrategia para un tick.
        
        Args:
            tick: Datos del tick de mercado
            
        Returns:
            Result con ExecutionResult o error
        """
        try:
            # 1. Obtener señal del core (caja negra)
            signal = self._strategy.process_tick(
                pair=tick.pair,
                bid=float(tick.bid),
                ask=float(tick.ask),
                timestamp=tick.timestamp
            )
            
            self._logger.debug(
                "Signal received from core",
                signal_type=signal.signal_type.value,
                pair=tick.pair
            )
            
            # 2. Ejecutar señal
            result = await self._execute_signal(signal, tick)
            
            return Result.ok(result)
            
        except Exception as e:
            self._logger.error("Strategy execution failed", exception=e)
            return Result.fail(str(e), code="STRATEGY_EXECUTION_ERROR")
    
    async def _execute_signal(
        self, 
        signal: StrategySignal,
        tick: TickData
    ) -> ExecutionResult:
        """Ejecuta una señal del core"""
        
        operations_created: List[OperationId] = []
        operations_closed: List[OperationId] = []
        errors: List[str] = []
        
        if signal.signal_type == SignalType.OPEN_CYCLE:
            result = await self._open_cycle(signal, tick)
            if result.success:
                operations_created.extend(result.value)
            else:
                errors.append(result.error)
        
        elif signal.signal_type == SignalType.ACTIVATE_HEDGE:
            result = await self._activate_hedge(signal)
            if result.success:
                operations_created.append(result.value)
            else:
                errors.append(result.error)
        
        elif signal.signal_type == SignalType.CLOSE_OPERATIONS:
            result = await self._close_operations(signal.operations_to_close)
            if result.success:
                operations_closed.extend(result.value)
            else:
                errors.append(result.error)
        
        return ExecutionResult(
            signal=signal,
            operations_created=operations_created,
            operations_closed=operations_closed,
            errors=errors
        )
    
    async def _open_cycle(
        self, 
        signal: StrategySignal,
        tick: TickData
    ) -> Result[List[OperationId]]:
        """Abre un nuevo ciclo"""
        # Implementación...
        pass
    
    async def _activate_hedge(
        self, 
        signal: StrategySignal
    ) -> Result[OperationId]:
        """Activa cobertura"""
        # Implementación...
        pass
    
    async def _close_operations(
        self, 
        operation_ids: List[OperationId]
    ) -> Result[List[OperationId]]:
        """Cierra operaciones"""
        # Implementación...
        pass
```

---

### Debug Helpers

```python
# infrastructure/debug/helpers.py
"""
Helpers para debugging que NO exponen lógica sensible.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import functools
import time
import asyncio

def debug_timer(func):
    """
    Decorador que mide tiempo de ejecución.
    Útil para identificar cuellos de botella.
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        
        # Log si es lento (>100ms)
        if elapsed > 100:
            print(f"⏱️ SLOW: {func.__name__} took {elapsed:.2f}ms")
        
        return result
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        
        if elapsed > 100:
            print(f"⏱️ SLOW: {func.__name__} took {elapsed:.2f}ms")
        
        return result
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def debug_state(label: str):
    """
    Decorador para debug de estado antes/después.
    Solo activo en modo DEBUG.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not getattr(self, '_debug_mode', False):
                return await func(self, *args, **kwargs)
            
            # Estado antes (sanitizado)
            state_before = self._get_debug_state() if hasattr(self, '_get_debug_state') else {}
            
            result = await func(self, *args, **kwargs)
            
            # Estado después (sanitizado)
            state_after = self._get_debug_state() if hasattr(self, '_get_debug_state') else {}
            
            # Mostrar cambios
            changes = _diff_states(state_before, state_after)
            if changes:
                print(f"🔍 {label}: {changes}")
            
            return result
        return wrapper
    return decorator


def _diff_states(before: Dict, after: Dict) -> Dict:
    """Calcula diferencias entre estados (sin datos sensibles)"""
    changes = {}
    
    for key in set(before.keys()) | set(after.keys()):
        val_before = before.get(key)
        val_after = after.get(key)
        
        if val_before != val_after:
            # Solo mostrar que cambió, no los valores exactos
            changes[key] = f"{type(val_before).__name__} → {type(val_after).__name__}"
    
    return changes


class DebugContext:
    """
    Context manager para debugging seguro.
    Captura estado sin exponer información sensible.
    """
    
    def __init__(self, name: str, capture_state: bool = True):
        self.name = name
        self.capture_state = capture_state
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error: Optional[Exception] = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.error = exc_val
        
        elapsed = (self.end_time - self.start_time) * 1000
        
        if self.error:
            print(f"❌ {self.name}: FAILED in {elapsed:.2f}ms - {type(self.error).__name__}")
        elif elapsed > 100:
            print(f"⚠️ {self.name}: SLOW {elapsed:.2f}ms")
        
        return False  # No suprimir excepciones


# Uso:
# with DebugContext("process_tick"):
#     result = strategy.process_tick(...)
```

---

### Resumen de Protección

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAPAS DE PROTECCIÓN                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CÓDIGO                                                      │
│     ├── Core en carpeta separada (/core/)                      │
│     ├── .gitignore excluye código fuente del core              │
│     ├── Compilación con Cython (.so/.pyd)                      │
│     └── Interface abstracta oculta implementación               │
│                                                                 │
│  2. LOGGING                                                     │
│     ├── Campos secretos → ***REDACTED***                       │
│     ├── Terminología pública (cycle → position_group)          │
│     ├── IDs parcialmente enmascarados                          │
│     └── Números redondeados                                     │
│                                                                 │
│  3. API                                                         │
│     ├── Solo expone acciones, no lógica                        │
│     ├── Respuestas sanitizadas                                 │
│     └── Sin endpoints de debug en producción                   │
│                                                                 │
│  4. BASE DE DATOS                                               │
│     ├── Parámetros cifrados                                    │
│     ├── Sin columnas de lógica interna                         │
│     └── Logs sanitizados                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Arquitectura Técnica

### Principios de Diseño

**Clean Architecture**
- Separación estricta de capas
- Dependencias hacia adentro (dominio no depende de infraestructura)
- Testeable, mantenible, extensible

**Modular y Expandible**
- Cada componente es independiente
- Fácil añadir nuevos pares, estrategias o brokers
- Plug & play para nuevas funcionalidades

---

### Stack Tecnológico

| Capa          | Tecnología          | Función                                     |
| ------------- | ------------------- | ------------------------------------------- |
| API           | FastAPI             | Endpoints REST, WebSockets para tiempo real |
| Trading       | MT5 + Darwinex API  | Ejecución de órdenes, gestión de posiciones |
| Datos         | QuantDataManager    | Históricos 15 años, sin nulls               |
| Base de datos | PostgreSQL / SQLite | Persistencia de operaciones y estado        |
| Cache         | Redis (opcional)    | Estado en tiempo real, pub/sub              |

---

### Estructura de Carpetas (Clean Architecture)

```
fontanero/
│
├── domain/                     # Capa de dominio (núcleo)
│   ├── entities/
│   │   ├── operation.py        # Operación (principal, cobertura, recovery)
│   │   ├── cycle.py            # Ciclo (principal, recovery)
│   │   └── portfolio.py        # Portfolio de pares
│   ├── value_objects/
│   │   ├── price.py
│   │   ├── pips.py
│   │   └── lot_size.py
│   ├── services/
│   │   ├── cycle_manager.py    # Lógica de ciclos
│   │   ├── hedge_calculator.py # Cálculo de coberturas
│   │   └── recovery_manager.py # Gestión de recovery
│   └── interfaces/             # Puertos (abstracciones)
│       ├── broker.py           # Interface broker
│       ├── data_provider.py    # Interface datos
│       └── repository.py       # Interface persistencia
│
├── application/                # Capa de aplicación (casos de uso)
│   ├── use_cases/
│   │   ├── open_main_cycle.py
│   │   ├── activate_hedge.py
│   │   ├── open_recovery.py
│   │   ├── close_cycle.py
│   │   └── calculate_exposure.py
│   ├── dto/
│   │   ├── cycle_dto.py
│   │   └── operation_dto.py
│   └── services/
│       ├── spread_controller.py    # Control de spreads
│       ├── correlation_checker.py  # Verificación correlación
│       └── reserve_fund.py         # Gestión fondo 20%
│
├── infrastructure/             # Capa de infraestructura
│   ├── brokers/
│   │   ├── mt5_adapter.py      # Adaptador MetaTrader 5
│   │   └── darwinex_adapter.py # Adaptador API Darwinex
│   ├── data/
│   │   ├── quantdata_loader.py # Carga datos históricos
│   │   └── realtime_feed.py    # Feed tiempo real
│   ├── persistence/
│   │   ├── postgres_repo.py
│   │   └── sqlite_repo.py
│   └── external/
│       └── news_calendar.py    # Calendario eventos
│
├── api/                        # Capa de presentación (FastAPI)
│   ├── main.py                 # Punto de entrada
│   ├── routers/
│   │   ├── cycles.py           # Endpoints ciclos
│   │   ├── operations.py       # Endpoints operaciones
│   │   ├── portfolio.py        # Endpoints portfolio
│   │   ├── metrics.py          # Endpoints métricas
│   │   └── backtest.py         # Endpoints backtesting
│   ├── websockets/
│   │   └── realtime.py         # WS para dashboard
│   └── middleware/
│       └── error_handler.py
│
├── backtesting/                # Motor de backtesting
│   ├── engine.py               # Motor principal
│   ├── data_loader.py          # Carga datos QuantData
│   └── reporters/
│       ├── html_report.py
│       └── metrics_calculator.py
│
├── config/
│   ├── settings.py             # Configuración general
│   ├── pairs_config.py         # Configuración por par
│   └── risk_params.py          # Parámetros de riesgo
│
└── tests/
    ├── unit/
    ├── integration/
    └── backtest/
```

---

### Sistema de IDs Jerárquicos

El sistema de IDs permite trazabilidad completa de cualquier operación hasta su origen.

```python
# domain/services/id_generator.py
class GeneradorIDs:
    """Genera IDs jerárquicos únicos y secuenciales"""
    
    def __init__(self):
        self.contadores = {}  # {simbolo: contador}
    
    def generar_id_ciclo_principal(self, simbolo: str) -> str:
        """EURUSD_001, EURUSD_002, etc."""
        if simbolo not in self.contadores:
            self.contadores[simbolo] = {'ciclo': 0, 'recovery': {}}
        self.contadores[simbolo]['ciclo'] += 1
        return f"{simbolo}_{self.contadores[simbolo]['ciclo']:03d}"
    
    def generar_id_operacion_principal(self, ciclo_id: str, tipo: str) -> str:
        """EURUSD_001_BUY, EURUSD_001_SELL"""
        return f"{ciclo_id}_{tipo}"
    
    def generar_id_recovery(self, ciclo_id: str) -> str:
        """REC_EURUSD_001_001, REC_EURUSD_001_002"""
        simbolo = ciclo_id.split('_')[0]
        if ciclo_id not in self.contadores[simbolo]['recovery']:
            self.contadores[simbolo]['recovery'][ciclo_id] = 0
        self.contadores[simbolo]['recovery'][ciclo_id] += 1
        num = self.contadores[simbolo]['recovery'][ciclo_id]
        return f"REC_{ciclo_id}_{num:03d}"
    
    def generar_id_cobertura(self, ciclo_id: str, tipo: str) -> str:
        """COB_EURUSD_001_BUY, COB_EURUSD_001_SELL"""
        return f"COB_{ciclo_id}_{tipo}"
```

**Ventajas del sistema:**
- Cualquier operación puede rastrearse hasta su origen
- Los IDs cuentan la historia completa
- Facilita debugging y auditoría
- Permite agrupar operaciones relacionadas

---

### Entidades del Dominio

```python
# domain/entities/operation.py
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

class OperationType(Enum):
    MAIN_BUY = "main_buy"
    MAIN_SELL = "main_sell"
    HEDGE_BUY = "hedge_buy"
    HEDGE_SELL = "hedge_sell"
    RECOVERY_BUY = "recovery_buy"
    RECOVERY_SELL = "recovery_sell"

class OperationStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    TP_HIT = "tp_hit"
    NEUTRALIZED = "neutralized"
    CLOSED = "closed"
    CANCELLED = "cancelled"

@dataclass
class Operation:
    id: str                          # "EURUSD_001_BUY"
    cycle_id: str                    # "EURUSD_001"
    pair: str
    op_type: OperationType
    status: OperationStatus
    entry_price: float
    tp_price: float
    lot_size: float
    pips_target: int
    created_at: datetime
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    linked_operation_id: Optional[str] = None
    recovery_id: Optional[str] = None        # "REC_EURUSD_001_001"
    
    # Contabilidad
    commission_open: float = 7.0             # Comisión apertura (EUR)
    commission_close: float = 7.0            # Comisión cierre (EUR)
    swap_daily: float = 2.0                  # Swap diario (EUR)
    profit_pips: float = 0.0
    
    def days_open(self) -> int:
        """Días que lleva abierta la operación"""
        if not self.activated_at:
            return 0
        end = self.closed_at or datetime.now()
        return (end - self.activated_at).days
    
    def total_cost(self) -> float:
        """Costo total: comisiones + swaps"""
        swaps = self.swap_daily * self.days_open()
        return self.commission_open + self.commission_close + swaps
    
    def net_profit_eur(self, pip_value: float = 1.0) -> float:
        """Beneficio neto en EUR"""
        return (self.profit_pips * pip_value) - self.total_cost()
```

```python
# domain/entities/cycle.py
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict

class CycleType(Enum):
    MAIN = "main"
    RECOVERY = "recovery"

class CycleStatus(Enum):
    ACTIVE = "active"
    HEDGED = "hedged"
    IN_RECOVERY = "in_recovery"
    CLOSED = "closed"

@dataclass
class Cycle:
    id: str                                  # "EURUSD_001"
    cycle_type: CycleType
    pair: str
    status: CycleStatus
    parent_cycle_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    recovery_level: int = 0                  # 0=main, 1=first, 2=second...
    min_profit_target: int = 20              # Pips mínimos para cerrar ciclo
    
    # Operaciones del ciclo
    main_operations: List[str] = field(default_factory=list)
    hedge_operations: List[str] = field(default_factory=list)
    recovery_operations: Dict[str, List[str]] = field(default_factory=dict)
    
    # Contabilidad
    first_recovery_id: Optional[str] = None  # Para lógica especial 20 pips
```

---

### Contabilidad del Ciclo con Sistema FIFO

```python
# domain/services/cycle_accounting.py
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

@dataclass
class ContabilidadCiclo:
    """Mantiene contabilidad completa de un ciclo y sus recovery"""
    
    ciclo_principal_id: str
    operaciones_principales: List[str] = field(default_factory=list)
    operaciones_cobertura: List[str] = field(default_factory=list)
    operaciones_recovery: List[str] = field(default_factory=list)
    primer_recovery_id: Optional[str] = None
    
    def calcular_balance_total(self, repo) -> float:
        """Suma beneficio_neto de todas las operaciones del ciclo"""
        balance = 0.0
        all_ops = (
            self.operaciones_principales + 
            self.operaciones_cobertura + 
            self.operaciones_recovery
        )
        for op_id in all_ops:
            op = repo.get_operation(op_id)
            balance += op.net_profit_eur()
        return balance
    
    def puede_cerrar_con_tp(
        self, 
        pips_disponibles: int, 
        repo
    ) -> Tuple[List[str], int]:
        """
        Determina qué recovery cerrar con X pips ganados (Sistema FIFO)
        
        Lógica especial:
        - Primer recovery: cuesta 20 pips (incluye principales)
        - Recovery siguientes: cuestan 40 pips cada uno
        
        Returns:
            (lista_ids_a_cerrar, pips_restantes)
        """
        a_cerrar = []
        pips_restantes = pips_disponibles
        
        # Ordenar recovery por fecha de creación (FIFO)
        recovery_ordenados = self._ordenar_recovery_por_fecha(repo)
        
        for recovery_id in recovery_ordenados:
            # Determinar costo de este recovery
            if recovery_id == self.primer_recovery_id:
                costo = 20  # Primer recovery incluye principales
            else:
                costo = 40  # Recovery adicionales
            
            if pips_restantes >= costo:
                a_cerrar.append(recovery_id)
                pips_restantes -= costo
            else:
                break
        
        return a_cerrar, pips_restantes
    
    def _ordenar_recovery_por_fecha(self, repo) -> List[str]:
        """Ordena recovery del más antiguo al más nuevo"""
        recovery_con_fecha = []
        for rec_id in self.operaciones_recovery:
            op = repo.get_operation(rec_id)
            recovery_con_fecha.append((rec_id, op.created_at))
        
        recovery_con_fecha.sort(key=lambda x: x[1])
        return [r[0] for r in recovery_con_fecha]
    
    def identificar_recovery_sin_cubrir(self, repo) -> List[str]:
        """
        Encuentra recovery donde ambas operaciones están activas
        (neutralizados pero sin cobertura de recovery exitoso)
        """
        sin_cubrir = []
        # Agrupar recovery por pares
        recovery_pairs = {}
        
        for rec_id in self.operaciones_recovery:
            base_id = rec_id.rsplit('_', 1)[0]  # REC_EURUSD_001_001 -> REC_EURUSD_001
            if base_id not in recovery_pairs:
                recovery_pairs[base_id] = []
            recovery_pairs[base_id].append(rec_id)
        
        for base_id, ops in recovery_pairs.items():
            if len(ops) == 2:
                op1 = repo.get_operation(ops[0])
                op2 = repo.get_operation(ops[1])
                if (op1.status == OperationStatus.ACTIVE and 
                    op2.status == OperationStatus.ACTIVE):
                    sin_cubrir.append(base_id)
        
        return sin_cubrir
```

**Lógica FIFO explicada:**
1. El primer recovery que se cierra cuesta **20 pips** (incluye las operaciones principales)
2. Los recovery siguientes cuestan **40 pips** cada uno
3. Siempre se cierran los **más antiguos primero**
4. Con 80 pips de un recovery exitoso puedes cerrar: primer recovery (20) + un recovery adicional (40) = 60 pips usados, 20 pips de beneficio

---

### Interfaces (Puertos)

```python
# domain/interfaces/broker.py
from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.operation import Operation

class BrokerInterface(ABC):
    
    @abstractmethod
    async def place_order(self, operation: Operation) -> str:
        """Coloca orden, retorna ticket/id del broker"""
        pass
    
    @abstractmethod
    async def cancel_order(self, ticket: str) -> bool:
        """Cancela orden pendiente"""
        pass
    
    @abstractmethod
    async def close_position(self, ticket: str) -> bool:
        """Cierra posición activa"""
        pass
    
    @abstractmethod
    async def get_current_price(self, pair: str) -> tuple[float, float]:
        """Retorna (bid, ask)"""
        pass
    
    @abstractmethod
    async def get_spread(self, pair: str) -> float:
        """Retorna spread actual en pips"""
        pass
    
    @abstractmethod
    async def get_open_positions(self) -> list:
        """Lista posiciones abiertas"""
        pass
```

---

### Adaptadores de Broker

```python
# infrastructure/brokers/mt5_adapter.py
import MetaTrader5 as mt5
from domain.interfaces.broker import BrokerInterface

class MT5Adapter(BrokerInterface):
    
    def __init__(self, login: int, password: str, server: str):
        self.login = login
        self.password = password
        self.server = server
        
    async def connect(self):
        if not mt5.initialize():
            raise ConnectionError("MT5 init failed")
        if not mt5.login(self.login, self.password, self.server):
            raise ConnectionError("MT5 login failed")
    
    async def place_order(self, operation: Operation) -> str:
        order_type = self._map_order_type(operation.op_type)
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": operation.pair,
            "volume": operation.lot_size,
            "type": order_type,
            "price": operation.entry_price,
            "tp": operation.tp_price,
            "magic": int(operation.cycle_id[:8], 16),  # ID único
            "comment": f"{operation.op_type.value}:{operation.cycle_id}"
        }
        result = mt5.order_send(request)
        return str(result.order)
    
    async def get_spread(self, pair: str) -> float:
        tick = mt5.symbol_info_tick(pair)
        point = mt5.symbol_info(pair).point
        return (tick.ask - tick.bid) / point / 10  # En pips
```

```python
# infrastructure/brokers/darwinex_adapter.py
import httpx
from domain.interfaces.broker import BrokerInterface

class DarwinexAdapter(BrokerInterface):
    
    def __init__(self, api_key: str, account_id: str):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = "https://api.darwinex.com/v1"
        
    async def place_order(self, operation: Operation) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/accounts/{self.account_id}/orders",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "instrument": operation.pair,
                    "side": "buy" if "BUY" in operation.op_type.name else "sell",
                    "type": "stop",
                    "price": operation.entry_price,
                    "takeProfit": operation.tp_price,
                    "quantity": operation.lot_size
                }
            )
            return response.json()["orderId"]
```

---

### Casos de Uso

```python
# application/use_cases/open_main_cycle.py
from domain.entities.cycle import Cycle, CycleType, CycleStatus
from domain.entities.operation import Operation, OperationType, OperationStatus
from domain.interfaces.broker import BrokerInterface
from application.services.spread_controller import SpreadController

class OpenMainCycleUseCase:
    
    def __init__(
        self,
        broker: BrokerInterface,
        spread_controller: SpreadController,
        repository
    ):
        self.broker = broker
        self.spread_controller = spread_controller
        self.repo = repository
    
    async def execute(self, pair: str, lot_size: float = 0.01) -> Cycle:
        # Verificar spread
        if not await self.spread_controller.is_acceptable(pair):
            raise SpreadTooHighError(f"Spread too high for {pair}")
        
        # Obtener precio actual
        bid, ask = await self.broker.get_current_price(pair)
        mid_price = (bid + ask) / 2
        
        # Crear ciclo
        cycle = Cycle(
            id=generate_uuid(),
            cycle_type=CycleType.MAIN,
            pair=pair,
            status=CycleStatus.ACTIVE
        )
        
        # Crear operaciones principales
        buy_op = Operation(
            id=generate_uuid(),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_BUY,
            status=OperationStatus.PENDING,
            entry_price=mid_price + 0.0005,  # +5 pips
            tp_price=mid_price + 0.0015,     # +15 pips (entry + 10)
            lot_size=lot_size,
            pips_target=10
        )
        
        sell_op = Operation(
            id=generate_uuid(),
            cycle_id=cycle.id,
            pair=pair,
            op_type=OperationType.MAIN_SELL,
            status=OperationStatus.PENDING,
            entry_price=mid_price - 0.0005,  # -5 pips
            tp_price=mid_price - 0.0015,     # -15 pips
            lot_size=lot_size,
            pips_target=10,
            linked_operation_id=buy_op.id
        )
        buy_op.linked_operation_id = sell_op.id
        
        # Enviar al broker
        buy_ticket = await self.broker.place_order(buy_op)
        sell_ticket = await self.broker.place_order(sell_op)
        
        # Persistir
        await self.repo.save_cycle(cycle)
        await self.repo.save_operation(buy_op)
        await self.repo.save_operation(sell_op)
        
        return cycle
```

---

### API FastAPI

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import cycles, operations, portfolio, metrics, backtest

app = FastAPI(
    title="El Fontanero de Wall Street",
    description="Sistema de trading con coberturas",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(cycles.router, prefix="/cycles", tags=["Cycles"])
app.include_router(operations.router, prefix="/operations", tags=["Operations"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
app.include_router(backtest.router, prefix="/backtest", tags=["Backtest"])

@app.get("/health")
async def health():
    return {"status": "ok", "system": "El Fontanero de Wall Street"}
```

```python
# api/routers/cycles.py
from fastapi import APIRouter, Depends, HTTPException
from application.use_cases.open_main_cycle import OpenMainCycleUseCase

router = APIRouter()

@router.post("/main")
async def open_main_cycle(pair: str, lot_size: float = 0.01):
    """Abre un nuevo ciclo principal"""
    use_case = get_open_main_cycle_use_case()  # Dependency injection
    try:
        cycle = await use_case.execute(pair, lot_size)
        return {"cycle_id": cycle.id, "status": "created"}
    except SpreadTooHighError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{cycle_id}")
async def get_cycle(cycle_id: str):
    """Obtiene estado de un ciclo"""
    pass

@router.get("/")
async def list_cycles(status: str = None, pair: str = None):
    """Lista ciclos con filtros"""
    pass

@router.post("/{cycle_id}/pause")
async def pause_cycle(cycle_id: str):
    """Pausa un ciclo (no abre nuevas ops)"""
    pass
```

```python
# api/routers/metrics.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/exposure")
async def get_exposure():
    """Exposición actual por par y total"""
    return {
        "total_exposure_eur": 450,
        "by_pair": {
            "EURUSD": {"operations": 12, "pips_locked": 120, "eur": 120},
            "GBPUSD": {"operations": 8, "pips_locked": 80, "eur": 80}
        },
        "reserve_fund": 156,
        "available_margin": 1200
    }

@router.get("/daily")
async def get_daily_metrics():
    """Métricas del día"""
    return {
        "main_cycles_closed": 12,
        "main_pips": 120,
        "recovery_closed": 2,
        "recovery_pips": 160,
        "to_reserve": 32,  # 20% de recovery
        "net_profit_eur": 24.8
    }

@router.get("/correlation")
async def get_portfolio_correlation():
    """Matriz de correlación del portfolio"""
    pass
```

---

### Motor de Backtesting

```python
# backtesting/engine.py
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class BacktestEngine:
    
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.data: pd.DataFrame = None
        self.ticks: List[Dict] = []
        self.cycles = []
        self.metrics = {
            'ticks_processed': 0,
            'cycles_completed': 0,
            'recovery_created': 0,
            'gaps_detected': 0,
            'balance_history': [],
            'operations_log': []
        }
        
    def load_data(self, pair: str, start_date: str, end_date: str):
        """Carga datos de QuantDataManager"""
        file_path = self.data_path / f"{pair}_tick.parquet"
        self.data = pd.read_parquet(file_path)
        self.data = self.data[
            (self.data.index >= start_date) & 
            (self.data.index <= end_date)
        ]
        print(f"Loaded {len(self.data)} records for {pair}")
        
    def run(self, config: dict) -> dict:
        """Ejecuta backtest completo"""
        for i, (timestamp, row) in enumerate(self.data.iterrows()):
            price = row['mid'] if 'mid' in row else (row['bid'] + row['ask']) / 2
            
            # Detectar gaps
            if i > 0:
                prev_price = self.metrics['balance_history'][-1]['price'] if self.metrics['balance_history'] else price
                gap_pips = abs(price - prev_price) * 10000
                if gap_pips > 50:
                    self._handle_gap(price, prev_price, timestamp)
            
            # Procesar tick
            self._process_tick(price, timestamp)
            
            # Registrar estado
            self.metrics['balance_history'].append({
                'timestamp': timestamp,
                'price': price,
                'balance': self._calculate_current_balance()
            })
        
        return self._calculate_final_metrics()
    
    def _handle_gap(self, current_price: float, prev_price: float, timestamp):
        """Maneja gaps >50 pips con correcciones automáticas"""
        self.metrics['gaps_detected'] += 1
        gap_pips = (current_price - prev_price) * 10000
        
        self.metrics['operations_log'].append({
            'timestamp': timestamp,
            'event': 'GAP_DETECTED',
            'details': f"Gap de {gap_pips:.1f} pips detectado",
            'action': 'Verificando TPs saltados y órdenes pendientes'
        })
        
        # Verificar TPs que pudieron saltarse
        for cycle in self.cycles:
            if cycle.status != CycleStatus.CLOSED:
                self._check_skipped_tps(cycle, prev_price, current_price)
        
        # Cancelar y recolocar órdenes orphan
        self._rebalance_pending_orders(current_price)
    
    def _check_skipped_tps(self, cycle, prev_price: float, current_price: float):
        """Verifica si algún TP fue saltado por el gap"""
        min_price = min(prev_price, current_price)
        max_price = max(prev_price, current_price)
        
        # Si el TP estaba entre prev y current, se considera tocado
        for op_id in cycle.main_operations + list(cycle.recovery_operations.keys()):
            op = self.repo.get_operation(op_id)
            if op.status == OperationStatus.ACTIVE:
                if min_price <= op.tp_price <= max_price:
                    op.status = OperationStatus.TP_HIT
                    op.profit_pips = op.pips_target
                    self.metrics['operations_log'].append({
                        'timestamp': datetime.now(),
                        'event': 'TP_HIT_BY_GAP',
                        'operation': op_id
                    })
```

---

### Conversor de OHLC a Ticks

Para backtesting con datos OHLC (velas), convertimos a ticks realistas:

```python
# backtesting/tick_converter.py
import pandas as pd
import numpy as np
from typing import List, Dict

class ConvertidorTicks:
    """Convierte velas OHLC en secuencia de ticks realistas"""
    
    @staticmethod
    def crear_ticks_detallados(df_ohlc: pd.DataFrame, ticks_por_vela: int = 10) -> List[Dict]:
        """
        Convierte cada vela OHLC en ~10 ticks con movimiento lógico
        
        Algoritmo:
        1. Determinar si va primero a high o low (basado en close vs open)
        2. Crear secuencia: Open → (High/Low) → (Low/High) → Close
        3. Añadir ruido sintético entre puntos
        """
        ticks = []
        
        for idx, row in df_ohlc.iterrows():
            timestamp_base = idx
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            
            # Determinar dirección principal de la vela
            bullish = c > o
            
            # Crear secuencia de precios
            if bullish:
                # Vela alcista: O → L → H → C
                sequence = ConvertidorTicks._create_sequence(o, l, h, c, ticks_por_vela)
            else:
                # Vela bajista: O → H → L → C
                sequence = ConvertidorTicks._create_sequence(o, h, l, c, ticks_por_vela)
            
            # Distribuir timestamps uniformemente
            time_delta = pd.Timedelta(minutes=1) / ticks_por_vela  # Asume M1
            
            for i, price in enumerate(sequence):
                tick_time = timestamp_base + (time_delta * i)
                spread = 0.00015  # Spread sintético ~1.5 pips
                ticks.append({
                    'timestamp': tick_time,
                    'bid': price,
                    'ask': price + spread,
                    'mid': price + spread/2
                })
        
        return ticks
    
    @staticmethod
    def _create_sequence(start: float, point1: float, point2: float, end: float, n: int) -> List[float]:
        """Crea secuencia de n precios entre 4 puntos con ruido"""
        # Dividir n ticks entre los 3 segmentos
        n1 = n // 3
        n2 = n // 3
        n3 = n - n1 - n2
        
        # Crear interpolación con ruido
        seg1 = np.linspace(start, point1, n1)
        seg2 = np.linspace(point1, point2, n2)
        seg3 = np.linspace(point2, end, n3)
        
        sequence = np.concatenate([seg1, seg2[1:], seg3[1:]])
        
        # Añadir ruido pequeño
        noise = np.random.normal(0, 0.00002, len(sequence))
        sequence = sequence + noise
        
        return sequence.tolist()
```

**Uso en backtest:**
```python
# Si tienes datos OHLC en lugar de ticks
df_ohlc = pd.read_csv('EURUSD_M1.csv')
ticks = ConvertidorTicks.crear_ticks_detallados(df_ohlc)
engine.run_with_ticks(ticks, config)
```

```python
# api/routers/backtest.py
from fastapi import APIRouter, BackgroundTasks
from backtesting.engine import BacktestEngine

router = APIRouter()

@router.post("/run")
async def run_backtest(
    pair: str,
    start_date: str,
    end_date: str,
    background_tasks: BackgroundTasks
):
    """Lanza backtest en background"""
    task_id = generate_uuid()
    background_tasks.add_task(
        execute_backtest, 
        task_id, pair, start_date, end_date
    )
    return {"task_id": task_id, "status": "running"}

@router.get("/results/{task_id}")
async def get_backtest_results(task_id: str):
    """Obtiene resultados de backtest"""
    pass
```

---

### Configuración

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Broker
    broker_type: str = "mt5"  # mt5 | darwinex
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    darwinex_api_key: str = ""
    darwinex_account_id: str = ""
    
    # Trading params
    default_lot_size: float = 0.01
    max_spread_pips: float = 2.0
    main_tp_pips: int = 10
    main_distance_pips: int = 5
    recovery_tp_pips: int = 80
    recovery_distance_pips: int = 20
    recovery_separation_pips: int = 40
    
    # Risk management
    max_operations_per_pair: int = 50
    max_total_operations: int = 200
    max_exposure_percent: float = 30.0
    reserve_fund_percent: float = 20.0
    
    # Data
    quantdata_path: str = "/data/quantdata"
    
    class Config:
        env_file = ".env"
```

```python
# config/pairs_config.py
PAIRS_CONFIG = {
    "EURUSD": {
        "enabled": True,
        "lot_size": 0.01,
        "max_spread": 1.5,
        "tp_principal": 10,
        "tp_recovery": 80,
        "spread_promedio": 0.2,
        "sesiones_activas": ["London", "NewYork"],
        "correlation_group": "EUR",
        "filtro_volatilidad_min": 10  # pips mínimos de rango diario
    },
    "GBPUSD": {
        "enabled": True,
        "lot_size": 0.01,
        "max_spread": 2.0,
        "tp_principal": 12,  # Más volátil, TPs más amplios
        "tp_recovery": 85,
        "spread_promedio": 0.5,
        "sesiones_activas": ["London", "NewYork"],
        "correlation_group": "GBP",
        "filtro_volatilidad_min": 15
    },
    "USDJPY": {
        "enabled": True,
        "lot_size": 0.01,
        "max_spread": 1.5,
        "tp_principal": 8,   # Pips más pequeños en JPY
        "tp_recovery": 70,
        "spread_promedio": 0.3,
        "sesiones_activas": ["Tokyo", "London", "NewYork"],
        "correlation_group": "JPY",
        "ajuste_sesion_asia": True
    },
    "AUDUSD": {
        "enabled": False,  # Deshabilitado por alta correlación con otros
        "lot_size": 0.01,
        "max_spread": 2.0,
        "correlation_group": "AUD"
    }
}
```

---

### Filtros de Mercado

```python
# application/services/market_filters.py
from datetime import datetime
from typing import Dict, Tuple

class MarketFilters:
    """Filtros que determinan si las condiciones son favorables para operar"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def debe_operar(
        self, 
        pair: str,
        current_price: float,
        current_spread: float,
        recent_data: list
    ) -> Tuple[bool, str]:
        """
        Evalúa todas las condiciones para operar
        
        Returns:
            (puede_operar, razon_si_no)
        """
        # 1. Filtro de spread
        max_spread = self.config.get('max_spread', 2.0)
        if current_spread > max_spread:
            return False, f"Spread alto: {current_spread:.1f} > {max_spread}"
        
        # 2. Filtro de volatilidad mínima
        volatility = self._calculate_recent_volatility(recent_data)
        min_vol = self.config.get('filtro_volatilidad_min', 10)
        if volatility < min_vol:
            return False, f"Volatilidad baja: {volatility:.1f} < {min_vol} pips"
        
        # 3. Filtro de horario
        hora = datetime.now().hour
        if not self._is_active_session(hora, pair):
            return False, f"Fuera de sesión activa para {pair}"
        
        # 4. Filtro de gaps recientes (apertura de mercado)
        if self._near_market_open():
            return False, "Cerca de apertura de mercado, esperando estabilización"
        
        return True, "OK"
    
    def _calculate_recent_volatility(self, recent_data: list, periods: int = 24) -> float:
        """Calcula volatilidad reciente en pips (rango high-low promedio)"""
        if len(recent_data) < periods:
            return 0
        
        ranges = []
        for candle in recent_data[-periods:]:
            range_pips = (candle['high'] - candle['low']) * 10000
            ranges.append(range_pips)
        
        return sum(ranges) / len(ranges)
    
    def _is_active_session(self, hora: int, pair: str) -> bool:
        """Verifica si estamos en sesión activa para el par"""
        sessions = {
            'Tokyo': range(0, 9),      # 00:00 - 09:00 UTC
            'London': range(7, 16),    # 07:00 - 16:00 UTC
            'NewYork': range(12, 21)   # 12:00 - 21:00 UTC
        }
        
        pair_sessions = self.config.get('sesiones_activas', ['London', 'NewYork'])
        
        for session_name in pair_sessions:
            if hora in sessions.get(session_name, []):
                return True
        
        return False
    
    def _near_market_open(self) -> bool:
        """Detecta si estamos cerca de apertura de mercado (domingo noche)"""
        now = datetime.now()
        # Domingo 21:00 - 23:59 o Lunes 00:00 - 01:00 UTC
        if now.weekday() == 6 and now.hour >= 21:  # Domingo tarde
            return True
        if now.weekday() == 0 and now.hour < 2:    # Lunes madrugada
            return True
        return False
```

```python
# application/services/spread_controller.py
class SpreadController:
    """Controla que no se abran operaciones con spreads altos"""
    
    def __init__(self, broker, config):
        self.broker = broker
        self.config = config
        self.spread_history = {}  # {pair: [spreads]}
    
    async def is_acceptable(self, pair: str) -> bool:
        """Verifica si el spread actual es aceptable"""
        current_spread = await self.broker.get_spread(pair)
        max_spread = self.config.get(pair, {}).get('max_spread', 2.0)
        
        # Guardar histórico
        if pair not in self.spread_history:
            self.spread_history[pair] = []
        self.spread_history[pair].append(current_spread)
        
        # Mantener solo últimos 100
        if len(self.spread_history[pair]) > 100:
            self.spread_history[pair] = self.spread_history[pair][-100:]
        
        return current_spread <= max_spread
    
    def get_average_spread(self, pair: str) -> float:
        """Retorna spread promedio reciente"""
        if pair not in self.spread_history or not self.spread_history[pair]:
            return 0
        return sum(self.spread_history[pair]) / len(self.spread_history[pair])
```

---

### Datos Históricos

**Fuente:** QuantDataManager  
**Cobertura:** 15 años de datos históricos  
**Calidad:** Verificado sin nulls  
**Formatos disponibles:** Tick data, M1, M5, M15, H1, D1

```python
# infrastructure/data/quantdata_loader.py
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, List

class QuantDataLoader:
    """Cargador de datos de QuantDataManager (15 años, sin nulls)"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    def load_pair(
        self, 
        pair: str, 
        timeframe: str = "tick",
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """Carga datos de un par con filtros opcionales de fecha"""
        
        # Buscar archivo (soporta parquet y csv)
        file_path = self._find_data_file(pair, timeframe)
        
        if file_path.suffix == '.parquet':
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path, parse_dates=['timestamp'], index_col='timestamp')
        
        # Filtrar por fechas
        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]
        
        # Verificar calidad
        self._validate_data(df, pair)
        
        print(f"✅ Cargados {len(df):,} registros de {pair} ({timeframe})")
        print(f"   Rango: {df.index.min()} → {df.index.max()}")
        
        return df
    
    def _find_data_file(self, pair: str, timeframe: str) -> Path:
        """Busca el archivo de datos en diferentes formatos"""
        patterns = [
            f"{pair}_{timeframe}.parquet",
            f"{pair}_{timeframe}.csv",
            f"{pair}/{timeframe}.parquet",
            f"{pair}/{timeframe}.csv"
        ]
        
        for pattern in patterns:
            path = self.base_path / pattern
            if path.exists():
                return path
        
        raise FileNotFoundError(f"No se encontró archivo para {pair} {timeframe}")
    
    def _validate_data(self, df: pd.DataFrame, pair: str):
        """Valida calidad de datos"""
        null_count = df.isnull().sum().sum()
        if null_count > 0:
            raise ValueError(f"⚠️ {pair}: Encontrados {null_count} valores null")
        
        # Verificar columnas mínimas
        required = ['bid', 'ask'] if 'bid' in df.columns else ['open', 'high', 'low', 'close']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"⚠️ {pair}: Faltan columnas {missing}")
    
    def get_available_pairs(self) -> List[str]:
        """Lista pares disponibles"""
        pairs = set()
        for f in self.base_path.rglob("*.parquet"):
            pairs.add(f.stem.split('_')[0])
        for f in self.base_path.rglob("*.csv"):
            pairs.add(f.stem.split('_')[0])
        return sorted(pairs)
    
    def get_date_range(self, pair: str, timeframe: str = "tick") -> Tuple[str, str]:
        """Retorna rango de fechas disponible para un par"""
        df = self.load_pair(pair, timeframe)
        return str(df.index.min()), str(df.index.max())
    
    def get_data_summary(self) -> pd.DataFrame:
        """Resumen de todos los datos disponibles"""
        summary = []
        for pair in self.get_available_pairs():
            try:
                df = self.load_pair(pair, 'tick')
                summary.append({
                    'pair': pair,
                    'records': len(df),
                    'start': df.index.min(),
                    'end': df.index.max(),
                    'years': (df.index.max() - df.index.min()).days / 365
                })
            except:
                pass
        return pd.DataFrame(summary)
```

**Uso:**
```python
loader = QuantDataLoader("/data/quantdata")

# Ver pares disponibles
print(loader.get_available_pairs())
# ['EURUSD', 'GBPUSD', 'USDJPY', ...]

# Cargar datos
df = loader.load_pair('EURUSD', 'tick', start='2020-01-01', end='2024-12-31')

# Resumen completo
summary = loader.get_data_summary()
print(summary)
```

---

## Próximos Pasos

### Fase 1: Backtesting
- [ ] Configurar carga de datos QuantDataManager (15 años)
- [ ] Implementar BacktestEngine básico
- [ ] Ejecutar backtest EURUSD y GBPUSD
- [ ] Validar métricas y ajustar parámetros
- [ ] Incluir períodos de estrés (COVID 2020, tipos 2022)

### Fase 2: Infraestructura
- [ ] Setup proyecto Clean Architecture
- [ ] Implementar entidades del dominio
- [ ] Crear adaptador MT5
- [ ] Crear adaptador Darwinex API
- [ ] Implementar repositorio (PostgreSQL/SQLite)

### Fase 3: Lógica de Negocio
- [ ] Use case: OpenMainCycle
- [ ] Use case: ActivateHedge
- [ ] Use case: OpenRecovery
- [ ] Use case: CloseCycle
- [ ] Service: SpreadController
- [ ] Service: CorrelationChecker
- [ ] Service: ReserveFundManager

### Fase 4: API y Monitorización
- [ ] Endpoints FastAPI básicos
- [ ] WebSocket para tiempo real
- [ ] Dashboard de métricas
- [ ] Alertas de exposición

### Fase 5: Producción
- [ ] Tests unitarios e integración
- [ ] Deploy en servidor
- [ ] Conexión con Darwinex (paper trading)
- [ ] Validación en real con lote mínimo
- [ ] Escalado gradual

---

## Elementos Críticos del Sistema

### 🔴 Crítico: Reconciliación Broker-Sistema

El estado local del sistema puede desincronizarse del estado real en el broker.

**Escenarios de riesgo:**
- Orden enviada pero respuesta perdida por timeout
- Broker ejecuta orden pero sistema no registra
- Sistema cree que orden está pendiente pero broker ya la ejecutó

**Solución:**

```python
# infrastructure/services/reconciliation.py
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class ReconciliationService:
    """Reconcilia estado local con estado del broker"""
    
    def __init__(self, broker, repository):
        self.broker = broker
        self.repo = repository
        self.last_reconciliation = None
        self.discrepancies_log = []
    
    async def full_reconciliation(self) -> Dict:
        """
        Reconciliación completa - ejecutar cada 5 minutos
        y siempre al iniciar el sistema
        """
        report = {
            'timestamp': datetime.now(),
            'local_operations': 0,
            'broker_operations': 0,
            'matched': 0,
            'discrepancies': [],
            'actions_taken': []
        }
        
        # 1. Obtener estado del broker
        broker_positions = await self.broker.get_open_positions()
        broker_pending = await self.broker.get_pending_orders()
        
        # 2. Obtener estado local
        local_active = self.repo.get_active_operations()
        local_pending = self.repo.get_pending_operations()
        
        report['broker_operations'] = len(broker_positions) + len(broker_pending)
        report['local_operations'] = len(local_active) + len(local_pending)
        
        # 3. Comparar y detectar discrepancias
        discrepancies = self._find_discrepancies(
            broker_positions, broker_pending,
            local_active, local_pending
        )
        
        # 4. Resolver discrepancias automáticamente si es posible
        for disc in discrepancies:
            action = await self._resolve_discrepancy(disc)
            report['actions_taken'].append(action)
        
        report['discrepancies'] = discrepancies
        report['matched'] = report['local_operations'] - len(discrepancies)
        
        self.last_reconciliation = report
        return report
    
    def _find_discrepancies(
        self,
        broker_pos: List,
        broker_pend: List,
        local_active: List,
        local_pending: List
    ) -> List[Dict]:
        """Encuentra diferencias entre broker y sistema local"""
        discrepancies = []
        
        # Crear sets de IDs para comparación rápida
        broker_ids = {self._extract_local_id(p) for p in broker_pos + broker_pend}
        local_ids = {op.id for op in local_active + local_pending}
        
        # Operaciones en broker pero no en local (CRÍTICO)
        orphan_broker = broker_ids - local_ids
        for bid in orphan_broker:
            discrepancies.append({
                'type': 'ORPHAN_IN_BROKER',
                'severity': 'CRITICAL',
                'broker_id': bid,
                'action': 'IMPORT_TO_LOCAL'
            })
        
        # Operaciones en local pero no en broker
        orphan_local = local_ids - broker_ids
        for lid in orphan_local:
            local_op = self.repo.get_operation(lid)
            if local_op.status in ['ACTIVE', 'PENDING']:
                discrepancies.append({
                    'type': 'ORPHAN_IN_LOCAL',
                    'severity': 'HIGH',
                    'local_id': lid,
                    'action': 'VERIFY_AND_UPDATE_STATUS'
                })
        
        return discrepancies
    
    async def _resolve_discrepancy(self, disc: Dict) -> Dict:
        """Intenta resolver discrepancia automáticamente"""
        if disc['type'] == 'ORPHAN_IN_BROKER':
            # Importar operación del broker al sistema local
            broker_op = await self.broker.get_order_details(disc['broker_id'])
            local_op = self._convert_broker_to_local(broker_op)
            self.repo.save_operation(local_op)
            return {'action': 'IMPORTED', 'id': disc['broker_id']}
        
        elif disc['type'] == 'ORPHAN_IN_LOCAL':
            # Verificar si fue ejecutada o cancelada
            local_op = self.repo.get_operation(disc['local_id'])
            history = await self.broker.get_order_history(local_op.broker_ticket)
            
            if history and history['status'] == 'FILLED':
                local_op.status = OperationStatus.CLOSED
                local_op.profit_pips = history['profit_pips']
                self.repo.save_operation(local_op)
                return {'action': 'MARKED_AS_FILLED', 'id': disc['local_id']}
            
            elif history and history['status'] == 'CANCELLED':
                local_op.status = OperationStatus.CANCELLED
                self.repo.save_operation(local_op)
                return {'action': 'MARKED_AS_CANCELLED', 'id': disc['local_id']}
        
        return {'action': 'MANUAL_REVIEW_REQUIRED', 'discrepancy': disc}
```

---

### 🔴 Crítico: Persistencia y Recuperación de Estado

Si el sistema se cae, debe poder recuperar exactamente donde estaba.

```python
# infrastructure/persistence/state_manager.py
import json
from datetime import datetime
from pathlib import Path

class StateManager:
    """Gestiona persistencia y recuperación del estado del sistema"""
    
    def __init__(self, db_repo, state_file: Path):
        self.repo = db_repo
        self.state_file = state_file
        self.checkpoint_interval = 60  # segundos
        self.last_checkpoint = None
    
    async def create_checkpoint(self) -> str:
        """
        Crea checkpoint completo del estado
        Llamar periódicamente y antes de operaciones críticas
        """
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'version': '2.0',
            'cycles': self._serialize_cycles(),
            'operations': self._serialize_operations(),
            'pending_actions': self._serialize_pending_actions(),
            'metrics': self._serialize_metrics(),
            'config_hash': self._get_config_hash()
        }
        
        # Guardar en DB
        checkpoint_id = await self.repo.save_checkpoint(checkpoint)
        
        # Guardar también en archivo (backup)
        backup_file = self.state_file.parent / f"checkpoint_{checkpoint_id}.json"
        with open(backup_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        # Mantener solo últimos 10 checkpoints en archivo
        self._cleanup_old_checkpoints()
        
        self.last_checkpoint = checkpoint_id
        return checkpoint_id
    
    async def restore_from_checkpoint(self, checkpoint_id: str = None) -> Dict:
        """
        Restaura estado desde checkpoint
        Si no se especifica ID, usa el más reciente
        """
        if checkpoint_id is None:
            checkpoint = await self.repo.get_latest_checkpoint()
        else:
            checkpoint = await self.repo.get_checkpoint(checkpoint_id)
        
        if not checkpoint:
            raise StateRecoveryError("No checkpoint found")
        
        # Verificar integridad
        if not self._verify_checkpoint_integrity(checkpoint):
            raise StateRecoveryError("Checkpoint integrity check failed")
        
        # Restaurar estado
        restored = {
            'cycles': self._deserialize_cycles(checkpoint['cycles']),
            'operations': self._deserialize_operations(checkpoint['operations']),
            'pending_actions': checkpoint['pending_actions']
        }
        
        # Log de recuperación
        print(f"✅ Estado restaurado desde checkpoint {checkpoint['timestamp']}")
        print(f"   Ciclos: {len(restored['cycles'])}")
        print(f"   Operaciones: {len(restored['operations'])}")
        
        return restored
    
    async def startup_recovery(self) -> Dict:
        """
        Procedimiento de recuperación al iniciar el sistema
        """
        print("🔄 Iniciando recuperación de estado...")
        
        # 1. Restaurar desde último checkpoint
        try:
            state = await self.restore_from_checkpoint()
        except StateRecoveryError as e:
            print(f"⚠️ No se pudo restaurar checkpoint: {e}")
            state = {'cycles': [], 'operations': [], 'pending_actions': []}
        
        # 2. Reconciliar con broker
        reconciliation = await self.reconciliation_service.full_reconciliation()
        
        # 3. Procesar acciones pendientes que no se completaron
        for action in state.get('pending_actions', []):
            await self._retry_pending_action(action)
        
        # 4. Crear checkpoint post-recovery
        await self.create_checkpoint()
        
        return {
            'restored_state': state,
            'reconciliation': reconciliation,
            'status': 'RECOVERED'
        }
```

---

### 🔴 Crítico: Idempotencia de Órdenes

Evitar que una orden se ejecute múltiples veces.

```python
# infrastructure/services/order_executor.py
import hashlib
from datetime import datetime, timedelta

class IdempotentOrderExecutor:
    """Ejecutor de órdenes con garantía de idempotencia"""
    
    def __init__(self, broker, cache):
        self.broker = broker
        self.cache = cache  # Redis o similar
        self.order_ttl = timedelta(hours=24)
    
    async def execute_order(self, operation: Operation) -> OrderResult:
        """
        Ejecuta orden de forma idempotente
        Si la orden ya fue enviada, retorna el resultado anterior
        """
        # Generar clave única para esta orden
        idempotency_key = self._generate_idempotency_key(operation)
        
        # Verificar si ya existe
        existing = await self.cache.get(idempotency_key)
        if existing:
            print(f"⚠️ Orden {operation.id} ya ejecutada, retornando resultado cached")
            return OrderResult.from_cache(existing)
        
        # Marcar como "en proceso" para evitar duplicados concurrentes
        lock_acquired = await self.cache.set_nx(
            f"lock:{idempotency_key}", 
            "processing",
            ttl=60  # Lock de 60 segundos máximo
        )
        
        if not lock_acquired:
            # Otra instancia está procesando esta orden
            await self._wait_for_result(idempotency_key)
            return OrderResult.from_cache(await self.cache.get(idempotency_key))
        
        try:
            # Ejecutar orden
            result = await self.broker.place_order(operation)
            
            # Guardar resultado
            await self.cache.set(
                idempotency_key,
                result.to_cache(),
                ttl=self.order_ttl
            )
            
            return result
            
        finally:
            # Liberar lock
            await self.cache.delete(f"lock:{idempotency_key}")
    
    def _generate_idempotency_key(self, operation: Operation) -> str:
        """
        Genera clave única basada en características inmutables de la orden
        """
        key_components = [
            operation.id,
            operation.pair,
            str(operation.op_type.value),
            f"{operation.entry_price:.5f}",
            f"{operation.tp_price:.5f}",
            f"{operation.lot_size:.2f}"
        ]
        key_string = "|".join(key_components)
        return f"order:{hashlib.sha256(key_string.encode()).hexdigest()[:16]}"
```

---

## Sistema de Robustez y Tolerancia a Fallos

### Filosofía de Robustez

> **"El sistema asume que TODO puede fallar en cualquier momento"**

El dinero real está en juego. No hay segundas oportunidades. El sistema debe:
1. **Nunca perder estado** - Siempre saber qué operaciones existen
2. **Nunca duplicar órdenes** - Una orden = una posición
3. **Siempre recuperarse** - Cualquier fallo debe ser recuperable
4. **Fallar de forma segura** - Ante la duda, NO operar

---

### Catálogo de Errores y Mitigaciones

#### 🔴 CRÍTICOS (Pueden causar pérdida de dinero)

| Error                                   | Escenario                       | Consecuencia sin mitigar                    | Mitigación                           |
| --------------------------------------- | ------------------------------- | ------------------------------------------- | ------------------------------------ |
| Orden enviada, respuesta perdida        | Timeout de red                  | Orden existe en broker pero sistema no sabe | Idempotencia + Reconciliación        |
| Desconexión durante operación           | WiFi/Internet cae               | Estado inconsistente                        | Checkpoint antes de cada orden       |
| Crash después de TP                     | Sistema cae justo después de TP | No se procesa el TP, no se abre recovery    | Event sourcing + Recovery automático |
| Doble ejecución                         | Retry envía orden 2 veces       | 2 posiciones abiertas                       | Idempotency keys                     |
| Broker rechaza pero sistema cree que OK | Error parseado mal              | Posición fantasma en sistema                | Verificación post-orden              |

#### 🟡 ALTOS (Pueden causar problemas operativos)

| Error                 | Escenario            | Consecuencia          | Mitigación           |
| --------------------- | -------------------- | --------------------- | -------------------- |
| Rate limit del broker | Demasiadas órdenes   | Órdenes rechazadas    | Rate limiter + Queue |
| Supabase timeout      | DB lenta o caída     | No se guarda estado   | Retry + Cache local  |
| Spread spike          | Volatilidad extrema  | Entrar en mal momento | Spread controller    |
| Gap de fin de semana  | Mercado abre con gap | TP/SL saltados        | Gap handler          |

#### 🟢 MEDIOS (Degradación de servicio)

| Error                  | Escenario            | Consecuencia               | Mitigación           |
| ---------------------- | -------------------- | -------------------------- | -------------------- |
| Métricas no se guardan | Error en trigger     | Dashboard desactualizado   | Queue de métricas    |
| Alertas no se envían   | Telegram/Email caído | No te enteras de problemas | Múltiples canales    |
| Logs perdidos          | Disco lleno          | Sin trazabilidad           | Log rotation + Cloud |

---

### Arquitectura de Robustez

```
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE RESILIENCIA                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Watchdog   │  │  Health      │  │  Graceful Shutdown   │  │
│  │   Process    │  │  Monitor     │  │  Handler             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      CAPA DE COMUNICACIÓN                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Retry      │  │  Circuit     │  │  Timeout             │  │
│  │   Manager    │  │  Breaker     │  │  Manager             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Rate       │  │  Connection  │  │  Request             │  │
│  │   Limiter    │  │  Pool        │  │  Queue               │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      CAPA DE CONSISTENCIA                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Idempotency │  │  Outbox      │  │  Reconciliation      │  │
│  │  Manager     │  │  Pattern     │  │  Engine              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Event       │  │  Dead Letter │  │  Compensation        │  │
│  │  Store       │  │  Queue       │  │  Manager             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Retry Manager con Backoff Exponencial

```python
# infrastructure/resilience/retry_manager.py
import asyncio
import random
from typing import TypeVar, Callable, Optional, List, Type
from dataclasses import dataclass
from datetime import datetime
import logging

T = TypeVar('T')

@dataclass
class RetryConfig:
    """Configuración de reintentos"""
    max_attempts: int = 3
    base_delay: float = 1.0          # segundos
    max_delay: float = 60.0          # segundos
    exponential_base: float = 2.0
    jitter: bool = True              # Añade aleatoriedad para evitar thundering herd
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()

class RetryManager:
    """
    Gestor de reintentos con backoff exponencial y jitter.
    
    Patrón: Espera entre reintentos crece exponencialmente
    Jitter: Añade aleatoriedad para evitar que todos los reintentos ocurran a la vez
    """
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        operation_name: str = "operation",
        on_retry: Optional[Callable] = None,
        **kwargs
    ) -> T:
        """
        Ejecuta función con reintentos automáticos.
        
        Args:
            func: Función async a ejecutar
            operation_name: Nombre para logging
            on_retry: Callback opcional cuando hay retry
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 1:
                    self.logger.info(
                        f"✅ {operation_name} exitoso en intento {attempt}"
                    )
                
                return result
                
            except self.config.non_retryable_exceptions as e:
                # Errores que no tienen sentido reintentar
                self.logger.error(
                    f"❌ {operation_name} falló con error no-retryable: {e}"
                )
                raise
                
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    self.logger.error(
                        f"❌ {operation_name} falló después de {attempt} intentos: {e}"
                    )
                    raise
                
                # Calcular delay con backoff exponencial
                delay = self._calculate_delay(attempt)
                
                self.logger.warning(
                    f"⚠️ {operation_name} intento {attempt} falló: {e}. "
                    f"Reintentando en {delay:.2f}s..."
                )
                
                if on_retry:
                    await on_retry(attempt, e, delay)
                
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calcula delay con backoff exponencial y jitter opcional"""
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** (attempt - 1)),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Jitter: delay aleatorio entre 0 y delay calculado
            delay = random.uniform(0, delay)
        
        return delay


# Configuraciones predefinidas para diferentes operaciones
RETRY_CONFIGS = {
    'broker_order': RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        retryable_exceptions=(TimeoutError, ConnectionError),
        non_retryable_exceptions=(ValueError, PermissionError)  # Errores de lógica
    ),
    'database': RetryConfig(
        max_attempts=5,
        base_delay=0.2,
        max_delay=10.0,
        retryable_exceptions=(TimeoutError, ConnectionError)
    ),
    'reconciliation': RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0
    )
}
```

---

### Circuit Breaker Mejorado

```python
# infrastructure/resilience/circuit_breaker.py
import asyncio
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict
from dataclasses import dataclass, field
import logging

class CircuitState(Enum):
    CLOSED = "closed"       # Funcionando normal
    OPEN = "open"           # Bloqueado, no permite llamadas
    HALF_OPEN = "half_open" # Probando si se recuperó

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Fallos para abrir
    success_threshold: int = 3          # Éxitos para cerrar desde half-open
    timeout: timedelta = timedelta(seconds=60)  # Tiempo en OPEN antes de HALF_OPEN
    half_open_max_calls: int = 3        # Llamadas permitidas en HALF_OPEN
    excluded_exceptions: tuple = ()      # Excepciones que no cuentan como fallo

@dataclass
class CircuitStats:
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0
    total_blocked: int = 0
    state_changes: list = field(default_factory=list)

class CircuitBreaker:
    """
    Circuit Breaker pattern mejorado.
    
    Estados:
    - CLOSED: Funcionando normal, contando fallos
    - OPEN: Bloqueado, rechaza todas las llamadas
    - HALF_OPEN: Permitiendo algunas llamadas para probar recuperación
    """
    
    def __init__(
        self, 
        name: str,
        config: CircuitBreakerConfig = None,
        on_state_change: Optional[Callable] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change
        
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self.half_open_calls = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Ejecuta función protegida por circuit breaker"""
        
        # Verificar si podemos ejecutar
        if not self._can_execute():
            self.stats.total_blocked += 1
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' está OPEN. "
                f"Bloqueado hasta {self._time_until_half_open()}"
            )
        
        self.stats.total_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.config.excluded_exceptions:
            # Estas excepciones no cuentan como fallo del servicio
            raise
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _can_execute(self) -> bool:
        """Determina si se puede ejecutar una llamada"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Verificar si es hora de probar (pasar a HALF_OPEN)
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Permitir número limitado de llamadas
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return False
    
    def _on_success(self):
        """Registra éxito"""
        self.stats.successes += 1
        self.stats.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.successes >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        
        elif self.state == CircuitState.CLOSED:
            # Reset contador de fallos después de éxito
            self.stats.failures = 0
    
    def _on_failure(self, exception: Exception):
        """Registra fallo"""
        self.stats.failures += 1
        self.stats.total_failures += 1
        self.stats.last_failure_time = datetime.now()
        
        self.logger.warning(
            f"Circuit breaker '{self.name}' registró fallo "
            f"({self.stats.failures}/{self.config.failure_threshold}): {exception}"
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # Un fallo en HALF_OPEN vuelve a OPEN
            self._transition_to(CircuitState.OPEN)
        
        elif self.state == CircuitState.CLOSED:
            if self.stats.failures >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def _transition_to(self, new_state: CircuitState):
        """Transiciona a nuevo estado"""
        old_state = self.state
        self.state = new_state
        
        # Reset contadores según el nuevo estado
        if new_state == CircuitState.CLOSED:
            self.stats.failures = 0
            self.stats.successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.half_open_calls = 0
            self.stats.successes = 0
        elif new_state == CircuitState.OPEN:
            self.stats.successes = 0
        
        # Registrar cambio
        change = {
            'from': old_state.value,
            'to': new_state.value,
            'timestamp': datetime.now().isoformat()
        }
        self.stats.state_changes.append(change)
        
        self.logger.info(
            f"🔄 Circuit breaker '{self.name}': {old_state.value} → {new_state.value}"
        )
        
        # Callback opcional
        if self.on_state_change:
            self.on_state_change(self.name, old_state, new_state)
    
    def _should_attempt_reset(self) -> bool:
        """Verifica si es hora de intentar recuperación"""
        if self.stats.last_failure_time is None:
            return True
        
        elapsed = datetime.now() - self.stats.last_failure_time
        return elapsed >= self.config.timeout
    
    def _time_until_half_open(self) -> str:
        """Tiempo restante hasta intentar recuperación"""
        if self.stats.last_failure_time is None:
            return "ahora"
        
        elapsed = datetime.now() - self.stats.last_failure_time
        remaining = self.config.timeout - elapsed
        
        if remaining.total_seconds() <= 0:
            return "ahora"
        
        return f"{remaining.total_seconds():.0f}s"
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del circuit breaker"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failures': self.stats.failures,
            'successes': self.stats.successes,
            'total_calls': self.stats.total_calls,
            'total_failures': self.stats.total_failures,
            'total_blocked': self.stats.total_blocked,
            'last_failure': self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            'recent_state_changes': self.stats.state_changes[-5:]
        }
    
    def force_open(self):
        """Fuerza apertura del circuit breaker (para emergencias)"""
        self._transition_to(CircuitState.OPEN)
        self.logger.warning(f"⚠️ Circuit breaker '{self.name}' forzado a OPEN")
    
    def force_close(self):
        """Fuerza cierre del circuit breaker (para recuperación manual)"""
        self._transition_to(CircuitState.CLOSED)
        self.logger.info(f"✅ Circuit breaker '{self.name}' forzado a CLOSED")


class CircuitBreakerOpen(Exception):
    """Excepción cuando el circuit breaker está abierto"""
    pass


# Registry global de circuit breakers
class CircuitBreakerRegistry:
    """Registro centralizado de circuit breakers"""
    
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_or_create(
        cls, 
        name: str, 
        config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]
    
    @classmethod
    def get_all_stats(cls) -> Dict:
        return {name: cb.get_stats() for name, cb in cls._breakers.items()}
    
    @classmethod
    def force_open_all(cls):
        """Abre todos los circuit breakers (parada de emergencia)"""
        for cb in cls._breakers.values():
            cb.force_open()
```

---

### Outbox Pattern para Consistencia

```python
# infrastructure/resilience/outbox.py
"""
Outbox Pattern: Garantiza que las operaciones de DB y broker 
ocurran de forma consistente.

Problema: Si guardamos en DB pero el broker falla, o viceversa,
tenemos inconsistencia.

Solución: Guardamos la intención en una tabla "outbox" dentro de
la misma transacción de DB. Un proceso separado lee el outbox
y ejecuta las operaciones del broker.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
import json
import asyncio

class OutboxStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

@dataclass
class OutboxEntry:
    id: str
    operation_type: str      # 'place_order', 'cancel_order', 'close_position'
    payload: Dict            # Datos de la operación
    status: OutboxStatus
    attempts: int
    max_attempts: int
    created_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]
    idempotency_key: str

class OutboxProcessor:
    """
    Procesa entradas del outbox de forma confiable.
    
    Flujo:
    1. Use case guarda operación en outbox (misma transacción que ciclo)
    2. Este procesador lee pendientes y ejecuta en broker
    3. Si falla, reintenta con backoff
    4. Si excede max_attempts, va a dead letter queue
    """
    
    def __init__(
        self,
        repository,
        broker,
        retry_manager: RetryManager,
        poll_interval: float = 1.0
    ):
        self.repo = repository
        self.broker = broker
        self.retry_manager = retry_manager
        self.poll_interval = poll_interval
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Inicia el procesador en background"""
        self.running = True
        self.logger.info("📤 Outbox processor iniciado")
        
        while self.running:
            try:
                await self._process_pending()
            except Exception as e:
                self.logger.error(f"Error en outbox processor: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Detiene el procesador de forma graceful"""
        self.running = False
        self.logger.info("📤 Outbox processor detenido")
    
    async def _process_pending(self):
        """Procesa todas las entradas pendientes"""
        entries = await self.repo.get_pending_outbox_entries(limit=10)
        
        for entry in entries:
            await self._process_entry(entry)
    
    async def _process_entry(self, entry: OutboxEntry):
        """Procesa una entrada individual"""
        # Marcar como processing
        await self.repo.update_outbox_status(
            entry.id, 
            OutboxStatus.PROCESSING
        )
        
        try:
            # Ejecutar operación en broker
            result = await self._execute_broker_operation(entry)
            
            # Marcar como completado
            await self.repo.update_outbox_status(
                entry.id,
                OutboxStatus.COMPLETED,
                processed_at=datetime.now()
            )
            
            self.logger.info(
                f"✅ Outbox {entry.id} procesado: {entry.operation_type}"
            )
            
        except Exception as e:
            entry.attempts += 1
            
            if entry.attempts >= entry.max_attempts:
                # Mover a dead letter queue
                await self.repo.update_outbox_status(
                    entry.id,
                    OutboxStatus.DEAD_LETTER,
                    error_message=str(e)
                )
                self.logger.error(
                    f"💀 Outbox {entry.id} movido a dead letter: {e}"
                )
                
                # Alerta crítica
                await self._alert_dead_letter(entry, e)
            else:
                # Reintentar después
                await self.repo.update_outbox_status(
                    entry.id,
                    OutboxStatus.PENDING,
                    attempts=entry.attempts,
                    error_message=str(e)
                )
                self.logger.warning(
                    f"⚠️ Outbox {entry.id} reintento {entry.attempts}: {e}"
                )
    
    async def _execute_broker_operation(self, entry: OutboxEntry):
        """Ejecuta la operación del broker según el tipo"""
        payload = entry.payload
        
        if entry.operation_type == 'place_order':
            return await self.broker.place_order_raw(
                pair=payload['pair'],
                order_type=payload['order_type'],
                price=payload['price'],
                tp=payload['tp'],
                lot_size=payload['lot_size'],
                comment=payload['comment']
            )
        
        elif entry.operation_type == 'cancel_order':
            return await self.broker.cancel_order(payload['ticket'])
        
        elif entry.operation_type == 'close_position':
            return await self.broker.close_position(payload['ticket'])
        
        else:
            raise ValueError(f"Tipo de operación desconocido: {entry.operation_type}")
    
    async def _alert_dead_letter(self, entry: OutboxEntry, error: Exception):
        """Envía alerta cuando una operación va a dead letter"""
        # Esto es crítico - requiere intervención manual
        await self.repo.create_alert(
            severity='critical',
            alert_type='dead_letter_operation',
            message=f"Operación {entry.operation_type} falló después de {entry.max_attempts} intentos",
            metadata={
                'outbox_id': entry.id,
                'operation_type': entry.operation_type,
                'payload': entry.payload,
                'error': str(error)
            }
        )


# Tabla SQL para outbox
OUTBOX_TABLE_SQL = """
CREATE TABLE outbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    
    CONSTRAINT valid_outbox_status CHECK (status IN (
        'pending', 'processing', 'completed', 'failed', 'dead_letter'
    ))
);

CREATE INDEX idx_outbox_pending ON outbox(created_at) 
    WHERE status = 'pending';
CREATE INDEX idx_outbox_dead_letter ON outbox(created_at)
    WHERE status = 'dead_letter';
"""
```

---

### Dead Letter Queue y Compensación

```python
# infrastructure/resilience/dead_letter.py
"""
Dead Letter Queue: Operaciones que fallaron después de todos los reintentos.
Requieren intervención manual o compensación automática.
"""

from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class DeadLetterAction(Enum):
    MANUAL_REVIEW = "manual_review"
    AUTO_COMPENSATE = "auto_compensate"
    RETRY = "retry"
    DISCARD = "discard"

class DeadLetterProcessor:
    """Procesa operaciones en dead letter queue"""
    
    def __init__(self, repository, broker, reconciliation_service):
        self.repo = repository
        self.broker = broker
        self.reconciliation = reconciliation_service
        self.logger = logging.getLogger(__name__)
    
    async def process_dead_letters(self) -> List[Dict]:
        """
        Procesa todas las entradas en dead letter.
        Intenta compensación automática cuando es posible.
        """
        entries = await self.repo.get_dead_letter_entries()
        results = []
        
        for entry in entries:
            result = await self._process_entry(entry)
            results.append(result)
        
        return results
    
    async def _process_entry(self, entry: Dict) -> Dict:
        """Procesa una entrada de dead letter"""
        operation_type = entry['operation_type']
        payload = entry['payload']
        
        # Determinar acción según tipo de operación
        action = self._determine_action(entry)
        
        if action == DeadLetterAction.AUTO_COMPENSATE:
            return await self._auto_compensate(entry)
        
        elif action == DeadLetterAction.RETRY:
            return await self._retry_with_reconciliation(entry)
        
        else:
            # Requiere revisión manual
            return {
                'entry_id': entry['id'],
                'action': 'manual_review_required',
                'reason': 'No se puede compensar automáticamente'
            }
    
    def _determine_action(self, entry: Dict) -> DeadLetterAction:
        """Determina qué acción tomar con la entrada"""
        operation_type = entry['operation_type']
        error = entry.get('error_message', '')
        
        # Órdenes de apertura que fallaron: verificar si existe en broker
        if operation_type == 'place_order':
            return DeadLetterAction.RETRY  # Reconciliación verificará
        
        # Cancelaciones: verificar estado actual
        if operation_type == 'cancel_order':
            return DeadLetterAction.RETRY
        
        # Cierres: crítico, necesita revisión
        if operation_type == 'close_position':
            return DeadLetterAction.MANUAL_REVIEW
        
        return DeadLetterAction.MANUAL_REVIEW
    
    async def _auto_compensate(self, entry: Dict) -> Dict:
        """Intenta compensación automática"""
        # Por ejemplo: si intentamos abrir una orden que ya existe,
        # simplemente actualizamos el estado local
        
        operation_type = entry['operation_type']
        payload = entry['payload']
        
        if operation_type == 'place_order':
            # Verificar si la orden realmente se creó
            ticket = payload.get('expected_ticket')
            if ticket:
                broker_order = await self.broker.get_order_details(ticket)
                if broker_order:
                    # La orden sí existe, actualizar estado local
                    await self.repo.update_operation_from_broker(
                        payload['operation_id'],
                        broker_order
                    )
                    
                    # Marcar dead letter como resuelta
                    await self.repo.resolve_dead_letter(
                        entry['id'],
                        resolution='auto_compensated',
                        notes='Orden encontrada en broker'
                    )
                    
                    return {
                        'entry_id': entry['id'],
                        'action': 'auto_compensated',
                        'result': 'Order found in broker, state synced'
                    }
        
        return {
            'entry_id': entry['id'],
            'action': 'compensation_failed',
            'reason': 'Could not auto-compensate'
        }
    
    async def _retry_with_reconciliation(self, entry: Dict) -> Dict:
        """Reintenta después de reconciliar estado"""
        # Primero reconciliar para tener estado correcto
        await self.reconciliation.full_reconciliation()
        
        # Luego mover de vuelta a pending
        await self.repo.retry_dead_letter(entry['id'])
        
        return {
            'entry_id': entry['id'],
            'action': 'retried_after_reconciliation'
        }
```

---

### Health Monitor y Watchdog

```python
# infrastructure/resilience/health_monitor.py
"""
Sistema de monitoreo de salud y watchdog.
Detecta problemas y toma acciones correctivas.
"""

import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Callable
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    name: str
    check_func: Callable
    timeout: float = 5.0
    critical: bool = False  # Si es crítico, fallo = shutdown

@dataclass 
class HealthResult:
    name: str
    status: HealthStatus
    message: str
    latency_ms: float
    timestamp: datetime

class HealthMonitor:
    """
    Monitorea la salud de todos los componentes del sistema.
    """
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.results: Dict[str, HealthResult] = {}
        self.on_status_change: List[Callable] = []
        self.logger = logging.getLogger(__name__)
    
    def register_check(self, check: HealthCheck):
        """Registra un health check"""
        self.checks.append(check)
    
    async def run_all_checks(self) -> Dict[str, HealthResult]:
        """Ejecuta todos los health checks"""
        for check in self.checks:
            result = await self._run_check(check)
            
            # Detectar cambio de estado
            if check.name in self.results:
                old_status = self.results[check.name].status
                if old_status != result.status:
                    await self._notify_status_change(check.name, old_status, result.status)
            
            self.results[check.name] = result
        
        return self.results
    
    async def _run_check(self, check: HealthCheck) -> HealthResult:
        """Ejecuta un health check individual"""
        start = datetime.now()
        
        try:
            result = await asyncio.wait_for(
                check.check_func(),
                timeout=check.timeout
            )
            
            latency = (datetime.now() - start).total_seconds() * 1000
            
            return HealthResult(
                name=check.name,
                status=HealthStatus.HEALTHY,
                message=str(result),
                latency_ms=latency,
                timestamp=datetime.now()
            )
            
        except asyncio.TimeoutError:
            return HealthResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Timeout después de {check.timeout}s",
                latency_ms=check.timeout * 1000,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(datetime.now() - start).total_seconds() * 1000,
                timestamp=datetime.now()
            )
    
    async def _notify_status_change(self, name: str, old: HealthStatus, new: HealthStatus):
        """Notifica cambio de estado"""
        self.logger.warning(
            f"🔔 Health status change: {name} {old.value} → {new.value}"
        )
        
        for callback in self.on_status_change:
            try:
                await callback(name, old, new)
            except Exception as e:
                self.logger.error(f"Error en callback de health: {e}")
    
    def get_overall_status(self) -> HealthStatus:
        """Calcula estado general del sistema"""
        if not self.results:
            return HealthStatus.UNHEALTHY
        
        statuses = [r.status for r in self.results.values()]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY


class Watchdog:
    """
    Proceso watchdog que monitorea y reinicia componentes.
    """
    
    def __init__(
        self,
        health_monitor: HealthMonitor,
        check_interval: float = 10.0,
        max_consecutive_failures: int = 3
    ):
        self.health = health_monitor
        self.check_interval = check_interval
        self.max_consecutive_failures = max_consecutive_failures
        
        self.consecutive_failures: Dict[str, int] = {}
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Inicia el watchdog"""
        self.running = True
        self.logger.info("🐕 Watchdog iniciado")
        
        while self.running:
            await self._check_and_act()
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Detiene el watchdog"""
        self.running = False
        self.logger.info("🐕 Watchdog detenido")
    
    async def _check_and_act(self):
        """Ejecuta checks y toma acciones si es necesario"""
        results = await self.health.run_all_checks()
        
        for name, result in results.items():
            if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                self.consecutive_failures[name] = self.consecutive_failures.get(name, 0) + 1
                
                if self.consecutive_failures[name] >= self.max_consecutive_failures:
                    await self._take_action(name, result)
            else:
                self.consecutive_failures[name] = 0
    
    async def _take_action(self, name: str, result: HealthResult):
        """Toma acción correctiva"""
        self.logger.error(
            f"🚨 {name} unhealthy por {self.consecutive_failures[name]} checks consecutivos"
        )
        
        # Acciones según el componente
        if name == 'broker_connection':
            await self._reconnect_broker()
        elif name == 'database':
            await self._reconnect_database()
        elif name == 'memory':
            await self._handle_memory_pressure()
        elif name == 'circuit_breakers':
            await self._handle_circuit_breaker_issues()
        
        # Reset contador
        self.consecutive_failures[name] = 0
    
    async def _reconnect_broker(self):
        """Intenta reconectar al broker"""
        self.logger.info("🔄 Intentando reconectar al broker...")
        # Implementar reconexión
    
    async def _reconnect_database(self):
        """Intenta reconectar a la base de datos"""
        self.logger.info("🔄 Intentando reconectar a la base de datos...")
        # Implementar reconexión
    
    async def _handle_memory_pressure(self):
        """Maneja presión de memoria"""
        self.logger.warning("🧹 Limpiando memoria...")
        import gc
        gc.collect()
    
    async def _handle_circuit_breaker_issues(self):
        """Maneja problemas de circuit breakers"""
        self.logger.warning("🔌 Verificando circuit breakers...")
        stats = CircuitBreakerRegistry.get_all_stats()
        for name, stat in stats.items():
            if stat['state'] == 'open':
                self.logger.warning(f"Circuit breaker {name} está OPEN")


# Health checks predefinidos
def create_standard_health_checks(broker, repository, circuit_breakers) -> List[HealthCheck]:
    """Crea los health checks estándar del sistema"""
    
    async def check_broker():
        # Verificar conexión con broker
        connected = await broker.is_connected()
        if not connected:
            raise Exception("Broker desconectado")
        
        # Verificar latencia
        start = datetime.now()
        await broker.get_account_info()
        latency = (datetime.now() - start).total_seconds() * 1000
        
        if latency > 5000:
            raise Exception(f"Latencia alta: {latency}ms")
        
        return f"OK, latency: {latency:.0f}ms"
    
    async def check_database():
        # Verificar conexión con DB
        result = await repository.health_check()
        return f"OK, {result}"
    
    async def check_memory():
        # Verificar uso de memoria
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            raise Exception(f"Memoria crítica: {memory.percent}%")
        if memory.percent > 80:
            return f"WARNING: {memory.percent}%"
        return f"OK: {memory.percent}%"
    
    async def check_disk():
        # Verificar espacio en disco
        disk = psutil.disk_usage('/')
        if disk.percent > 95:
            raise Exception(f"Disco crítico: {disk.percent}%")
        return f"OK: {disk.percent}%"
    
    async def check_circuit_breakers():
        # Verificar estado de circuit breakers
        stats = CircuitBreakerRegistry.get_all_stats()
        open_breakers = [n for n, s in stats.items() if s['state'] == 'open']
        
        if open_breakers:
            raise Exception(f"Circuit breakers abiertos: {open_breakers}")
        return f"OK, {len(stats)} breakers healthy"
    
    async def check_reconciliation():
        # Verificar última reconciliación exitosa
        last = await repository.get_last_successful_reconciliation()
        if last is None:
            raise Exception("Nunca se ha reconciliado")
        
        age = datetime.now() - last['created_at']
        if age > timedelta(minutes=10):
            raise Exception(f"Última reconciliación hace {age}")
        
        return f"OK, última hace {age.total_seconds():.0f}s"
    
    return [
        HealthCheck("broker_connection", check_broker, timeout=10.0, critical=True),
        HealthCheck("database", check_database, timeout=5.0, critical=True),
        HealthCheck("memory", check_memory, timeout=2.0),
        HealthCheck("disk", check_disk, timeout=2.0),
        HealthCheck("circuit_breakers", check_circuit_breakers, timeout=2.0),
        HealthCheck("reconciliation", check_reconciliation, timeout=5.0),
    ]
```

---

### Graceful Shutdown

```python
# infrastructure/resilience/shutdown.py
"""
Graceful Shutdown: Apagar el sistema de forma segura.
Crítico para no dejar operaciones a medias.
"""

import asyncio
import signal
from typing import Callable, List
from datetime import datetime
import logging

class GracefulShutdown:
    """
    Maneja el apagado ordenado del sistema.
    
    Orden de apagado:
    1. Dejar de aceptar nuevas operaciones
    2. Esperar a que operaciones en curso terminen
    3. Crear checkpoint del estado
    4. Cerrar conexiones
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.shutdown_started = False
        self.shutdown_complete = False
        self.handlers: List[Callable] = []
        self.logger = logging.getLogger(__name__)
    
    def register_handler(self, handler: Callable, priority: int = 0):
        """
        Registra un handler de shutdown.
        Priority: menor = ejecuta primero
        """
        self.handlers.append((priority, handler))
        self.handlers.sort(key=lambda x: x[0])
    
    def setup_signal_handlers(self):
        """Configura handlers de señales del sistema"""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s))
            )
        
        self.logger.info("🛑 Signal handlers configurados")
    
    async def shutdown(self, sig=None):
        """Ejecuta shutdown ordenado"""
        if self.shutdown_started:
            self.logger.warning("Shutdown ya en progreso, ignorando")
            return
        
        self.shutdown_started = True
        self.logger.warning(
            f"🛑 Iniciando shutdown (señal: {sig.name if sig else 'manual'})..."
        )
        
        start = datetime.now()
        
        try:
            # Ejecutar todos los handlers con timeout
            for priority, handler in self.handlers:
                handler_name = handler.__name__
                self.logger.info(f"Ejecutando handler: {handler_name}")
                
                try:
                    await asyncio.wait_for(
                        handler(),
                        timeout=self.timeout / len(self.handlers)
                    )
                    self.logger.info(f"✅ {handler_name} completado")
                except asyncio.TimeoutError:
                    self.logger.error(f"⏱️ {handler_name} timeout")
                except Exception as e:
                    self.logger.error(f"❌ {handler_name} error: {e}")
            
            elapsed = (datetime.now() - start).total_seconds()
            self.logger.info(f"✅ Shutdown completado en {elapsed:.1f}s")
            
        finally:
            self.shutdown_complete = True


# Handlers de shutdown estándar
async def create_shutdown_handlers(
    trading_engine,
    outbox_processor,
    watchdog,
    health_monitor,
    state_manager,
    broker,
    repository
) -> List[tuple]:
    """Crea los handlers de shutdown en orden"""
    
    async def stop_new_operations():
        """Para aceptación de nuevas operaciones"""
        trading_engine.pause_all()
        logging.info("Nuevas operaciones pausadas")
    
    async def wait_pending_operations():
        """Espera a que operaciones en curso terminen"""
        max_wait = 10
        while trading_engine.has_pending_operations() and max_wait > 0:
            await asyncio.sleep(1)
            max_wait -= 1
        logging.info("Operaciones pendientes completadas o timeout")
    
    async def stop_background_tasks():
        """Detiene tareas de background"""
        await outbox_processor.stop()
        await watchdog.stop()
        logging.info("Tareas de background detenidas")
    
    async def create_final_checkpoint():
        """Crea checkpoint final del estado"""
        await state_manager.create_checkpoint()
        logging.info("Checkpoint final creado")
    
    async def final_reconciliation():
        """Reconciliación final antes de cerrar"""
        try:
            from infrastructure.services.reconciliation import ReconciliationService
            recon = ReconciliationService(broker, repository)
            await recon.full_reconciliation()
            logging.info("Reconciliación final completada")
        except Exception as e:
            logging.error(f"Error en reconciliación final: {e}")
    
    async def close_broker():
        """Cierra conexión con broker"""
        await broker.disconnect()
        logging.info("Conexión con broker cerrada")
    
    async def close_database():
        """Cierra conexión con base de datos"""
        await repository.close()
        logging.info("Conexión con base de datos cerrada")
    
    return [
        (1, stop_new_operations),
        (2, wait_pending_operations),
        (3, stop_background_tasks),
        (4, create_final_checkpoint),
        (5, final_reconciliation),
        (6, close_broker),
        (7, close_database),
    ]
```

---

### Reconexión Automática

```python
# infrastructure/resilience/auto_reconnect.py
"""
Sistema de reconexión automática para broker y base de datos.
"""

import asyncio
from typing import Callable, Optional
from datetime import datetime, timedelta
import logging

class AutoReconnect:
    """
    Gestiona reconexión automática de conexiones.
    """
    
    def __init__(
        self,
        name: str,
        connect_func: Callable,
        disconnect_func: Callable,
        health_check_func: Callable,
        max_retries: int = 10,
        base_delay: float = 1.0,
        max_delay: float = 300.0,  # 5 minutos máximo entre reintentos
    ):
        self.name = name
        self.connect = connect_func
        self.disconnect = disconnect_func
        self.health_check = health_check_func
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        self.is_connected = False
        self.reconnect_attempts = 0
        self.last_connected = None
        self.last_disconnected = None
        
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        
        self.logger = logging.getLogger(__name__)
    
    async def ensure_connected(self) -> bool:
        """Asegura que estamos conectados, reconectando si es necesario"""
        if await self._check_connection():
            return True
        
        return await self._reconnect()
    
    async def _check_connection(self) -> bool:
        """Verifica si la conexión está activa"""
        try:
            await asyncio.wait_for(self.health_check(), timeout=5.0)
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False
    
    async def _reconnect(self) -> bool:
        """Intenta reconectar con backoff exponencial"""
        self.logger.warning(f"🔌 Iniciando reconexión de {self.name}...")
        
        # Notificar desconexión
        if self.on_disconnected:
            await self.on_disconnected()
        
        self.last_disconnected = datetime.now()
        
        for attempt in range(1, self.max_retries + 1):
            self.reconnect_attempts = attempt
            
            try:
                # Intentar desconectar limpiamente primero
                try:
                    await self.disconnect()
                except Exception:
                    pass
                
                # Intentar conectar
                await asyncio.wait_for(self.connect(), timeout=30.0)
                
                # Verificar que la conexión funciona
                if await self._check_connection():
                    self.is_connected = True
                    self.last_connected = datetime.now()
                    self.reconnect_attempts = 0
                    
                    self.logger.info(
                        f"✅ {self.name} reconectado en intento {attempt}"
                    )
                    
                    # Notificar conexión
                    if self.on_connected:
                        await self.on_connected()
                    
                    return True
                
            except Exception as e:
                # Calcular delay con backoff
                delay = min(
                    self.base_delay * (2 ** (attempt - 1)),
                    self.max_delay
                )
                
                self.logger.warning(
                    f"⚠️ {self.name} reconexión intento {attempt}/{self.max_retries} "
                    f"falló: {e}. Reintentando en {delay:.0f}s..."
                )
                
                await asyncio.sleep(delay)
        
        self.logger.error(
            f"❌ {self.name} no se pudo reconectar después de {self.max_retries} intentos"
        )
        return False
    
    def get_status(self) -> dict:
        """Retorna estado de la conexión"""
        return {
            'name': self.name,
            'is_connected': self.is_connected,
            'reconnect_attempts': self.reconnect_attempts,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'last_disconnected': self.last_disconnected.isoformat() if self.last_disconnected else None,
        }


class ConnectionPool:
    """
    Pool de conexiones con reconexión automática.
    Mantiene múltiples conexiones y balancea carga.
    """
    
    def __init__(self, create_connection: Callable, pool_size: int = 3):
        self.create_connection = create_connection
        self.pool_size = pool_size
        self.connections = []
        self.current_index = 0
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Inicializa el pool de conexiones"""
        for i in range(self.pool_size):
            conn = await self.create_connection()
            self.connections.append({
                'connection': conn,
                'healthy': True,
                'last_used': datetime.now()
            })
        self.logger.info(f"Connection pool inicializado con {self.pool_size} conexiones")
    
    async def get_connection(self):
        """Obtiene una conexión saludable del pool"""
        for _ in range(self.pool_size):
            self.current_index = (self.current_index + 1) % self.pool_size
            conn_info = self.connections[self.current_index]
            
            if conn_info['healthy']:
                conn_info['last_used'] = datetime.now()
                return conn_info['connection']
        
        # Todas las conexiones están unhealthy, intentar reconectar una
        await self._recover_connection(self.current_index)
        return self.connections[self.current_index]['connection']
    
    async def mark_unhealthy(self, connection):
        """Marca una conexión como unhealthy"""
        for conn_info in self.connections:
            if conn_info['connection'] == connection:
                conn_info['healthy'] = False
                self.logger.warning("Conexión marcada como unhealthy")
                break
    
    async def _recover_connection(self, index: int):
        """Intenta recuperar una conexión"""
        try:
            new_conn = await self.create_connection()
            self.connections[index] = {
                'connection': new_conn,
                'healthy': True,
                'last_used': datetime.now()
            }
            self.logger.info(f"Conexión {index} recuperada")
        except Exception as e:
            self.logger.error(f"Error recuperando conexión {index}: {e}")
            raise
```

---

### Logging Estructurado

```python
# infrastructure/resilience/structured_logging.py
"""
Logging estructurado para trazabilidad completa.
Cada log incluye contexto suficiente para debug.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import traceback

# Context variables para tracing
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')
operation_id: ContextVar[str] = ContextVar('operation_id', default='')

class StructuredLogger:
    """Logger que emite logs en formato JSON estructurado"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
    
    def _build_log(
        self,
        level: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Construye entrada de log estructurada"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'logger': self.name,
            'message': message,
            'correlation_id': correlation_id.get(),
            'operation_id': operation_id.get(),
        }
        
        # Añadir campos extra
        log_entry.update(kwargs)
        
        return log_entry
    
    def info(self, message: str, **kwargs):
        log = self._build_log('INFO', message, **kwargs)
        self.logger.info(json.dumps(log))
    
    def warning(self, message: str, **kwargs):
        log = self._build_log('WARNING', message, **kwargs)
        self.logger.warning(json.dumps(log))
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        if exception:
            kwargs['exception'] = str(exception)
            kwargs['traceback'] = traceback.format_exc()
        log = self._build_log('ERROR', message, **kwargs)
        self.logger.error(json.dumps(log))
    
    def critical(self, message: str, exception: Exception = None, **kwargs):
        if exception:
            kwargs['exception'] = str(exception)
            kwargs['traceback'] = traceback.format_exc()
        log = self._build_log('CRITICAL', message, **kwargs)
        self.logger.critical(json.dumps(log))
    
    # Logs específicos de trading
    def order_sent(self, operation_id: str, order_type: str, **kwargs):
        self.info(
            "Order sent to broker",
            event='order_sent',
            operation_id=operation_id,
            order_type=order_type,
            **kwargs
        )
    
    def order_confirmed(self, operation_id: str, broker_ticket: str, **kwargs):
        self.info(
            "Order confirmed by broker",
            event='order_confirmed',
            operation_id=operation_id,
            broker_ticket=broker_ticket,
            **kwargs
        )
    
    def order_failed(self, operation_id: str, error: str, **kwargs):
        self.error(
            "Order failed",
            event='order_failed',
            operation_id=operation_id,
            error=error,
            **kwargs
        )
    
    def reconciliation_completed(self, discrepancies: int, **kwargs):
        level = 'warning' if discrepancies > 0 else 'info'
        getattr(self, level)(
            "Reconciliation completed",
            event='reconciliation_completed',
            discrepancies=discrepancies,
            **kwargs
        )
    
    def state_checkpoint(self, checkpoint_id: str, **kwargs):
        self.info(
            "State checkpoint created",
            event='state_checkpoint',
            checkpoint_id=checkpoint_id,
            **kwargs
        )


# Configuración de logging
def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """Configura logging estructurado"""
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    # Handler para archivo (si se especifica)
    handlers = [console_handler]
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handlers.append(file_handler)
    
    # Configurar root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        handlers=handlers,
        format='%(message)s'  # JSON ya formateado
    )


# Decorador para tracing
def traced(operation_name: str):
    """Decorador que añade tracing a una función"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import uuid
            op_id = str(uuid.uuid4())[:8]
            
            token = operation_id.set(op_id)
            logger = StructuredLogger(func.__module__)
            
            try:
                logger.info(f"Starting {operation_name}", operation=operation_name)
                result = await func(*args, **kwargs)
                logger.info(f"Completed {operation_name}", operation=operation_name)
                return result
            except Exception as e:
                logger.error(f"Failed {operation_name}", exception=e, operation=operation_name)
                raise
            finally:
                operation_id.reset(token)
        
        return wrapper
    return decorator
```

---

### Tabla de Estado de Conexiones (SQL)

```sql
-- Añadir a Supabase para monitoreo de conexiones

CREATE TABLE connection_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component VARCHAR(50) NOT NULL,  -- 'broker_mt5', 'broker_darwinex', 'database'
    status VARCHAR(20) NOT NULL,     -- 'connected', 'disconnected', 'reconnecting'
    last_connected TIMESTAMPTZ,
    last_disconnected TIMESTAMPTZ,
    reconnect_attempts INTEGER DEFAULT 0,
    last_error TEXT,
    metadata JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(component)
);

CREATE TABLE error_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    severity VARCHAR(20) NOT NULL,
    component VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    
    -- Contexto
    correlation_id VARCHAR(50),
    operation_id VARCHAR(50),
    cycle_id UUID REFERENCES cycles(id),
    operation_ref_id UUID REFERENCES operations(id),
    
    -- Metadata
    metadata JSONB,
    
    -- Resolución
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX idx_error_log_unresolved ON error_log(created_at DESC) 
    WHERE resolved = FALSE;
CREATE INDEX idx_error_log_severity ON error_log(severity, created_at DESC);

-- Vista de errores recientes sin resolver
CREATE VIEW v_unresolved_errors AS
SELECT 
    id,
    created_at,
    severity,
    component,
    error_type,
    error_message,
    correlation_id,
    operation_id
FROM error_log
WHERE resolved = FALSE
ORDER BY 
    CASE severity 
        WHEN 'critical' THEN 1 
        WHEN 'error' THEN 2 
        WHEN 'warning' THEN 3 
        ELSE 4 
    END,
    created_at DESC;
```

---

### Resumen de Robustez

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEFENSA EN PROFUNDIDAD                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Capa 1: Prevención                                             │
│  ├── Rate Limiter (evita sobrecarga)                           │
│  ├── Spread Controller (evita malas entradas)                  │
│  └── Market Filters (evita momentos peligrosos)                │
│                                                                 │
│  Capa 2: Detección                                              │
│  ├── Health Monitor (detecta problemas)                        │
│  ├── Watchdog (monitoreo continuo)                             │
│  └── Logging estructurado (trazabilidad)                       │
│                                                                 │
│  Capa 3: Contención                                             │
│  ├── Circuit Breaker (aísla fallos)                            │
│  ├── Timeout Manager (evita bloqueos)                          │
│  └── Connection Pool (distribuye carga)                        │
│                                                                 │
│  Capa 4: Recuperación                                           │
│  ├── Retry Manager (reintentos inteligentes)                   │
│  ├── Auto Reconnect (reconexión automática)                    │
│  └── Reconciliation (sincroniza estado)                        │
│                                                                 │
│  Capa 5: Consistencia                                           │
│  ├── Idempotency Manager (evita duplicados)                    │
│  ├── Outbox Pattern (operaciones atómicas)                     │
│  ├── Checkpoints (estado recuperable)                          │
│  └── Dead Letter Queue (nada se pierde)                        │
│                                                                 │
│  Capa 6: Apagado Seguro                                         │
│  ├── Graceful Shutdown (cierre ordenado)                       │
│  └── Final Reconciliation (estado consistente)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

El backtest asume ejecución perfecta. Debemos modelar slippage realista.

```python
# backtesting/slippage_model.py
import numpy as np
from typing import Optional

class SlippageModel:
    """Modela slippage realista para backtesting"""
    
    def __init__(self, config: dict):
        self.base_slippage_pips = config.get('base_slippage', 0.3)
        self.volatility_factor = config.get('volatility_factor', 0.1)
        self.spread_factor = config.get('spread_factor', 0.5)
    
    def calculate_slippage(
        self,
        order_type: str,
        volatility: float,
        spread: float,
        is_market_order: bool = False
    ) -> float:
        """
        Calcula slippage en pips
        
        Args:
            order_type: 'BUY' o 'SELL'
            volatility: Volatilidad reciente en pips
            spread: Spread actual en pips
            is_market_order: True si es orden de mercado
        
        Returns:
            Slippage en pips (siempre desfavorable)
        """
        # Base slippage
        slippage = self.base_slippage_pips
        
        # Ajuste por volatilidad
        slippage += volatility * self.volatility_factor
        
        # Ajuste por spread (spreads altos = más slippage)
        slippage += spread * self.spread_factor
        
        # Órdenes de mercado tienen más slippage
        if is_market_order:
            slippage *= 1.5
        
        # Añadir componente aleatorio (0 a 50% adicional)
        random_component = np.random.uniform(0, 0.5)
        slippage *= (1 + random_component)
        
        return round(slippage, 2)
    
    def apply_slippage(
        self,
        intended_price: float,
        order_type: str,
        slippage_pips: float
    ) -> float:
        """
        Aplica slippage al precio
        Slippage siempre es desfavorable al trader
        """
        pip_value = 0.0001  # Para pares XXX/USD
        
        if order_type in ['BUY', 'BUY_STOP']:
            # Compramos más caro
            return intended_price + (slippage_pips * pip_value)
        else:
            # Vendemos más barato
            return intended_price - (slippage_pips * pip_value)


class RealisticBacktestEngine(BacktestEngine):
    """Backtest engine con slippage realista"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slippage_model = SlippageModel({
            'base_slippage': 0.3,
            'volatility_factor': 0.1,
            'spread_factor': 0.5
        })
        self.total_slippage_cost = 0
    
    def _execute_order(self, operation, current_price, volatility, spread):
        """Ejecuta orden con slippage realista"""
        
        slippage = self.slippage_model.calculate_slippage(
            operation.op_type.value,
            volatility,
            spread
        )
        
        actual_price = self.slippage_model.apply_slippage(
            operation.entry_price,
            operation.op_type.value,
            slippage
        )
        
        # Registrar costo de slippage
        self.total_slippage_cost += slippage
        
        # Ajustar TP también (el TP efectivo es menor)
        operation.entry_price = actual_price
        
        return operation
```

---

### 🟡 Alto: Rate Limiting y Circuit Breaker

```python
# infrastructure/services/rate_limiter.py
import asyncio
from datetime import datetime, timedelta
from collections import deque

class RateLimiter:
    """Rate limiter para APIs de broker"""
    
    def __init__(self, max_requests: int, period_seconds: int):
        self.max_requests = max_requests
        self.period = timedelta(seconds=period_seconds)
        self.requests = deque()
    
    async def acquire(self):
        """Espera hasta que se pueda hacer una request"""
        now = datetime.now()
        
        # Limpiar requests antiguas
        while self.requests and self.requests[0] < now - self.period:
            self.requests.popleft()
        
        # Si estamos en el límite, esperar
        if len(self.requests) >= self.max_requests:
            wait_time = (self.requests[0] + self.period - now).total_seconds()
            if wait_time > 0:
                print(f"⏳ Rate limit alcanzado, esperando {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)


class CircuitBreaker:
    """Circuit breaker para manejar fallos del broker"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_requests = half_open_requests
        
        self.failures = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.half_open_successes = 0
    
    async def execute(self, func, *args, **kwargs):
        """Ejecuta función con protección de circuit breaker"""
        
        if self.state == 'OPEN':
            if datetime.now() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                self.half_open_successes = 0
                print("🔄 Circuit breaker: HALF_OPEN")
            else:
                raise CircuitBreakerOpen("Circuit breaker está abierto")
        
        try:
            result = await func(*args, **kwargs)
            
            if self.state == 'HALF_OPEN':
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_requests:
                    self.state = 'CLOSED'
                    self.failures = 0
                    print("✅ Circuit breaker: CLOSED")
            
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.failures >= self.failure_threshold:
                self.state = 'OPEN'
                print(f"🔴 Circuit breaker: OPEN después de {self.failures} fallos")
            
            raise


# Uso en el adaptador del broker
class ResilientBrokerAdapter:
    """Broker adapter con rate limiting y circuit breaker"""
    
    def __init__(self, broker):
        self.broker = broker
        self.rate_limiter = RateLimiter(max_requests=10, period_seconds=1)
        self.circuit_breaker = CircuitBreaker()
    
    async def place_order(self, operation):
        await self.rate_limiter.acquire()
        return await self.circuit_breaker.execute(
            self.broker.place_order, 
            operation
        )
```

---

### 🟡 Alto: Gestión de Timezones

```python
# infrastructure/utils/timezone_handler.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

class ForexTimezoneHandler:
    """Maneja timezones para forex (24/5)"""
    
    # Sesiones de mercado en UTC
    SESSIONS = {
        'Sydney': {'open': 21, 'close': 6},    # 21:00 - 06:00 UTC
        'Tokyo': {'open': 0, 'close': 9},       # 00:00 - 09:00 UTC
        'London': {'open': 7, 'close': 16},     # 07:00 - 16:00 UTC
        'NewYork': {'open': 12, 'close': 21}    # 12:00 - 21:00 UTC
    }
    
    def __init__(self, broker_timezone: str = 'UTC'):
        self.broker_tz = ZoneInfo(broker_timezone)
        self.utc = timezone.utc
    
    def to_utc(self, dt: datetime, source_tz: str = None) -> datetime:
        """Convierte cualquier datetime a UTC"""
        if dt.tzinfo is None:
            if source_tz:
                dt = dt.replace(tzinfo=ZoneInfo(source_tz))
            else:
                dt = dt.replace(tzinfo=self.broker_tz)
        return dt.astimezone(self.utc)
    
    def to_broker_time(self, dt: datetime) -> datetime:
        """Convierte a timezone del broker"""
        return self.to_utc(dt).astimezone(self.broker_tz)
    
    def is_market_open(self, dt: datetime = None) -> bool:
        """Verifica si el mercado forex está abierto"""
        if dt is None:
            dt = datetime.now(self.utc)
        else:
            dt = self.to_utc(dt)
        
        # Forex cierra viernes 21:00 UTC, abre domingo 21:00 UTC
        weekday = dt.weekday()
        hour = dt.hour
        
        if weekday == 4 and hour >= 21:  # Viernes después de 21:00
            return False
        if weekday == 5:  # Sábado
            return False
        if weekday == 6 and hour < 21:  # Domingo antes de 21:00
            return False
        
        return True
    
    def get_active_sessions(self, dt: datetime = None) -> list:
        """Retorna sesiones activas en un momento dado"""
        if dt is None:
            dt = datetime.now(self.utc)
        else:
            dt = self.to_utc(dt)
        
        hour = dt.hour
        active = []
        
        for session, times in self.SESSIONS.items():
            if times['open'] <= times['close']:
                if times['open'] <= hour < times['close']:
                    active.append(session)
            else:  # Cruza medianoche
                if hour >= times['open'] or hour < times['close']:
                    active.append(session)
        
        return active
    
    def next_market_open(self) -> datetime:
        """Retorna próxima apertura de mercado"""
        now = datetime.now(self.utc)
        
        if self.is_market_open(now):
            return now
        
        # Buscar próximo domingo 21:00 UTC
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 21:
            days_until_sunday = 7
        
        next_open = now.replace(hour=21, minute=0, second=0, microsecond=0)
        next_open += timedelta(days=days_until_sunday)
        
        return next_open
```

---

## Plan de Desarrollo por Fases

### Visión General

```
Fase 0 ──► Fase 1 ──► Fase 2 ──► Fase 3 ──► Fase 4 ──► Fase 5 ──► Fase 6
Setup     Backtest   Backtest   Core       API &      Paper      Producción
Inicial   Básico     Completo   Trading    Monitor    Trading    
                                                                  
2 días    1 semana   2 semanas  2 semanas  1 semana   1 mes      Gradual
```

---

### FASE 0: Setup Inicial
**Duración:** 2 días  
**Objetivo:** Preparar entorno de desarrollo

#### Tareas

| #   | Tarea                             | Entregable                       | Criterio de Aceptación           |
| --- | --------------------------------- | -------------------------------- | -------------------------------- |
| 0.1 | Crear repositorio Git             | Repo con .gitignore, README      | Repo creado en GitHub/GitLab     |
| 0.2 | Configurar estructura de carpetas | Estructura Clean Architecture    | Todas las carpetas creadas       |
| 0.3 | Setup entorno Python              | pyproject.toml, requirements.txt | `pip install -e .` funciona      |
| 0.4 | Configurar pre-commit hooks       | .pre-commit-config.yaml          | black, flake8, mypy configurados |
| 0.5 | **Crear proyecto Supabase**       | Proyecto en supabase.com         | Dashboard accesible              |
| 0.6 | **Ejecutar schema SQL**           | Todas las tablas creadas         | Vistas funcionando               |
| 0.7 | **Configurar .env**               | Variables de Supabase            | Conexión funciona                |
| 0.8 | Configurar Docker                 | Dockerfile, docker-compose.yml   | `docker-compose up` funciona     |
| 0.9 | Verificar datos QuantData         | Script de verificación           | Datos accesibles, sin nulls      |

#### Setup Supabase (Detalle)

```bash
# 1. Crear cuenta en supabase.com (free tier)
# 2. Crear nuevo proyecto
# 3. Ir a SQL Editor
# 4. Ejecutar el schema completo (ver sección Base de Datos)
# 5. Copiar URL y keys de Settings > API
```

```python
# scripts/test_supabase_connection.py
from supabase import create_client
import os

def test_connection():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    client = create_client(url, key)
    
    # Test básico
    result = client.table('cycles').select('*').limit(1).execute()
    print("✅ Conexión exitosa")
    
    # Test vista
    status = client.table('v_system_status').select('*').execute()
    print(f"✅ Vista funcionando: {status.data}")
    
    # Test insert/delete
    test_data = {'external_id': 'TEST_001', 'pair': 'EURUSD', 'cycle_type': 'main', 'status': 'active'}
    client.table('cycles').insert(test_data).execute()
    client.table('cycles').delete().eq('external_id', 'TEST_001').execute()
    print("✅ CRUD funcionando")

if __name__ == "__main__":
    test_connection()
```

#### Estructura de Carpetas Final

```
fontanero/
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── fontanero/
│       ├── domain/
│       │   ├── entities/
│       │   ├── value_objects/
│       │   ├── services/
│       │   └── interfaces/
│       ├── application/
│       │   ├── use_cases/
│       │   ├── services/
│       │   └── dto/
│       ├── infrastructure/
│       │   ├── brokers/
│       │   ├── persistence/
│       │   ├── data/
│       │   └── services/
│       ├── api/
│       │   ├── routers/
│       │   └── websockets/
│       └── backtesting/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── backtest/
├── data/
│   └── .gitkeep
├── config/
├── scripts/
├── docs/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

#### Checklist de Completación
- [ ] Repo creado y clonado
- [ ] Estructura de carpetas
- [ ] Dependencias instalables
- [ ] Pre-commit funcionando
- [ ] Docker funcionando
- [ ] Datos verificados

---

### FASE 1: Backtesting Básico
**Duración:** 1 semana  
**Objetivo:** Motor de backtest funcional con un par

#### Tareas

| #   | Tarea                              | Entregable           | Criterio de Aceptación    |
| --- | ---------------------------------- | -------------------- | ------------------------- |
| 1.1 | Implementar entidades básicas      | Operation, Cycle     | Tests unitarios pasan     |
| 1.2 | Implementar GeneradorIDs           | Clase completa       | IDs jerárquicos correctos |
| 1.3 | Implementar QuantDataLoader        | Cargador de datos    | Carga EURUSD sin errores  |
| 1.4 | Implementar ConvertidorTicks       | OHLC → Ticks         | Genera ticks realistas    |
| 1.5 | Implementar BacktestEngine básico  | Motor sin slippage   | Procesa 1 día de datos    |
| 1.6 | Implementar lógica ciclo principal | Apertura, TP, cierre | Ciclo simple funciona     |
| 1.7 | Tests unitarios fase 1             | Suite de tests       | Coverage > 80%            |

#### Código a Implementar

```python
# Día 1-2: Entidades
src/fontanero/domain/entities/operation.py
src/fontanero/domain/entities/cycle.py
src/fontanero/domain/services/id_generator.py
tests/unit/domain/test_entities.py

# Día 3-4: Data Loading
src/fontanero/infrastructure/data/quantdata_loader.py
src/fontanero/backtesting/tick_converter.py
tests/unit/infrastructure/test_data_loader.py

# Día 5-7: Backtest Engine
src/fontanero/backtesting/engine.py
src/fontanero/backtesting/basic_strategy.py
tests/unit/backtesting/test_engine.py
```

#### Test de Validación Fase 1

```python
def test_fase_1_completa():
    """Test que valida completación de Fase 1"""
    # Cargar datos
    loader = QuantDataLoader("/data/quantdata")
    df = loader.load_pair("EURUSD", "M1", start="2023-01-01", end="2023-01-31")
    assert len(df) > 0
    
    # Convertir a ticks
    ticks = ConvertidorTicks.crear_ticks_detallados(df)
    assert len(ticks) > len(df)
    
    # Ejecutar backtest básico
    engine = BacktestEngine()
    result = engine.run(ticks, config={'tp_principal': 10})
    
    # Verificar resultados mínimos
    assert result['cycles_completed'] > 0
    assert 'balance_final' in result
```

---

### FASE 2: Backtesting Completo
**Duración:** 2 semanas  
**Objetivo:** Backtest con todas las features y métricas

#### Tareas

| #    | Tarea                          | Entregable            | Criterio de Aceptación              |
| ---- | ------------------------------ | --------------------- | ----------------------------------- |
| 2.1  | Implementar sistema cobertura  | Lógica de hedge       | Coberturas se activan correctamente |
| 2.2  | Implementar sistema recovery   | Lógica completa       | Recovery funciona con FIFO          |
| 2.3  | Implementar ContabilidadCiclo  | Clase completa        | Balance correcto                    |
| 2.4  | Implementar detección de gaps  | Gap handler           | Gaps >50 pips detectados            |
| 2.5  | Implementar SlippageModel      | Modelo realista       | Slippage aplicado                   |
| 2.6  | Implementar MetricsCalculator  | Todas las métricas    | KPIs calculados                     |
| 2.7  | Implementar filtros de mercado | MarketFilters         | Filtros funcionando                 |
| 2.8  | Backtest EURUSD 5 años         | Reporte completo      | Métricas validadas                  |
| 2.9  | Backtest GBPUSD 5 años         | Reporte completo      | Métricas validadas                  |
| 2.10 | Análisis de resultados         | Documento de análisis | Conclusiones documentadas           |
| 2.11 | Tests integración backtest     | Suite de tests        | Coverage > 85%                      |

#### Semana 1: Core del Backtest

```python
# Días 1-3: Coberturas y Recovery
src/fontanero/domain/services/hedge_manager.py
src/fontanero/domain/services/recovery_manager.py
src/fontanero/domain/services/cycle_accounting.py

# Días 4-5: Gaps y Slippage
src/fontanero/backtesting/gap_handler.py
src/fontanero/backtesting/slippage_model.py

# Días 6-7: Métricas
src/fontanero/backtesting/metrics_calculator.py
src/fontanero/backtesting/report_generator.py
```

#### Semana 2: Validación y Análisis

```python
# Días 1-2: Filtros
src/fontanero/application/services/market_filters.py
src/fontanero/application/services/spread_controller.py

# Días 3-5: Backtests extensivos
scripts/run_backtest_eurusd.py
scripts/run_backtest_gbpusd.py
scripts/analyze_results.py

# Días 6-7: Documentación y tests
docs/backtest_results.md
tests/integration/test_full_backtest.py
```

#### Criterios de Éxito Fase 2

```python
FASE_2_SUCCESS_CRITERIA = {
    'eurusd': {
        'min_profit_factor': 1.3,
        'max_drawdown_pips': 500,
        'max_recovery_ratio': 2.0
    },
    'gbpusd': {
        'min_profit_factor': 1.2,
        'max_drawdown_pips': 600,
        'max_recovery_ratio': 2.5
    }
}
```

---

### FASE 3: Core de Trading
**Duración:** 2 semanas  
**Objetivo:** Sistema de trading funcional sin API

#### Tareas

| #    | Tarea                               | Entregable               | Criterio de Aceptación  |
| ---- | ----------------------------------- | ------------------------ | ----------------------- |
| 3.1  | Implementar BrokerInterface         | Interface abstracta      | Contrato definido       |
| 3.2  | Implementar MT5Adapter              | Adaptador completo       | Conecta y opera en demo |
| 3.3  | Implementar DarwinexAdapter         | Adaptador completo       | Conecta y opera en demo |
| 3.4  | Implementar SupabaseRepository      | Repositorio completo     | CRUD funciona           |
| 3.5  | Implementar StateManager            | Checkpoints              | Recovery funciona       |
| 3.6  | Implementar ReconciliationService   | Reconciliación           | Detecta discrepancias   |
| 3.7  | Implementar IdempotentOrderExecutor | Órdenes idempotentes     | Sin duplicados          |
| 3.8  | Implementar RateLimiter             | Rate limiting            | No excede límites       |
| 3.9  | Implementar CircuitBreaker          | Circuit breaker          | Protege de fallos       |
| 3.10 | Implementar TimezoneHandler         | Manejo TZ                | Sesiones correctas      |
| 3.11 | Implementar Use Cases               | OpenCycle, CloseRecovery | Lógica de negocio       |
| 3.12 | Tests integración trading           | Suite completa           | Coverage > 85%          |

#### Semana 1: Infraestructura

```python
# Días 1-2: Interfaces y Adaptadores
src/fontanero/domain/interfaces/broker.py
src/fontanero/infrastructure/brokers/mt5_adapter.py
src/fontanero/infrastructure/brokers/darwinex_adapter.py

# Días 3-4: Persistencia
src/fontanero/infrastructure/persistence/supabase_repo.py
src/fontanero/infrastructure/persistence/models.py
src/fontanero/infrastructure/services/state_manager.py

# Días 5-7: Servicios críticos
src/fontanero/infrastructure/services/reconciliation.py
src/fontanero/infrastructure/services/order_executor.py
src/fontanero/infrastructure/services/rate_limiter.py
```

#### Semana 2: Lógica de Negocio

```python
# Días 1-3: Use Cases
src/fontanero/application/use_cases/open_main_cycle.py
src/fontanero/application/use_cases/activate_hedge.py
src/fontanero/application/use_cases/open_recovery.py
src/fontanero/application/use_cases/close_cycle.py
src/fontanero/application/use_cases/process_recovery_tp.py

# Días 4-5: Servicios de aplicación
src/fontanero/application/services/cycle_orchestrator.py
src/fontanero/application/services/reserve_fund_manager.py

# Días 6-7: Tests
tests/integration/test_trading_flow.py
tests/integration/test_broker_adapters.py
```

#### Test de Validación Fase 3

```python
async def test_fase_3_flow_completo():
    """Test que valida flujo completo de trading"""
    # Setup
    broker = MT5Adapter(demo_credentials)
    repo = PostgresRepository(test_db)
    orchestrator = CycleOrchestrator(broker, repo)
    
    # Abrir ciclo
    cycle = await orchestrator.open_main_cycle("EURUSD")
    assert cycle.status == CycleStatus.ACTIVE
    
    # Simular TP de una operación
    await orchestrator.process_tp_hit(cycle.main_operations[0])
    
    # Verificar cobertura activada
    cycle = repo.get_cycle(cycle.id)
    assert len(cycle.hedge_operations) > 0
    
    # Verificar reconciliación
    recon = await reconciliation.full_reconciliation()
    assert len(recon['discrepancies']) == 0
```

---

### FASE 4: API y Monitoreo
**Duración:** 1 semana  
**Objetivo:** API REST y dashboard de monitoreo

#### Tareas

| #   | Tarea                          | Entregable              | Criterio de Aceptación  |
| --- | ------------------------------ | ----------------------- | ----------------------- |
| 4.1 | Implementar FastAPI app        | main.py con routers     | Swagger accesible       |
| 4.2 | Implementar endpoints ciclos   | CRUD ciclos             | Postman tests pasan     |
| 4.3 | Implementar endpoints métricas | Métricas en tiempo real | Dashboard funciona      |
| 4.4 | Implementar WebSocket          | Updates en tiempo real  | WS conecta              |
| 4.5 | Implementar alertas            | Sistema de alertas      | Email/Telegram funciona |
| 4.6 | Implementar health checks      | /health endpoint        | Monitoreo OK            |
| 4.7 | Implementar logging            | Logging estructurado    | Logs en JSON            |
| 4.8 | Docker compose producción      | docker-compose.prod.yml | Deploy funciona         |

```python
# Estructura API
src/fontanero/api/
├── main.py
├── routers/
│   ├── cycles.py
│   ├── operations.py
│   ├── metrics.py
│   ├── portfolio.py
│   └── health.py
├── websockets/
│   └── realtime.py
├── middleware/
│   ├── error_handler.py
│   └── logging.py
└── schemas/
    ├── cycle.py
    └── operation.py
```

#### Endpoints Principales

```yaml
# Ciclos
POST   /api/v1/cycles/main          # Abrir ciclo principal
GET    /api/v1/cycles               # Listar ciclos
GET    /api/v1/cycles/{id}          # Detalle ciclo
POST   /api/v1/cycles/{id}/pause    # Pausar ciclo
DELETE /api/v1/cycles/{id}          # Cerrar ciclo

# Operaciones
GET    /api/v1/operations           # Listar operaciones
GET    /api/v1/operations/{id}      # Detalle operación

# Métricas
GET    /api/v1/metrics/exposure     # Exposición actual
GET    /api/v1/metrics/daily        # Métricas diarias
GET    /api/v1/metrics/balance      # Balance histórico

# Sistema
GET    /api/v1/health               # Health check
POST   /api/v1/system/reconcile     # Forzar reconciliación
POST   /api/v1/system/emergency-stop # Parada de emergencia

# WebSocket
WS     /ws/realtime                 # Updates en tiempo real
```

---

### FASE 5: Paper Trading
**Duración:** 1 mes mínimo  
**Objetivo:** Validar sistema en condiciones reales sin riesgo

#### Semana 1-2: Setup y Estabilización

| Día  | Tarea                     | Verificación         |
| ---- | ------------------------- | -------------------- |
| 1    | Deploy en servidor        | Sistema accesible    |
| 2    | Conectar Darwinex demo    | Conexión estable     |
| 3    | Abrir primer ciclo manual | Ciclo funciona       |
| 4-7  | Monitoreo intensivo       | Sin errores críticos |
| 8-14 | Operación supervisada     | Métricas razonables  |

#### Semana 3-4: Operación Autónoma

| Métrica               | Target    | Acción si Falla         |
| --------------------- | --------- | ----------------------- |
| Uptime                | >99%      | Revisar infraestructura |
| Reconciliation errors | 0         | Revisar sincronización  |
| Profit factor         | >1.2      | Revisar parámetros      |
| Max drawdown          | <300 pips | Activar pausa           |
| Recovery ratio        | <2.0      | Ajustar TPs             |

#### Checklist Fin de Paper Trading

```markdown
## Validación Paper Trading - Checklist

### Sistema
- [ ] Uptime >99% durante 4 semanas
- [ ] 0 reconciliation errors
- [ ] 0 órdenes duplicadas
- [ ] Recovery de estado exitoso (probado)
- [ ] Circuit breaker probado

### Trading
- [ ] Profit factor >1.2
- [ ] Max drawdown <300 pips
- [ ] Recovery ratio <2.0
- [ ] >100 ciclos completados
- [ ] Gaps manejados correctamente

### Operacional
- [ ] Alertas funcionando
- [ ] Logs completos y útiles
- [ ] Dashboard operativo
- [ ] Documentación actualizada
- [ ] Runbook de emergencias

### Aprobación
- [ ] Revisión de métricas
- [ ] Decisión GO/NO-GO documentada
- [ ] Capital asignado definido
- [ ] Plan de rollback definido
```

---

### FASE 6: Producción
**Duración:** Gradual e indefinida  
**Objetivo:** Operación real con capital

#### Mes 1: Lote Mínimo (0.01)

```python
PRODUCTION_CONFIG_MONTH_1 = {
    'lot_size': 0.01,
    'max_cycles_per_pair': 3,
    'pairs': ['EURUSD'],  # Solo un par
    'reserve_fund_percent': 30,  # Mayor reserva inicial
    'emergency_stop_drawdown': 200  # Más conservador
}
```

**Revisión semanal obligatoria:**
- Comparar métricas reales vs paper trading
- Verificar slippage real vs modelo
- Ajustar parámetros si necesario

#### Mes 2-3: Escalado Gradual

```python
# Si mes 1 exitoso
PRODUCTION_CONFIG_MONTH_2 = {
    'lot_size': 0.01,
    'max_cycles_per_pair': 5,
    'pairs': ['EURUSD', 'GBPUSD'],  # Añadir segundo par
    'reserve_fund_percent': 25,
    'emergency_stop_drawdown': 300
}

# Si mes 2 exitoso
PRODUCTION_CONFIG_MONTH_3 = {
    'lot_size': 0.02,  # Aumentar lote
    'max_cycles_per_pair': 5,
    'pairs': ['EURUSD', 'GBPUSD'],
    'reserve_fund_percent': 20,
    'emergency_stop_drawdown': 400
}
```

#### Criterios de Escalado

| Condición                    | Acción                |
| ---------------------------- | --------------------- |
| Profit factor >1.3 por 1 mes | Puede escalar         |
| Profit factor 1.0-1.3        | Mantener nivel actual |
| Profit factor <1.0           | Reducir exposición    |
| Max drawdown >500 pips       | Pausa y revisión      |
| Recovery ratio >3.0          | Revisar parámetros    |

---

## Glosario de Términos

| Término                         | Definición                                                                 |
| ------------------------------- | -------------------------------------------------------------------------- |
| **Ciclo Principal**             | Conjunto de operaciones BUY/SELL simultáneas + recovery asociados          |
| **Recovery**                    | Operaciones de recuperación que buscan +80 pips para compensar pérdidas    |
| **Cobertura/Hedge**             | Operación que neutraliza la pérdida de otra, encapsulándola                |
| **Neutralización**              | Estado donde una pérdida queda "congelada" por una cobertura               |
| **FIFO**                        | First In, First Out - Sistema que cierra primero los recovery más antiguos |
| **Drawdown**                    | Pérdida desde el máximo histórico de balance                               |
| **TP (Take Profit)**            | Nivel de precio objetivo donde se cierra con beneficio                     |
| **Pips**                        | Unidad mínima de precio en forex (0.0001 para EURUSD, 0.01 para JPY)       |
| **Lotaje**                      | Tamaño de posición (0.01 = micro lote = ~1€/pip en EURUSD)                 |
| **Spread**                      | Diferencia entre precio de compra (ask) y venta (bid)                      |
| **Swap**                        | Costo/ingreso diario por mantener posición overnight                       |
| **ECN Broker**                  | Broker con acceso directo al mercado, spreads variables, comisiones fijas  |
| **Gap**                         | Salto de precio entre cierre y apertura de mercado                         |
| **Portfolio descorrelacionado** | Conjunto de pares que no se mueven juntos                                  |

---

## Fórmulas Matemáticas Clave

### Cálculo de Balance Neto
```
Balance_Neto = Σ(Beneficio_Pips × Valor_Pip - Comisiones - Swaps)
```

### Cálculo de Drawdown
```
Drawdown(t) = Balance(t) - Max(Balance[0...t])
Drawdown_Pct = Drawdown(t) / Max(Balance[0...t]) × 100
```

### Ratio de Recovery
```
Recovery_Ratio = Recovery_Creados / Ciclos_Completados
Target: < 1.5
```

### ROI Anualizado
```
ROI_Anual = (Balance_Final / Balance_Inicial)^(365/Días) - 1
```

### Costo de Recovery
```
Costo_Primer_Recovery = 20 pips (incluye principales)
Costo_Recovery_Adicional = 40 pips cada uno
```

### Break-even Recovery
```
Para cubrir N recovery neutralizados:
Recovery_Exitosos_Necesarios = ceil(N × 40 / 80) = ceil(N / 2)
Tasa_Éxito_Mínima = 33.3%
```

---

**Documento creado:** Enero 2025  
**Versión:** 2.0  
**Sistema:** El Fontanero de Wall Street  

---

*Gota a gota, se llena el cubo.*

---

## KPIs y Métricas de Evaluación

### Métricas de Rentabilidad

| Métrica            | Fórmula                                       | Objetivo |
| ------------------ | --------------------------------------------- | -------- |
| **Balance Final**  | Σ(pips_ganados - costos)                      | > 0      |
| **ROI Anualizado** | (balance_final / inicial)^(365/días) - 1      | > 20%    |
| **Sharpe Ratio**   | retorno_promedio / volatilidad_retornos       | > 1.5    |
| **Profit Factor**  | beneficios_totales / pérdidas_totales         | > 1.5    |
| **Expectancy**     | (win_rate × avg_win) - (loss_rate × avg_loss) | > 5 pips |

### Métricas de Riesgo

| Métrica               | Fórmula                            | Límite         |
| --------------------- | ---------------------------------- | -------------- |
| **Drawdown Máximo**   | balance - max(balance_histórico)   | < 500 pips     |
| **Drawdown Promedio** | promedio(todos_drawdowns)          | < 200 pips     |
| **Recovery Time**     | tiempo_promedio_recuperar_drawdown | < 5 días       |
| **VaR (95%)**         | pérdida_máxima_95%_confianza       | < 100 pips/día |

### Métricas Operativas

| Métrica                  | Descripción                           | Target |
| ------------------------ | ------------------------------------- | ------ |
| **Recovery Ratio**       | recovery_creados / ciclos_completados | < 1.5  |
| **Ciclos/Día**           | ciclos_completados / días_operados    | > 3    |
| **Tiempo Ciclo**         | duración_promedio_ciclo               | < 24h  |
| **Tasa Éxito Principal** | ciclos_sin_recovery / total_ciclos    | > 40%  |

### Cálculo de Métricas

```python
# backtesting/metrics_calculator.py
import numpy as np
from typing import Dict, List

class MetricsCalculator:
    
    @staticmethod
    def calculate_all(balance_history: List[float], operations: List) -> Dict:
        """Calcula todas las métricas del sistema"""
        
        returns = np.diff(balance_history) / np.abs(balance_history[:-1] + 1)
        
        return {
            # Rentabilidad
            'balance_final': balance_history[-1],
            'total_return_pct': (balance_history[-1] / balance_history[0] - 1) * 100,
            'sharpe_ratio': np.mean(returns) / (np.std(returns) + 0.0001) * np.sqrt(252),
            'profit_factor': MetricsCalculator._profit_factor(operations),
            
            # Riesgo
            'max_drawdown': MetricsCalculator._max_drawdown(balance_history),
            'avg_drawdown': MetricsCalculator._avg_drawdown(balance_history),
            'var_95': np.percentile(returns, 5) * -1,
            
            # Operativas
            'total_operations': len(operations),
            'win_rate': MetricsCalculator._win_rate(operations),
            'avg_win': MetricsCalculator._avg_win(operations),
            'avg_loss': MetricsCalculator._avg_loss(operations),
        }
    
    @staticmethod
    def _max_drawdown(balance_history: List[float]) -> float:
        """Calcula máximo drawdown en pips"""
        peak = balance_history[0]
        max_dd = 0
        
        for balance in balance_history:
            if balance > peak:
                peak = balance
            dd = peak - balance
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    @staticmethod
    def _profit_factor(operations: List) -> float:
        """Beneficios totales / Pérdidas totales"""
        gains = sum(op.profit_pips for op in operations if op.profit_pips > 0)
        losses = abs(sum(op.profit_pips for op in operations if op.profit_pips < 0))
        return gains / (losses + 0.0001)
```

---

## Troubleshooting: Solución de Problemas

### Problemas Comunes de Datos

#### "Datos con gaps extremos"
```python
# Filtrar gaps extremos antes de procesar
def filtrar_gaps_extremos(datos: pd.DataFrame, max_gap_pips: float = 500):
    """Elimina gaps que podrían causar comportamiento errático"""
    datos['precio_diff'] = datos['mid'].diff().abs() * 10000
    datos_filtrados = datos[datos['precio_diff'] <= max_gap_pips]
    
    gaps_eliminados = len(datos) - len(datos_filtrados)
    if gaps_eliminados > 0:
        print(f"⚠️ Eliminados {gaps_eliminados} registros con gaps > {max_gap_pips} pips")
    
    return datos_filtrados
```

#### "Formato de datos incorrecto"
```python
# Debug de estructura de datos
def debug_datos(datos: pd.DataFrame, num_muestras: int = 5):
    print("=== DEBUG DATOS ===")
    print(f"Columnas: {datos.columns.tolist()}")
    print(f"Tipos: {datos.dtypes}")
    print(f"Shape: {datos.shape}")
    print(f"Nulls: {datos.isnull().sum().sum()}")
    print(f"\nPrimeras {num_muestras} filas:")
    print(datos.head(num_muestras))
    print(f"\nÚltimas {num_muestras} filas:")
    print(datos.tail(num_muestras))
```

### Problemas de Rendimiento

#### "Backtesting muy lento"
```python
# Optimizaciones de rendimiento

# 1. Usar chunks para datasets grandes
def procesar_en_chunks(datos, chunk_size=10000):
    resultados = []
    for i in range(0, len(datos), chunk_size):
        chunk = datos.iloc[i:i+chunk_size]
        resultado = engine.run(chunk)
        resultados.append(resultado)
    return consolidar_resultados(resultados)

# 2. Reducir frecuencia de logging
engine.log_frequency = 1000  # Log cada 1000 ticks en lugar de cada uno

# 3. Deshabilitar gráficos durante desarrollo
engine.generate_plots = False
```

### Interpretación de Resultados

#### "Balance negativo - ¿El sistema no funciona?"

**No necesariamente.** Analiza:

1. **Duración del backtest**: Períodos cortos pueden ser engañosos
2. **Condiciones de mercado**: ¿Lateral extremo? ¿Trending fuerte?
3. **Parámetros**: Pueden necesitar optimización para ese mercado

```python
# Análisis de período problemático
def analizar_periodo_negativo(reporte):
    print("=== ANÁLISIS DE PERÍODO NEGATIVO ===")
    
    # 1. Verificar tipo de mercado
    volatilidad = reporte['metrics']['avg_daily_range']
    if volatilidad < 20:
        print("⚠️ Mercado de baja volatilidad - considerar pausa")
    
    # 2. Verificar acumulación de recovery
    recovery_ratio = reporte['recovery_created'] / max(1, reporte['cycles_completed'])
    if recovery_ratio > 2.0:
        print(f"⚠️ Recovery ratio alto: {recovery_ratio:.1f} - revisar TPs")
    
    # 3. Verificar drawdown
    if reporte['max_drawdown'] > 300:
        print(f"⚠️ Drawdown excesivo: {reporte['max_drawdown']} pips")
```

#### "Demasiados recovery por ciclo"

**Síntoma:** `recovery_ratio > 2.0`

**Causas:**
- Mercado muy lateral
- TPs demasiado pequeños
- Separación insuficiente

**Soluciones:**
```python
# Ajustar parámetros para mercados difíciles
config_mercado_lateral = {
    'tp_principal': 15,      # Aumentar de 10 a 15
    'tp_recovery': 100,      # Aumentar de 80 a 100
    'recovery_distance': 25, # Aumentar de 20 a 25
    'filtro_volatilidad_min': 20  # Aumentar umbral
}
```

### Validación de Estrategia

#### Pruebas críticas a realizar

```python
# 1. Test de crisis (2008, 2020)
def test_crisis():
    periodos_crisis = [
        ('2008-09-01', '2009-03-31', 'Crisis Financiera'),
        ('2020-02-15', '2020-04-15', 'COVID-19'),
        ('2022-01-01', '2022-06-30', 'Subida Tipos')
    ]
    
    for start, end, nombre in periodos_crisis:
        resultado = engine.run(start_date=start, end_date=end)
        print(f"{nombre}: Balance={resultado['balance']}, MaxDD={resultado['max_dd']}")

# 2. Test de condiciones de mercado
def test_condiciones():
    # Identificar períodos por tipo
    periodos_trending = identificar_trending(datos)
    periodos_lateral = identificar_lateral(datos)
    
    for tipo, periodos in [('trending', periodos_trending), ('lateral', periodos_lateral)]:
        for p in periodos[:5]:  # Primeros 5 de cada tipo
            resultado = engine.run(start_date=p['start'], end_date=p['end'])
            print(f"{tipo}: {resultado['balance']} pips")
```

---

## Disclaimer y Gestión de Riesgo

### ⚠️ IMPORTANTE: Descargo de Responsabilidad

**Este sistema es una herramienta de análisis y automatización. El trading conlleva riesgos significativos:**

- **Pérdidas de Capital**: Es posible perder todo el capital invertido
- **No Garantías**: Rendimientos pasados NO garantizan resultados futuros
- **Condiciones de Mercado**: El sistema puede no funcionar en todas las condiciones
- **Errores Técnicos**: El software puede tener bugs o fallar
- **Dependencia de Datos**: La calidad de datos afecta los resultados
- **Riesgo de Ejecución**: Slippage, requotes, desconexiones

### Gestión de Riesgo Recomendada

#### Capital
- **Máximo 2-5%** del patrimonio total en trading algorítmico
- Mantener **capital de emergencia separado**
- **Nunca** usar dinero necesario para gastos esenciales
- Considerar el capital invertido como **perdido** hasta demostrar lo contrario

#### Antes de Operar en Real
1. **Mínimo 3 meses de backtesting** con datos de diferentes condiciones
2. **Mínimo 1 mes de paper trading** en cuenta demo
3. **Comenzar con lote mínimo** (0.01) en cuenta real
4. **Escalar gradualmente** solo después de 3+ meses rentables

#### Límites de Emergencia
```python
# Implementar SIEMPRE estos límites
EMERGENCY_LIMITS = {
    'max_daily_loss_pips': 100,      # Pausa automática
    'max_weekly_loss_pips': 300,     # Revisión obligatoria
    'max_monthly_loss_pips': 500,    # Stop total del sistema
    'max_concurrent_recovery': 20,   # Pausa nuevos ciclos
    'max_exposure_percent': 30       # No abrir más operaciones
}
```

#### Plan de Contingencia
```python
def emergency_shutdown(reason: str):
    """Cierre de emergencia del sistema"""
    
    # 1. Pausar nuevas operaciones inmediatamente
    system.pause_new_cycles()
    
    # 2. Notificar al operador
    send_alert(f"🚨 EMERGENCY SHUTDOWN: {reason}")
    
    # 3. Log completo del estado
    log_system_state()
    
    # 4. NO cerrar posiciones automáticamente (podría empeorar)
    # El operador decide si cerrar manualmente
```

---

## Estado del Debate: Todas las Objeciones Resueltas

| #   | Objeción                        | Solución                                        | Estado |
| --- | ------------------------------- | ----------------------------------------------- | ------ |
| 1   | Neutralización congela pérdidas | Swaps incluidos + flujo de principales compensa | ✅      |
| 2   | Acumulación en lateral          | 40 pips separación + trailing stop opcional     | ✅      |
| 3   | Movimientos fuertes 400+ pips   | Solo activa una dirección, favorece al sistema  | ✅      |
| 4   | Pérdidas potenciales            | 2k€/par = margen 300 ops, lineal no exponencial | ✅      |
| 5   | Correlación entre pares         | Portfolio descorrelacionado, cálculo previo     | ✅      |
| 6   | Eventos alta volatilidad        | Pausar principales, mantener recovery           | ✅      |
| 7   | Spreads variables               | Broker ECN + controlador de spreads             | ✅      |
| 8   | Gaps fin de semana              | Aceptar + fondo reserva 20%                     | ✅      |

---

## Roadmap y Estado de Ejecución (Source of Truth)

### ✅ Logros Técnicos
- **[2026-01-05]** Creación de `requirements.txt` con todas las dependencias (Supabase, FastAPI, MT5, etc.).
- **[2026-01-05]** Instalación exitosa de dependencias en el entorno virtual `venv`.
- **[2026-01-05]** Limpieza del repositorio eliminando archivos redundantes en el directorio `new/`.
- **[2026-01-05]** Estandarización de la configuración usando **Pydantic v2** (eliminando uso de v1 deprecado).
- **[2026-01-05]** Migración e integración de activos avanzados desde el directorio `new/`:
    - Centralización de tipos y enums en `src/wsplumber/domain/types.py`.
    - Entidades `Cycle` y `Operation` avanzadas con lógica de negocio y contabilidad FIFO.
    - Interfaces de dominio (ports) en `src/wsplumber/domain/interfaces/ports.py`.
    - Logging seguro y sanitizado en `src/wsplumber/infrastructure/logging/safe_logger.py`.
    - Gestión de configuración con Pydantic en `src/wsplumber/config/settings.py`.
    - Implementación del `SupabaseRepository` en `src/wsplumber/infrastructure/persistence/supabase_repo.py`.
- **[2026-01-05]** Configuración del archivo `.env` con placeholders para todas las claves (Supabase, MT5, API).
- **[2026-01-05]** Creación de la estructura de directorios (`src/wsplumber/domain`, `infrastructure`, etc.) siguiendo Clean Architecture.

### 🚀 Próximos Pasos (Pendientes)
- [ ] Implementación del adaptador inicial para MetaTrader 5 (MT5Adapter).
- [ ] Implementación de los servicios de aplicación y orquestación de ciclos.
- [ ] Implementación del controlador de riesgo (RiskManager).
- [ ] Configuración del servidor API (FastAPI) y dashboard en tiempo real.

### 📝 Notas y Observaciones (Lo que falta o se ha pasado por alto)
- *Nota:* Debemos asegurar que el compilador de Cython esté configurado correctamente para la protección del core en la fase de distribución.
- *Nota:* Pendiente definir el umbral exacto de spread para el controlador de seguridad del broker.
- *Nota:* La migración del código desde `new/` incluyó corrección de namespaces (`fontanero` -> `wsplumber`) y adición de comentarios de ruta en cada archivo.


