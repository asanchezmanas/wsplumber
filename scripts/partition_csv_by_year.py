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
    output_format: str = "parquet"  # parquet o csv
) -> list[Path]:
    """
    Particiona un CSV por año.
    
    Args:
        input_path: Ruta al CSV grande
        output_dir: Directorio de salida (por defecto: data/partitions/)
        date_column: Nombre de columna de fecha (autodetecta)
        output_format: 'parquet' (recomendado) o 'csv'
    
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
    
    # Extraer año de la primera columna
    # Formato esperado: "2014.12.01" o "2014.12.01,02:00"
    df = df.with_columns(
        pl.col(first_col)
        .str.slice(0, 4)
        .cast(pl.Int32)
        .alias("_year")
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
