#!/usr/bin/env python3
"""
INE.Stat Scraper - Extractor de datos de módulos Agua y Aire
Ejecutor principal del proyecto de scraping

Uso:
    python main.py           # Modo normal (headless)
    python main.py --debug   # Modo debug (navegador visible)
    python main.py -d        # Modo debug (navegador visible)
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Añadir directorios al path para imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "src"))

from src.scraper.ine_scraper import INEScraper
from src.utils.logger import get_logger
from config.settings import SCRAPER_CONFIG, BROWSER_CONFIG

def parse_arguments():
    """Parsear argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='INE.Stat Scraper - Extractor de datos de módulos Agua y Aire',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py           # Modo normal (headless)
  python main.py --debug   # Modo debug (navegador visible)
  python main.py -d        # Modo debug (navegador visible)
        """
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Ejecutar en modo debug (navegador visible, logs detallados)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Forzar modo headless (navegador oculto)'
    )
    
    return parser.parse_args()

def get_browser_config(debug_mode: bool, force_headless: bool = False):
    """Obtener configuración del navegador según el modo"""
    base_config = BROWSER_CONFIG.copy()
    
    if force_headless:
        base_config["headless"] = True
        base_config["slow_mo"] = 500
    elif debug_mode:
        # Modo debug: navegador visible
        base_config["headless"] = False
        base_config["slow_mo"] = 2000
        if "--start-maximized" not in base_config["args"]:
            base_config["args"] = base_config["args"] + ["--start-maximized"]
    else:
        # Modo normal: mantener configuración por defecto
        base_config["headless"] = True
        base_config["slow_mo"] = 1000
    
    return base_config

def get_scraper_config(debug_mode: bool):
    """Obtener configuración del scraper según el modo"""
    base_config = SCRAPER_CONFIG.copy()
    
    if debug_mode:
        # Timeouts más largos para debug
        base_config["timeout"] = 120000  # 2 minutos
        base_config["wait_for_selector"] = 30000  # 30 segundos
        base_config["delay_between_requests"] = 5  # Más tiempo entre requests
    
    return base_config

def main():
    """Función principal que ejecuta el scraper"""
    
    # Parsear argumentos
    args = parse_arguments()
    
    # Obtener configuraciones según el modo
    browser_config = get_browser_config(args.debug, args.headless)
    scraper_config = get_scraper_config(args.debug)
    
    # Configurar logger con modo debug
    logger = get_logger(debug_mode=args.debug)
    
    # Mostrar información de inicio
    if args.debug:
        print("🚀 INE.Stat Scraper - MODO DEBUG")
        print("=" * 60)
        print("🔍 Navegador VISIBLE para debugging")
        print("⏱️  Timeouts extendidos para debug")
        print("📸 Screenshots automáticos guardados")
        print("=" * 60)
        logger.info("Iniciando scraper INE.Stat en modo DEBUG")
    else:
        print("🚀 INE.Stat Scraper - Módulos Agua y Aire")
        print("=" * 60)
        logger.info("Iniciando scraper INE.Stat en modo NORMAL")
    
    async def run_scraper():
        """Función asíncrona para ejecutar el scraper"""
        try:
            # Crear y ejecutar scraper usando context manager con configuraciones personalizadas
            scraper = INEScraper(browser_config=browser_config, scraper_config=scraper_config)
            async with scraper:
                logger.info("🌐 Scraper inicializado, comenzando extracción...")
                
                # Ejecutar scraping completo
                downloads = await scraper.scrape_all_modules()
                
                # Generar reporte
                report_path = scraper.generate_summary_report(downloads)
                
                logger.info(f"📊 Reporte generado: {report_path}")
                print(f"\n📊 Reporte completo disponible en: {report_path}")
                
                return downloads
                
        except Exception as e:
            logger.error(f"❌ Error crítico durante la ejecución: {str(e)}")
            print(f"\n❌ Error crítico: {str(e)}")
            
            if args.debug:
                print("\n🔍 MODO DEBUG - Información adicional:")
                print(f"   - Revisa los screenshots en: data/downloads/")
                print(f"   - Revisa los logs detallados en: logs/")
                print(f"   - El navegador se cerró, pero puedes volver a ejecutar")
            
            raise
    
    try:
        # Ejecutar el scraping de forma asíncrona
        downloads = asyncio.run(run_scraper())
        
        print("\n✅ ¡Scraping completado exitosamente!")
        print(f"📁 Archivos descargados en: data/downloads/")
        
        # Mostrar resumen rápido
        total_files = sum(len(files) for files in downloads.values())
        print(f"📈 Total de archivos descargados: {total_files}")
        
    except KeyboardInterrupt:
        print("\n❌ Scraper interrumpido por el usuario (Ctrl+C)")
        logger.warning("❌ Scraper interrumpido por el usuario (Ctrl+C)")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error crítico: {str(e)}")
        logger.error(f"❌ Error crítico durante la ejecución: {str(e)}")
        sys.exit(1)
    
    finally:
        print("\n" + "=" * 60)
        print("🏁 Fin de la ejecución")
        
        if args.debug:
            print("💡 Archivos de debug disponibles:")
            print("   - Screenshots: data/downloads/*/debug_*.png")
            print("   - Logs: logs/scraper_*.log")

if __name__ == "__main__":
    main()