# scripts/partition_csv_by_year.py
"""
Particiona un CSV grande de datos históricos en archivos por año.

Convierte un CSV de 3GB+ en archivos manejables:
- EURUSD_2014.parquet
- EURUSD_2015.parquet
- EURUSD_2016.parquet
- ...

Esto permite:
1. Tests más rápidos con años específicos
2. Backtests paralelos por año
3. Análisis de períodos concretos (COVID 2020, etc)
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


def partition_by_year(
    input_path: str,
    output_dir: str = None,
    date_column: str = None,
    output_format: str = "parquet",  # parquet o csv
    convert_to_tick: bool = True  # Convertir OHLC a formato tick (timestamp,bid,ask)
) -> list[Path]:
    """
    Particiona un CSV por año.
    
    Args:
        input_path: Ruta al CSV grande
        output_dir: Directorio de salida (por defecto: data/partitions/)
        date_column: Nombre de columna de fecha (autodetecta)
        output_format: 'parquet' (recomendado) o 'csv'
        convert_to_tick: Si True, convierte OHLC a formato tick (timestamp,bid,ask)
    
    Returns:
        Lista de archivos creados
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"No se encontró: {input_path}")
    
    # Directorio de salida
    if output_dir is None:
        output_dir = input_file.parent / "data" / "partitions"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Leyendo: {input_file.name}")
    print(f"   Tamaño: {input_file.stat().st_size / (1024*1024):.1f} MB")
    
    # Leer CSV
    df = pl.read_csv(input_path, infer_schema_length=10000)
    print(f"   Filas totales: {len(df):,}")
    print(f"   Columnas: {df.columns}")
    
    # Detectar columna de fecha
    first_col = df.columns[0]
    print(f"   Primera columna (fecha): {first_col}")
    
    # Detectar si es formato OHLC sin headers (fecha como nombre de columna tipo "2014.12.01")
    is_ohlc_no_header = first_col[0:4].isdigit() and "." in first_col[:10]
    
    if is_ohlc_no_header and convert_to_tick:
        print(f"\n🔄 Detectado OHLC sin headers - Convirtiendo a formato tick...")
        # Columnas OHLC: fecha, hora, open, high, low, close, volume
        # Crear columnas con nombres correctos
        col_names = df.columns
        df = df.rename({
            col_names[0]: "date_str",
            col_names[1]: "time_str", 
            col_names[2]: "open",
            col_names[3]: "high",
            col_names[4]: "low",
            col_names[5]: "close",
            col_names[6]: "volume" if len(col_names) > 6 else "vol"
        })
        
        # Extraer año de date_str (formato YYYY.MM.DD) ANTES de crear timestamp
        df = df.with_columns(
            pl.col("date_str").str.slice(0, 4).cast(pl.Int32).alias("_year")
        )
        
        # Filtrar filas donde el año no es válido (header row o datos corruptos)
        df = df.filter(pl.col("_year") > 1990)
        
        # Crear timestamp combinando fecha y hora (formato: 2014.12.01 02:00)
        df = df.with_columns([
            (pl.col("date_str") + " " + pl.col("time_str")).alias("timestamp"),
            # Usar close como bid (aproximación para datos M1)
            pl.col("close").cast(pl.Float64).alias("bid"),
            # Ask = bid + spread (1 pip = 0.0001)
            (pl.col("close").cast(pl.Float64) + 0.0001).alias("ask")
        ])
        
        # Seleccionar solo columnas necesarias para el broker
        df = df.select(["timestamp", "bid", "ask", "_year"])
        print(f"   Convertido a formato tick: {df.columns}")
    else:
        # Otros formatos - extraer año de la primera columna
        df = df.with_columns(
            pl.col(first_col).str.slice(0, 4).cast(pl.Int32).alias("_year")
        )
    
    # Ver años disponibles
    years = sorted(df["_year"].unique().to_list())
    print(f"\n📅 Años encontrados: {years}")
    print(f"   Rango: {min(years)} - {max(years)} ({len(years)} años)")
    
    # Particionar
    created_files = []
    base_name = input_file.stem.split("_")[0]  # e.g., "2026.1.5EURUSD" -> "2026.1.5EURUSD"
    
    # Limpiar nombre base
    if "EURUSD" in base_name.upper():
        base_name = "EURUSD"
    elif "GBPUSD" in base_name.upper():
        base_name = "GBPUSD"
    elif "USDJPY" in base_name.upper():
        base_name = "USDJPY"
    
    for year in years:
        year_df = df.filter(pl.col("_year") == year).drop("_year")
        
        if output_format == "parquet":
            out_file = output_path / f"{base_name}_{year}.parquet"
            year_df.write_parquet(out_file, compression="zstd")
        else:
            out_file = output_path / f"{base_name}_{year}.csv"
            year_df.write_csv(out_file)
        
        size_mb = out_file.stat().st_size / (1024*1024)
        print(f"   ✅ {year}: {len(year_df):,} filas -> {out_file.name} ({size_mb:.1f} MB)")
        created_files.append(out_file)
    
    # Resumen
    total_size = sum(f.stat().st_size for f in created_files) / (1024*1024)
    original_size = input_file.stat().st_size / (1024*1024)
    
    print(f"\n{'='*50}")
    print(f"📊 RESUMEN:")
    print(f"   Archivos creados: {len(created_files)}")
    print(f"   Tamaño original: {original_size:.1f} MB")
    print(f"   Tamaño particionado: {total_size:.1f} MB")
    if output_format == "parquet":
        print(f"   Compresión: {original_size/total_size:.1f}x")
    print(f"\n   Ubicación: {output_path}")
    
    return created_files


def list_partitions(partitions_dir: str = "data/partitions") -> dict[str, list[Path]]:
    """Lista las particiones disponibles agrupadas por par."""
    path = Path(partitions_dir)
    if not path.exists():
        return {}
    
    partitions = {}
    for f in path.glob("*.parquet"):
        pair = f.stem.split("_")[0]  # EURUSD_2020.parquet -> EURUSD
        if pair not in partitions:
            partitions[pair] = []
        partitions[pair].append(f)
    
    # Ordenar por año
    for pair in partitions:
        partitions[pair].sort(key=lambda x: x.stem)
    
    return partitions


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Particionar CSV por año")
    parser.add_argument("input", help="Archivo CSV de entrada")
    parser.add_argument("-o", "--output", help="Directorio de salida")
    parser.add_argument("-f", "--format", default="parquet", 
                       choices=["parquet", "csv"],
                       help="Formato de salida")
    parser.add_argument("--list", action="store_true",
                       help="Listar particiones existentes")
    
    args = parser.parse_args()
    
    if args.list:
        partitions = list_partitions()
        if not partitions:
            print("No se encontraron particiones en data/partitions/")
        else:
            for pair, files in partitions.items():
                print(f"\n{pair}:")
                for f in files:
                    size = f.stat().st_size / (1024*1024)
                    print(f"   {f.name} ({size:.1f} MB)")
    else:
        partition_by_year(
            args.input,
            args.output,
            output_format=args.format
        )
