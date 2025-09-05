"""
Configuración para el scraper de INE.Stat
"""

import os
from pathlib import Path

# Configuración base
BASE_URL = "https://stat.ine.cl/?lang=es&SubSessionId="
PROJECT_ROOT = Path(__file__).parent.parent

# Directorios
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

# Crear directorios si no existen
for dir_path in [DATA_DIR, LOGS_DIR, CONFIG_DIR]:
    dir_path.mkdir(exist_ok=True)

# Configuración del scraper
SCRAPER_CONFIG = {
    "timeout": 60000,  # 60 segundos
    "wait_for_selector": 15000,  # 15 segundos
    "download_timeout": 60000,  # 1 minuto para descargas
    "retry_attempts": 3,
    "delay_between_requests": 3,  # segundos entre requests
}

# Configuración del navegador
BROWSER_CONFIG = {
    "headless": True,  # Cambiar a False para debug - VISIBLE
    "slow_mo": 2000,   # Ralentizar acciones para evitar timeouts
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-web-security",
        "--start-maximized"  # Maximizar ventana para mejor visualización
    ]
}

# Módulos objetivo (nombres exactos del HTML)
MODULES_TO_SCRAPE = {
    "aire": {
        "name": "Módulo VBA- Estado - Aire",
        "datasets": [
            "Temperatura máxima absoluta",
            "Temperatura mínima absoluta", 
            "Temperatura media",
            "Humedad relativa media mensual",
            "Radiación global media",
            "Índice UV-B promedio",
            "Concentración de Material Particulado fino respirable (MP2,5) media mensual"
        ]
    },
    "agua": {
        "name": "Módulo VBA- Estado- Agua",
        "datasets": [
            "Caudal medio de aguas corrientes",
            "Volumen del embalse, según embalse",
            "Nivel estático de aguas subterráneas",
            "Cantidad de agua caída",
            "Temperatura superficial del mar",
            "Nivel medio del mar"
        ]
    }
}

# Logging
LOG_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    "rotation": "1 MB",
    "retention": "1 week"
}