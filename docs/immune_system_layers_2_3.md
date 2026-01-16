# 🛡️ WSPlumber - Sistema Inmune: Layer 2 y Layer 3

Este documento detalla la arquitectura de las capas avanzadas de protección del orquestador, diseñadas para transformar los "Cisnes Negros" y Gaps de mercado en oportunidades de beneficio o, como mínimo, eventos de impacto cero.

---

## 📅 Layer 2: El Escudo de Eventos (Scheduled Guard)

Diseñado para eventos macroeconómicos conocidos (NFP, FED, Decisiones de Tipos, etc.) donde la volatilidad extrema es predecible en tiempo.

### 1. Fase Pre-Evento (T - 5 Minutos)
*   **Órdenes Pendientes:** El orquestador envía una instrucción de cancelación masiva al broker para todas las órdenes `BUY_STOP` y `SELL_STOP` (Mains y Recoveries).
*   **Órdenes Activas:** Toda posición activa que no tenga contraparte (pérdida no bloqueada) se mueve automáticamente a **Break Even (BE)** + 1 pip.
*   **Estado del Orquestador:** Entra en modo `SHIELD_ACTIVE`. No se permiten nuevas aperturas durante esta fase.

### 2. El Momento del Gap (Explosión)
*   **Protección Astuta:** Al no haber órdenes en el broker, el precio puede saltar 100 pips sin ejecutar nada a precios "sucios".
*   **Cosecha de Beneficios (Harvesting):** Si el precio salta **a favor** de una posición activa (hacia su TP), el broker ejecutará el cierre al precio del gap, capturando pips extra (Slippage Positivo).

### 3. Fase Post-Evento (T + 5 Minutos)
*   **Re-situar la Defensa:** Una vez que el spread y el precio se estabilizan, el orquestador analiza la nueva realidad del mercado.
*   **Re-activación:** Se recalculan los puntos de entrada para los Recoveries y el nuevo Main basándose en el precio post-evento, manteniendo la lógica de separación de 20/40 pips.

---

## 🌑 Layer 3: Gestión de Gaps Ciegos (Blind Gap Guard)

Diseñado para proteger el capital contra eventos no anunciados (guerras, desastres, "Flash Crashes") donde no hay preaviso de calendario.

### 1. Detección por Delta de Precio
El orquestador monitoriza el cambio de precio entre ticks consecutivos.
*   **Trigger:** Si `abs(Price_t - Price_t-1) > THRESHOLD` (ej: 15 pips).
*   **Acción Inmediata:** Modo `EMERGENCY_FREEZE`.

### 2. El Mecanismo de "Cierre en Sombra"
Como no hay tiempo para cancelar en el broker durante el salto, el orquestador aplica **Shadow Management**:
*   **Validación de Ejecución:** Si el broker reporta ejecuciones dentro del gap (ejecución ciega de stops), el orquestador calcula la **Deuda Real de Resituación**.
*   **Aislamiento de Daños:** Se prioriza el cierre de cualquier posición "huérfana" (sin hedge) al primer precio disponible, asumiendo el slippage como costo de supervivencia.

### 3. Re-anclaje de Emergencia
*   Si un gap "vuela" por encima de toda nuestra estructura de recoverys, no intentamos "perseguir" el precio.
*   **Reset Estructural:** Las deudas se consolidan en una nueva `GapDebtUnit` y se abre un ciclo de recovery totalmente nuevo en los niveles de precios actuales para empezar la recuperación con aire fresco.

---

## 🛠️ Hoja de Ruta de Implementación

1.  **Etiquetado del Pasado (Dato Histórico):**
    *   Modificar los CSV/Parquet de 2015-2024 para incluir una columna `is_event` o `event_type`.
    *   Permite testear el Escudo de Layer 2 contra momentos específicos de la historia.

2.  **Hacia las "Órdenes Virtuales":**
    *   Transicionar el sistema para que las órdenes `STOP` no existan en el broker.
    *   El Orquestador monitoriza el precio y dispara órdenes `MARKET` (o `IOK`) solo cuando el mercado ofrece condiciones de ejecución reales.

3.  **Fondo de Reserva de Gaps:**
    *   Destinar el 10% del beneficio excedente de los Gaps a favor (Slippage Positivo) a un fondo específico para cubrir los deslizamientos negativos de los Gaps Ciegos.

---

> *"No luchamos contra el gap; lo dejamos pasar y nos re-posicionamos donde el precio ha decidido estar."*
