
# scripts/test_ingestion.py
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from wsplumber.infrastructure.brokers.mt5_broker import MT5Broker
from wsplumber.infrastructure.persistence.supabase_repo import SupabaseRepository
from wsplumber.application.services.history_service import HistoryService
from wsplumber.domain.types import CurrencyPair

async def main():
    # 1. Cargar configuración
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    mt5_login = int(os.getenv("MT5_LOGIN", "0"))
    mt5_password = os.getenv("MT5_PASSWORD")
    mt5_server = os.getenv("MT5_SERVER")
    mt5_path = os.getenv("MT5_PATH")

    print(f"🚀 Iniciando prueba de ingesta en: {url}")

    # 2. Inicializar componentes
    repo = SupabaseRepository(url, key)
    broker = MT5Broker()
    
    # Conectar al broker
    print("🔗 Conectando a MetaTrader 5...")
    connect_res = await broker.connect(
        login=mt5_login,
        password=mt5_password,
        server=mt5_server,
        path=mt5_path
    )
    
    if not connect_res.success:
        print(f"❌ Error conectando a MT5: {connect_res.error}")
        return

    history_service = HistoryService(broker, repo)

    try:
        # 3. Probar ingesta de OHLC (Velas M1)
        pair = CurrencyPair("EURUSD")
        print(f"📥 Ingestando 100 velas M1 para {pair}...")
        
        ohlc_res = await history_service.ingest_ohlc(
            pair=pair,
            timeframe="M1",
            count=100
        )
        
        if ohlc_res.success:
            print(f"✅ Éxito: Se han ingestado {ohlc_res.value} velas.")
        else:
            print(f"❌ Fallo en OHLC: {ohlc_res.error}")

        # 4. Probar ingesta de Ticks
        print(f"📥 Ingestando 50 ticks para {pair}...")
        ticks_res = await history_service.ingest_ticks(
            pair=pair,
            count=50
        )
        
        if ticks_res.success:
            print(f"✅ Éxito: Se han ingestado {ticks_res.value} ticks.")
        else:
            print(f"❌ Fallo en Ticks: {ticks_res.error}")

    finally:
        await broker.disconnect()
        print("🔌 Desconectado del broker.")

if __name__ == "__main__":
    asyncio.run(main())
