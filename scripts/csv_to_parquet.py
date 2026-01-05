# scripts/csv_to_parquet.py
"""
Script para convertir CSVs de tick data a formato Parquet.

Parquet ofrece:
- Compresión ~10x mejor que CSV
- Lectura columnar (solo las columnas que necesitas)
- Tipos de datos nativos (timestamps, floats)
- Compatible con pandas, polars, pyarrow
"""

import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import polars as pl
except ImportError:
    print("❌ Polars no está instalado. Instalando...")
    os.system(f"{sys.executable} -m pip install polars pyarrow")
    import polars as pl


def convert_csv_to_parquet(
    input_path: str,
    output_path: str = None,
    date_column: str = None,
    datetime_format: str = None,
    compression: str = "zstd"  # zstd ofrece mejor ratio compresión/velocidad
) -> Path:
    """
    Convierte un archivo CSV de tick data a Parquet.
    
    Args:
        input_path: Ruta al archivo CSV
        output_path: Ruta de salida (por defecto: mismo nombre con .parquet)
        date_column: Nombre de la columna de fecha/hora (autodetectado si no se especifica)
        datetime_format: Formato de datetime (e.g., "%Y.%m.%d %H:%M:%S.%f")
        compression: Algoritmo de compresión (zstd, snappy, gzip, lz4)
    
    Returns:
        Path al archivo Parquet creado
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {input_path}")
    
    # Determinar ruta de salida
    if output_path is None:
        output_file = input_file.with_suffix(".parquet")
    else:
        output_file = Path(output_path)
    
    print(f"📂 Leyendo: {input_file.name}")
    print(f"   Tamaño original: {input_file.stat().st_size / (1024*1024):.2f} MB")
    
    # Leer CSV con Polars (mucho más rápido que pandas)
    # Primero leemos una muestra para detectar el esquema
    try:
        # Intentar leer con detección automática
        df = pl.read_csv(
            input_path,
            try_parse_dates=True,
            ignore_errors=True,
            infer_schema_length=10000
        )
    except Exception as e:
        print(f"⚠️ Error en lectura automática, intentando con separador ;")
        df = pl.read_csv(
            input_path,
            separator=";",
            try_parse_dates=True,
            ignore_errors=True,
            infer_schema_length=10000
        )
    
    print(f"   Filas: {len(df):,}")
    print(f"   Columnas: {df.columns}")
    
    # Intentar detectar y convertir columna de fecha
    date_columns = ["time", "datetime", "timestamp", "date", "Time", "DateTime"]
    
    for col in date_columns:
        if col in df.columns:
            try:
                # Si es string, intentar parsear
                if df[col].dtype == pl.Utf8:
                    if datetime_format:
                        df = df.with_columns(
                            pl.col(col).str.to_datetime(datetime_format).alias(col)
                        )
                    else:
                        # Intentar formatos comunes
                        formats_to_try = [
                            "%Y.%m.%d %H:%M:%S.%f",
                            "%Y-%m-%d %H:%M:%S.%f",
                            "%Y.%m.%d %H:%M:%S",
                            "%Y-%m-%d %H:%M:%S",
                            "%d/%m/%Y %H:%M:%S",
                        ]
                        for fmt in formats_to_try:
                            try:
                                df = df.with_columns(
                                    pl.col(col).str.to_datetime(fmt).alias(col)
                                )
                                print(f"   ✅ Parseado {col} con formato: {fmt}")
                                break
                            except:
                                continue
                break
            except Exception as e:
                print(f"   ⚠️ No se pudo parsear {col}: {e}")
    
    # Escribir Parquet
    print(f"💾 Escribiendo: {output_file.name}")
    df.write_parquet(output_file, compression=compression)
    
    output_size = output_file.stat().st_size / (1024*1024)
    input_size = input_file.stat().st_size / (1024*1024)
    ratio = input_size / output_size if output_size > 0 else 0
    
    print(f"   ✅ Tamaño final: {output_size:.2f} MB")
    print(f"   📉 Compresión: {ratio:.1f}x más pequeño")
    
    return output_file


def convert_directory(
    input_dir: str,
    output_dir: str = None,
    pattern: str = "*.csv",
    **kwargs
):
    """
    Convierte todos los CSVs de un directorio a Parquet.
    
    Args:
        input_dir: Directorio con archivos CSV
        output_dir: Directorio de salida (por defecto: mismo directorio)
        pattern: Patrón glob para filtrar archivos
        **kwargs: Argumentos adicionales para convert_csv_to_parquet
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else input_path
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    csv_files = list(input_path.glob(pattern))
    print(f"🔍 Encontrados {len(csv_files)} archivos CSV en {input_dir}")
    
    total_input = 0
    total_output = 0
    
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\n[{i}/{len(csv_files)}] Procesando {csv_file.name}...")
        
        output_file = output_path / csv_file.with_suffix(".parquet").name
        
        try:
            convert_csv_to_parquet(str(csv_file), str(output_file), **kwargs)
            total_input += csv_file.stat().st_size
            total_output += output_file.stat().st_size
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 RESUMEN:")
    print(f"   Archivos procesados: {len(csv_files)}")
    print(f"   Tamaño total original: {total_input / (1024*1024*1024):.2f} GB")
    print(f"   Tamaño total Parquet: {total_output / (1024*1024*1024):.2f} GB")
    if total_output > 0:
        print(f"   Ratio de compresión: {total_input / total_output:.1f}x")


def load_parquet_example():
    """Ejemplo de cómo cargar y usar los datos en Parquet."""
    print("""
# Ejemplo de uso con Polars (recomendado para grandes datasets):
import polars as pl

# Cargar archivo completo
df = pl.read_parquet("EURUSD_ticks.parquet")

# Cargar solo columnas específicas (muy eficiente)
df = pl.read_parquet("EURUSD_ticks.parquet", columns=["time", "bid", "ask"])

# Filtrar por rango de fechas al cargar
df = pl.scan_parquet("EURUSD_ticks.parquet")\\
    .filter(pl.col("time") >= "2020-01-01")\\
    .filter(pl.col("time") < "2021-01-01")\\
    .collect()

# Ejemplo de uso con Pandas:
import pandas as pd
df = pd.read_parquet("EURUSD_ticks.parquet")
""")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convertir CSVs de tick data a Parquet")
    parser.add_argument("input", help="Archivo CSV o directorio con CSVs")
    parser.add_argument("-o", "--output", help="Archivo o directorio de salida")
    parser.add_argument("-f", "--format", help="Formato de datetime (e.g., '%%Y.%%m.%%d %%H:%%M:%%S')")
    parser.add_argument("-c", "--compression", default="zstd", 
                       choices=["zstd", "snappy", "gzip", "lz4"],
                       help="Algoritmo de compresión")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        convert_csv_to_parquet(
            args.input,
            args.output,
            datetime_format=args.format,
            compression=args.compression
        )
    elif input_path.is_dir():
        convert_directory(
            args.input,
            args.output,
            datetime_format=args.format,
            compression=args.compression
        )
    else:
        print(f"❌ No se encontró: {args.input}")
        sys.exit(1)
