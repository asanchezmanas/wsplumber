# scripts/run_segmented_backtest.py
"""
Ejecuta backtests segmentados de 3 meses para validar estabilidad
y evitar el problema del freeze en backtests largos.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from wsplumber.core.backtest.backtest_engine import BacktestEngine

# Configuración de segmentos (aproximado por número de ticks)
# 4.2M ticks / 11 años = ~380k ticks/año = ~95k ticks/trimestre
TICKS_PER_SEGMENT = 100_000  # ~3 meses de datos
TOTAL_SEGMENTS = 5  # Primeros 5 trimestres (~15 meses)

async def run_segment(segment_num: int, start_tick: int, end_tick: int):
    """Ejecuta un segmento del backtest."""
    print(f"\n{'='*60}")
    print(f"📊 SEGMENTO {segment_num}: Ticks {start_tick:,} - {end_tick:,}")
    print(f"{'='*60}")
    
    engine = BacktestEngine(initial_balance=10000.0)
    audit_file = f"docs/segment_{segment_num}_audit.md"
    
    try:
        # Usamos max_bars para limitar, pero empezamos desde el principio
        # TODO: Para segmentos posteriores, necesitaríamos skip inicial
        await engine.run(
            csv_path='2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv',
            pair='EURUSD',
            audit_file=audit_file,
            max_bars=end_tick
        )
        return True
    except Exception as e:
        print(f"❌ Error en segmento {segment_num}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 BACKTEST SEGMENTADO - WSPlumber")
    print(f"Segmentos: {TOTAL_SEGMENTS} x {TICKS_PER_SEGMENT:,} ticks")
    print(f"Hora inicio: {datetime.now().strftime('%H:%M:%S')}")
    
    results = []
    
    # Por ahora, solo corremos el primer segmento para validar
    # Los segmentos posteriores requerirían modificar el loader para skip
    segment_num = 1
    start_tick = 0
    end_tick = TICKS_PER_SEGMENT
    
    success = await run_segment(segment_num, start_tick, end_tick)
    results.append((segment_num, success))
    
    # Resumen
    print(f"\n{'='*60}")
    print("📋 RESUMEN DE SEGMENTOS")
    print(f"{'='*60}")
    for seg, ok in results:
        status = "✅ OK" if ok else "❌ FAIL"
        print(f"   Segmento {seg}: {status}")
    
    print(f"\nHora fin: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())
