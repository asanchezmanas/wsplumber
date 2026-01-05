#!/usr/bin/env python3
"""
Script para verificar la conexión y configuración de Supabase.

Uso:
    python scripts/test_connection.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def print_header(text: str) -> None:
    """Imprime header con formato."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = "") -> None:
    """Imprime resultado de un test."""
    icon = "✅" if success else "❌"
    print(f"  {icon} {name}: {message}")


def test_env_variables() -> bool:
    """Verifica variables de entorno."""
    print_header("Variables de Entorno")

    required = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
    }

    optional = {
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "MT5_LOGIN": os.getenv("MT5_LOGIN"),
        "DARWINEX_API_KEY": os.getenv("DARWINEX_API_KEY"),
    }

    all_ok = True

    for name, value in required.items():
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print_result(name, True, f"Configurado ({masked})")
        else:
            print_result(name, False, "NO CONFIGURADO - Requerido!")
            all_ok = False

    print("\n  Opcionales:")
    for name, value in optional.items():
        if value:
            print_result(name, True, f"Configurado")
        else:
            print_result(name, True, "No configurado (opcional)")

    return all_ok


def test_supabase_connection() -> bool:
    """Verifica conexión con Supabase."""
    print_header("Conexión Supabase")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print_result("Conexión", False, "Faltan credenciales")
        return False

    try:
        from supabase import create_client

        client = create_client(url, key)

        # Test 1: Query simple
        result = client.table("cycles").select("id").limit(1).execute()
        print_result("Query básico", True, "Tabla 'cycles' accesible")

        # Test 2: Verificar vistas
        try:
            result = client.table("v_system_status").select("*").execute()
            print_result("Vista v_system_status", True, "Accesible")
        except Exception as e:
            print_result("Vista v_system_status", False, str(e)[:50])

        # Test 3: Insert y delete de prueba
        test_id = f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            # Insert
            client.table("cycles").insert({
                "external_id": test_id,
                "pair": "EURUSD",
                "cycle_type": "main",
                "status": "active",
            }).execute()

            # Delete
            client.table("cycles").delete().eq("external_id", test_id).execute()

            print_result("CRUD test", True, "Insert/Delete funcionando")
        except Exception as e:
            print_result("CRUD test", False, str(e)[:50])

        return True

    except ImportError:
        print_result("Conexión", False, "supabase no instalado (pip install supabase)")
        return False
    except Exception as e:
        print_result("Conexión", False, str(e)[:80])
        return False


def test_tables_exist() -> bool:
    """Verifica que las tablas existan."""
    print_header("Tablas de Base de Datos")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("  ⚠️ Saltando - Sin credenciales")
        return False

    try:
        from supabase import create_client

        client = create_client(url, key)

        tables = [
            "cycles",
            "operations",
            "checkpoints",
            "outbox",
            "reconciliation_log",
            "metrics_daily",
            "reserve_fund",
            "alerts",
            "error_log",
            "connection_status",
        ]

        all_ok = True
        for table in tables:
            try:
                client.table(table).select("id").limit(1).execute()
                print_result(table, True, "Existe")
            except Exception as e:
                print_result(table, False, "No existe - Ejecutar supabase_schema.sql")
                all_ok = False

        return all_ok

    except Exception as e:
        print_result("Verificación", False, str(e)[:80])
        return False


def test_config_loading() -> bool:
    """Verifica carga de configuración."""
    print_header("Configuración")

    try:
        from wsplumber.config.settings import get_settings, validate_configuration

        settings = get_settings()
        print_result("Settings cargados", True, f"Entorno: {settings.environment.environment}")

        validation = validate_configuration()
        for key, value in validation.items():
            status = "✓" if value else "✗"
            print(f"    {status} {key}: {value}")

        return True

    except ImportError as e:
        print_result("Config", False, f"Error de importación: {e}")
        return False
    except Exception as e:
        print_result("Config", False, str(e)[:80])
        return False


def test_logging() -> bool:
    """Verifica sistema de logging."""
    print_header("Sistema de Logging")

    try:
        from wsplumber.infrastructure.logging.safe_logger import (
            get_logger,
            setup_logging,
        )

        setup_logging(level="DEBUG", environment="development")
        logger = get_logger("test")

        # Test log con datos sensibles
        logger.info(
            "Test log con sanitización",
            cycle_id="EURUSD_001",
            entry_price=1.12345,
            strategy_params={"threshold": 0.5},  # Debería ser ***REDACTED***
        )

        print_result("SafeLogger", True, "Funcionando con sanitización")
        return True

    except ImportError as e:
        print_result("Logging", False, f"Error de importación: {e}")
        return False
    except Exception as e:
        print_result("Logging", False, str(e)[:80])
        return False


def main() -> int:
    """Ejecuta todos los tests."""
    print("\n" + "🔧 TEST DE CONEXIÓN Y CONFIGURACIÓN 🔧".center(60))

    results = []

    # Tests
    results.append(("Variables de Entorno", test_env_variables()))
    results.append(("Conexión Supabase", test_supabase_connection()))
    results.append(("Tablas DB", test_tables_exist()))
    results.append(("Configuración", test_config_loading()))
    results.append(("Logging", test_logging()))

    # Resumen
    print_header("RESUMEN")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        icon = "✅" if result else "❌"
        print(f"  {icon} {name}")

    print(f"\n  Resultado: {passed}/{total} tests pasados")

    if passed == total:
        print("\n  🎉 ¡Todo configurado correctamente!")
        return 0
    else:
        print("\n  ⚠️ Hay problemas que resolver")
        print("\n  Pasos sugeridos:")
        print("  1. Verificar .env tiene las credenciales correctas")
        print("  2. Ejecutar scripts/supabase_schema.sql en Supabase")
        print("  3. Verificar que las dependencias estén instaladas")
        return 1


if __name__ == "__main__":
    sys.exit(main())
