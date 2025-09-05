"""
Configuración del logger para el scraper INE.Stat
"""

import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Configuración base
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def get_logger(debug_mode: bool = False):
    """Configurar y retornar logger configurado"""
    
    # Remover configuración por defecto
    logger.remove()
    
    # Configurar nivel según modo debug
    console_level = "DEBUG" if debug_mode else "INFO"
    
    # Configurar salida a consola con colores
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level=console_level,
        colorize=True
    )
    
    # Configurar salida a archivo
    log_file = LOGS_DIR / f"scraper_{datetime.now().strftime('%Y-%m-%d')}.log"
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="1 MB",
        retention="1 week",
        encoding="utf-8"
    )
    
    return logger