# ine.statScraper

`ine.statScraper` es una herramienta en Python para automatizar la descarga de datasets desde el portal [INE.Stat](https://stat.ine.cl/), enfocada en los módulos de Agua y Aire.

---

## Requisitos

- **Python** 3.10 o superior
- **uv** (gestor de entornos y dependencias ultrarrápido)  
  Instala `uv` siguiendo las instrucciones oficiales:  
  https://github.com/astral-sh/uv

---

## Instalación

1. Clona este repositorio:

   ```bash
   git clone https://github.com/JavierFuenza/ine.statScraper.git
   cd ine.statScraper
   ```

2. Crea el entorno virtual e instala las dependencias usando `uv`:
   ```bash
   uv venv
   uv sync
   ```
3. Instala el navegador en Playwright:
   ```bash
   uv run playwright install chromium
   ```

---

## Uso

El comando principal es:

```bash
uv run python main.py [opciones]
```

### Opciones y flags

- `--debug` / `-d`  
  Ejecuta el scraper en modo **debug** (navegador visible, logs detallados, timeouts extendidos).

- `--headless`  
  Fuerza el modo **headless** (navegador oculto), útil si quieres asegurarte de que el navegador no se muestre aunque estés en modo debug).

### Funciones utiles para usar despues del scrapping

- `--countfiles [--dir <carpeta>]`  
  Cuenta archivos **recursivamente** en la carpeta objetivo e imprime un reporte con:

  **Parámetros**

  - `--dir` _(opcional)_: carpeta a inspeccionar.  
    Por defecto: la última carpeta de descargas (ej. `data/downloads/AAAAmmdd_HHMMSS`).

  **Ejemplos**

  ```bash
  uv run python main.py --countfiles
  uv run python main.py --countfiles --dir data/downloads/20250914_132907
  ```

- `--missingfiles [--scope all|aire|agua] [--dir <carpeta>]`

  Compara los archivos descargados con las **listas maestras** de datasets esperados y genera un informe con los archivos que faltan o sobran en `missingfiles.txt` en la misma carpeta objetivo.

  **Parámetros**

  - `--scope` _(opcional)_: `all` (por defecto), `aire` o `agua`.
  - `--dir` _(opcional)_: carpeta a inspeccionar.

  **Ejemplos**

  ```bash
  uv run python main.py --missingfiles
  uv run python main.py --missingfiles --scope aire --dir data/downloads/20250914_132907
  ```

- `--standardize [--dir <carpeta>] [--drop-timestamp] [--dry-run]`

  Estandariza los nombres de los `.csv` en la carpeta objetivo para que sean **seguros en PostgreSQL** y **legibles**:

  **Parámetros**

  - `--dir` _(opcional)_: carpeta a estandarizar.
  - `--drop-timestamp` _(opcional)_: elimina el sufijo `_AAAAmmdd_HHMMSS` del nombre base al estandarizar.
  - `--dry-run` _(opcional)_: vista previa sin aplicar cambios.

  **Ejemplos**

  ```bash
  # Vista previa (no modifica archivos)
  uv run python main.py --standardize --dry-run --dir data/downloads/20250914_132907

  # Renombrar realmente, eliminando timestamps de los nombres
  uv run python main.py --standardize --drop-timestamp --dir data/downloads/20250914_132907
  ```

- `--loadbd [--dir <carpeta>] [--schema <esquema>] [--if-exists append|replace|fail]`

  Carga los archivos `.csv` de la carpeta objetivo a una base de datos **PostgreSQL** usando la **URL de conexión** definida en el archivo `.env`

  **Parámetros**

  - `--dir` _(opcional)_: carpeta que contiene los `.csv` a cargar.  
    Por defecto: la última carpeta de descargas (ej. `data/downloads/AAAAmmdd_HHMMSS`).
  - `--schema` _(opcional)_: esquema de PostgreSQL donde insertar (default: `public`).
  - `--if-exists` _(opcional)_: comportamiento si la tabla ya existe:
    - `append` (default): agrega registros.
    - `replace`: borra y recrea la tabla.
    - `fail`: lanza error.

  **Ejemplos**

  ```bash
    # Cargar todos los CSV estandarizados de la última carpeta de descargas
    uv run python main.py --loadbd

    # Cargar archivos desde una carpeta específica en el esquema public
    uv run python main.py --loadbd --dir data/downloads/20250914_132907 --schema public

    # Reemplazar las tablas existentes con los datos nuevos
    uv run python main.py --loadbd --dir data/downloads/20250914_132907 --if-exists replace
  ```

---

## Notas

- Los archivos descargados y los reportes se guardan en la carpeta `data/downloads/`.
- El scraping puede demorar dependiendo de la cantidad de datasets y la velocidad de la red.
- Si tienes problemas con la instalación de Playwright, ejecuta:
  ```bash
  playwright install
  ```
