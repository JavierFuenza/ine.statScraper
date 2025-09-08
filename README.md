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

- `--debug` o `-d`  
  Ejecuta el scraper en modo debug (navegador visible, logs detallados, timeouts extendidos).

- `--headless`  
  Fuerza el modo headless (navegador oculto), útil si quieres asegurarte de que el navegador no se muestre aunque estés en modo debug.

---

## Ejemplo de uso

- **Modo normal (headless por defecto):**
  ```bash
  python main.py
  ```

- **Modo debug (navegador visible):**
  ```bash
  python main.py --debug
  # o
  python main.py -d
  ```

---

## Notas

- Los archivos descargados y los reportes se guardan en la carpeta `data/downloads/`.
- El scraping puede demorar dependiendo de la cantidad de datasets y la velocidad de la red.
- Si tienes problemas con la instalación de Playwright, ejecuta:
  ```bash
  playwright install
  ```

---


