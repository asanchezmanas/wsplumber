# Fractal Gatekeeper: Teoría y Aplicación (Mandelbrot)

> *"Los mercados no son campanas de Gauss; son fractales, rugosos y tienen memoria."* — Benoit Mandelbrot.

## 1. El Fundamento Fractal

En el trading tradicional, se asume que los movimientos del precio son aleatorios (Movimiento Browniano). Sin embargo, Benoit Mandelbrot demostró que los mercados financieros poseen **"Memoria Estática"** y una estructura fractal. 

Esta Phase 17 implementa un **"Fractal Gatekeeper"** (Capa 4 del Sistema Inmune) para proteger al bot de los estados de mercado ineficientes.

---

## 2. Conceptos Clave

### A. El Exponente de Hurst (H)
Mide la **Persistencia** de la serie temporal. Nos dice si el precio está "queriendo ir a algún sitio" o si solo está oscilando sin sentido.

*   **H > 0.5 (Persistencia/Tendencia)**: El mercado tiene memoria de tendencia. Si ha subido, es probable que siga subiendo. 
    *   *Aplicación*: Luz verde para abrir ciclos y expandir Recoveries.
*   **H < 0.5 (Anti-persistencia/Lateralidad)**: El mercado tiende a volver sobre sus pasos (Mean Reversion). Es el "zig-zag" que activa ambos lados del bot.
    *   *Aplicación*: Veto de aperturas de nuevos ciclos.
*   **H ≈ 0.5 (Ruido Blanco)**: Caos puro. Paseo aleatorio.

### B. Análisis R/S (Rescaled Range)
Es el método robusto para medir la **Longitud Real del Rango**. A diferencia de un simple `Alto - Bajo`, el R/S analiza la desviación acumulada respecto a la media.

1.  Se calcula la media de un periodo.
2.  Se crea una serie de desviaciones acumuladas.
3.  El Rango (R) es la diferencia entre el máximo y el mínimo de esa serie acumulada.
4.  Se divide por la desviación estándar (S) para normalizarlo.

---

## 3. Sensibilidad y Ventanas Temporales (Tuning)

Uno de los riesgos de un filtro fractal es la **infra-operatividad** (congelar el bot demasiado tiempo). Para evitar esto, Phase 17 incluye:

### A. Análisis de Sensibilidad (Backtest de Ruido)
Antes de activar el filtro, ejecutaremos un script de análisis sobre los datos de 2015 para medir:
- **Duty Cycle**: ¿Qué porcentaje del tiempo el Hurst está debajo de 0.45?
- **Frecuencia de Cruce**: ¿Cuántas veces al día cambia de estado?
- **Objetivo**: Si a 4h el bot está apagado el 50% del tiempo, bajaremos la ventana a **1h o 30m**.

### B. Granularidad Adaptativa
- **Macro Filter (H4/H1)**: Define si el ecosistema general es apto para operar.
- **Micro Filter (30m)**: Define el "timing" preciso para soltar una reactivación escalonada. 

---

## 4. Aplicación en WSPlumber (Layer 4)

### Filtro 1: El Escudo Anti-Vibración (Toxic Range)
Si el **R/S Range Length** es menor a **40 pips** (configurable), el sistema asume que el mercado es una "Vibradora". 
- **Acción**: Pausa total de nuevas entradas (`SILENT_MODE`). 

### Filtro 2: Veto del Corazón del Rango
Si el precio está en el **40-60% central** de un rango consolidado:
- **Acción**: Bloqueo de apertura de nuevos `MAIN_CYCLES`.

### Filtro 3: Expansión por Paciencia Fractal
En un ciclo en recovery:
- El bot solo expande la deuda cuando el Hurst indica que el mercado está "despertando" (Rising Hurst).

---

## 5. Escenarios de Verificación (Nuevos)

| ID | Nombre | Descripción | Objetivo |
|---|---|---|---|
| **E07** | `hurst_sensitivity` | Datos reales 2015 (Q1) | Medir tiempo de bloqueo vs oportunidades perdidas |
| **E08** | `range_breakout` | Rango lateral de 50 pips | Verificar que el bot entra SOLO al salir del 60% central |
| **E09** | `vibrator_trap` | Micro-oscilaciones de 20 pips | Verificar que el bot se queda en `SILENT_MODE` total |

---
