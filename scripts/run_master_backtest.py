# scripts/run_master_backtest.py
import asyncio
import os
import sys
import time
from pathlib import Path

# Agregar src y root al path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from wsplumber.core.backtest.backtest_engine import BacktestEngine
from wsplumber.infrastructure.logging.safe_logger import setup_logging

async def main():
    # 1. Parámetros
    csv_file = "2026.1.5EURUSD_M1_UTCPlus02(2)-M1-No Session_ohlc.csv"
    audit_file = "docs/master_backtest_audit.md"
    
    # Asegurar que el directorio docs existe
    Path("docs").mkdir(exist_ok=True)
    
    print(f"🚀 Iniciando Backtest Maestro: {csv_file}")
    print(f"📋 Auditoría: {audit_file}")
    print(f"⏳ Tiempo estimado: ~10-14 horas para el archivo completo.")
    
    engine = BacktestEngine(initial_balance=10000.0)
    
    # 2. Ejecutar
    try:
        # Ejecutamos el archivo completo (sin max_bars)
        await engine.run(
            csv_path=csv_file,
            pair="EURUSD",
            audit_file=audit_file
        )
    except Exception as e:
        print(f"❌ Error durante el backtest: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Analizar resultados automáticamente
    print("\n📈 Generando reporte detallado...")
    try:
        # Usar el script de análisis que ya tenemos
        from subprocess import run
        run([sys.executable, "scripts/analyze_logs.py"])
    except Exception as e:
        print(f"⚠️ Error generando reporte: {e}")

if __name__ == "__main__":
    asyncio.run(main())
