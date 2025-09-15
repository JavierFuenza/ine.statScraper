#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INE.Stat Scraper - Ejecutor principal

Utilidades:
    uv run python main.py --countfiles [--dir <carpeta>]
    uv run python main.py --missingfiles [--scope all|aire|agua] [--dir <carpeta>]
    uv run python main.py --standardize [--drop-timestamp] [--dry-run] [--dir <carpeta>]
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Rutas para imports locales
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "src"))

# Scraper y utils
from src.scraper.ine_scraper import INEScraper
from src.utils.logger import get_logger
from config.settings import SCRAPER_CONFIG, BROWSER_CONFIG
from config.settings import DEFECT_DIR_PATH

# Listas esperadas
from src.utils.expectedfiles import (
    EXPECTED_DATASETS_AIRE,
    EXPECTED_DATASETS_AGUA,
    get_expected_datasets,
)

# Ops
from src.ops.countfiles import count_files_in_directory, print_count_report
from src.ops.missing import handle_missingfiles, compute_extras
from src.ops.standardize import standardize_directory_names


# ---------------------------
# Argumentos CLI
# ---------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description='INE.Stat Scraper - Extractor de datos de módulos Agua y Aire',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  uv run python main.py --countfiles --dir DEFECT_DIR_PATH
  uv run python main.py --missingfiles --scope aire --dir DEFECT_DIR_PATH
  uv run python main.py --standardize --drop-timestamp --dir DEFECT_DIR_PATH
        """
    )

    # Scraping
    parser.add_argument('--debug', '-d', action='store_true', help='Modo debug (navegador visible)')
    parser.add_argument('--headless', action='store_true', help='Forzar headless')

    # Utilidades
    parser.add_argument('--dir', default=DEFECT_DIR_PATH,
                        help='Carpeta objetivo para utilidades')
    # CountFiles
    parser.add_argument('--countfiles', action='store_true',
                        help='Cuenta archivos recursivamente en la carpeta objetivo')
    # Missing Files
    parser.add_argument('--missingfiles', action='store_true',
                        help='Genera missingfiles.txt con faltantes y extras')
    parser.add_argument('--scope', choices=['all', 'aire', 'agua'], default='all',
                        help="Filtra verificación por módulo (default: all)")
    # Standarize
    parser.add_argument('--standardize', action='store_true',
                        help='Estandariza nombres .csv (PostgreSQL-safe)')
    parser.add_argument('--drop-timestamp', action='store_true',
                        help='Estandarizar eliminando el sufijo _YYYYMMDD_HHMMSS')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simula la estandarización sin renombrar')
    
    # Load to database
    parser.add_argument('--loaddb', action='store_true',
                        help='Carga todos los .csv de la carpeta objetivo a PostgreSQL (usa DATABASE_URL del .env)')
    parser.add_argument('--schema', default='public',
                        help='Schema destino en PostgreSQL (default: public)')
    parser.add_argument('--if-exists', choices=['append', 'replace', 'fail'], default='append',
                        help='Comportamiento si la tabla existe (default: append)')
    parser.add_argument('--csv-sep', default=',',
                        help='Separador del CSV (default: ,)')
    parser.add_argument('--csv-encoding', default='utf-8-sig',
                        help='Codificación del CSV (default: utf-8-sig)')


    return parser.parse_args()


# ---------------------------
# Config scraper
# ---------------------------
def get_browser_config(debug_mode: bool, force_headless: bool = False):
    base_config = BROWSER_CONFIG.copy()
    if force_headless:
        base_config["headless"] = True
        base_config["slow_mo"] = 500
    elif debug_mode:
        base_config["headless"] = False
        base_config["slow_mo"] = 2000
        if "--start-maximized" not in base_config.get("args", []):
            base_config["args"] = base_config.get("args", []) + ["--start-maximized"]
    else:
        base_config["headless"] = True
        base_config["slow_mo"] = 1000
    return base_config


def get_scraper_config(debug_mode: bool):
    base_config = SCRAPER_CONFIG.copy()
    if debug_mode:
        base_config["timeout"] = 120000
        base_config["wait_for_selector"] = 30000
        base_config["delay_between_requests"] = 5
    return base_config


# ---------------------------
# Scraper
# ---------------------------
async def run_scraper(debug: bool, headless_flag: bool) -> int:
    logger = get_logger(debug_mode=debug)
    browser_config = get_browser_config(debug, headless_flag)
    scraper_config = get_scraper_config(debug)

    try:
        scraper = INEScraper(browser_config=browser_config, scraper_config=scraper_config)
        async with scraper:
            logger.info("🌐 Scraper inicializado, comenzando extracción...")
            downloads = await scraper.scrape_all_modules()
            report_path = scraper.generate_summary_report(downloads)
            logger.info(f"📊 Reporte generado: {report_path}")
            print(f"\n📊 Reporte completo disponible en: {report_path}")
        total_files = sum(len(files) for files in downloads.values())
        print("\n✅ ¡Scraping completado exitosamente!")
        print(f"📁 Archivos descargados en: data/downloads/")
        print(f"📈 Total de archivos descargados: {total_files}")
        return 0
    except Exception as e:
        logger.error(f"❌ Error crítico durante la ejecución: {str(e)}")
        print(f"\n❌ Error crítico: {str(e)}")
        return 1


# ---------------------------
# Main
# ---------------------------
def main():
    args = parse_arguments()

    # Contar archivos
    if args.countfiles:
        target_dir = Path(args.dir)
        total = count_files_in_directory(target_dir)

        expected_counts = {
            "aire": len(EXPECTED_DATASETS_AIRE),
            "agua": len(EXPECTED_DATASETS_AGUA),
        }
        expected_counts["total"] = expected_counts["aire"] + expected_counts["agua"]

        extras_count = 0
        if total >= 0:
            present_csvs = [p.name for p in target_dir.rglob("*.csv")]
            expected_all = get_expected_datasets("aire") + get_expected_datasets("agua")
            extras_count = len(compute_extras(expected_all, present_csvs))

        print_count_report(target_dir, total, expected_counts)
        if total >= 0:
            print(f"🟡 CSV extra (no esperados): {extras_count}")
            print("=" * 60)
        if total < 0:
            sys.exit(3)
        sys.exit(0)

    # Missing files
    if args.missingfiles:
        target_dir = Path(args.dir)
        code = handle_missingfiles(target_dir, scope=args.scope)
        sys.exit(code)

    # Estandarizar nombres
    if args.standardize:
        target_dir = Path(args.dir)
        if not target_dir.exists() or not target_dir.is_dir():
            print(f"⚠️  La carpeta objetivo no existe o no es un directorio: {target_dir}")
            sys.exit(3)
        renames = standardize_directory_names(
            target_dir, drop_timestamp=args.drop_timestamp, dry_run=args.dry_run
        )
        if not renames:
            print("✅ No hubo archivos a renombrar (o ya están estandarizados).")
            sys.exit(0)
        print("=" * 60)
        print(f"🔤 Archivos estandarizados ({'simulación' if args.dry_run else 'renombrados'}): {len(renames)}")
        for old, new in renames:
            print(f"  - {old.name}  ->  {new.name}")
        print("=" * 60)
        sys.exit(0)
    
    # Cargar a base de datos
    if args.loaddb:
        from src.ops.loadtodatabase import load_directory_to_postgres
        target_dir = Path(args.dir)
        if not target_dir.exists() or not target_dir.is_dir():
            print(f"⚠️  La carpeta objetivo no existe o no es un directorio: {target_dir}")
            sys.exit(3)
        try:
            results = load_directory_to_postgres(
                target_dir=target_dir,
                conn_url=None,                 # usa DATABASE_URL desde settings.py
                schema=args.schema,
                if_exists=args.if_exists,
                recursive=True,
                sep=args.csv_sep,
                encoding=args.csv_encoding,
            )
        except Exception as e:
            print(f"❌ Error al cargar a la base de datos: {e}")
            sys.exit(2)

        total_files = len(results)
        total_rows = sum(rows for _, rows in results)
        print("=" * 60)
        print(f"🛢️  Archivos cargados: {total_files}")
        for path, rows in results:
            print(f"  - {path.name}  ->  {rows} filas")
        print(f"✅ Total de filas insertadas: {total_rows}")
        print("=" * 60)
        sys.exit(0)


    # Scraper por defecto
    code = asyncio.run(run_scraper(args.debug, args.headless))
    sys.exit(code)


if __name__ == "__main__":
    main()
