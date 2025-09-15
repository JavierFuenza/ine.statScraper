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
# NOTA: Para habilitar el auto-descubrimiento de datasets, deja la lista "datasets" vacía: []
# El scraper automáticamente encontrará y descargará todos los datasets disponibles en el módulo

# Configuración original con datasets predefinidos (comentada):
# MODULES_TO_SCRAPE = {
#     "aire": {
#         "name": "Módulo VBA- Estado - Aire",
#         "datasets": [
#             "Temperatura máxima absoluta",
#             "Temperatura mínima absoluta", 
#             "Temperatura media",
#             "Humedad relativa media mensual",
#             "Radiación global media",
#             "Índice UV-B promedio",
#             "Concentración de Material Particulado fino respirable (MP2,5) media mensual"
#         ]
#     },
#     "agua": {
#         "name": "Módulo VBA- Estado- Agua",
#         "datasets": [
#             "Caudal medio de aguas corrientes",
#             "Volumen del embalse, según embalse",
#             "Nivel estático de aguas subterráneas",
#             "Cantidad de agua caída",
#             "Temperatura superficial del mar",
#             "Nivel medio del mar"
#         ]
#     }
# }

# Configuración para auto-descubrimiento (ACTIVA):
MODULES_TO_SCRAPE = {
    "aire": {
        "name": "Módulo VBA- Estado - Aire",
        "datasets": []  # Lista vacía = auto-descubrimiento
    },
    "agua": {
        "name": "Módulo VBA- Estado- Agua",
        "datasets": []  # Lista vacía = auto-descubrimiento
    }
}

# Logging
LOG_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    "rotation": "1 MB",
    "retention": "1 week"
}

# Direccion por defecto para las funciones de ops para countfiles, missingfiles, standarize y loadtodatabase
DEFECT_DIR_PATH = "data/downloads/20250914_230910"

# --- Carga de variables de entorno (.env) ---
from dotenv import load_dotenv
load_dotenv()  # busca .env en el cwd o padres

# URL de conexión a PostgreSQL (incluye driver: postgresql+psycopg2://...)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    # No lanzamos excepción aquí para no romper otras utilidades;
    # el módulo de carga validará y dará un mensaje claro si falta.
    pass