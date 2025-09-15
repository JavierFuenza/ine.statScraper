# -*- coding: utf-8 -*-
"""
Ops: conteo de archivos y reporte de consola.
"""

from pathlib import Path
from typing import Dict


def count_files_in_directory(target: Path) -> int:
    """Cuenta todos los archivos (no directorios) de forma recursiva en 'target'."""
    if not target.exists() or not target.is_dir():
        return -1
    return sum(1 for p in target.rglob('*') if p.is_file())


def print_count_report(target: Path, total: int,
                       expected: Dict[str, int] | None = None) -> None:
    """Imprime reporte del conteo de archivos (con esperados si se proveen)."""
    print("=" * 60)
    print("📂 Contador de archivos")
    print("=" * 60)
    print(f"📁 Carpeta objetivo : {target}")
    if total >= 0:
        print(f"🔢 Total de archivos: {total}")
    else:
        print("⚠️  La carpeta no existe o no es un directorio.")
    print("-" * 60)

    # Desglose por extensión y conteo de CSV
    ext_map: Dict[str, int] = {}
    csv_count = 0
    if total >= 0:
        for p in target.rglob('*'):
            if p.is_file():
                ext = p.suffix.lower() or "(sin extensión)"
                ext_map[ext] = ext_map.get(ext, 0) + 1
        if ext_map:
            print("📑 Por extensión:")
            for ext, cnt in sorted(ext_map.items(), key=lambda x: (-x[1], x[0])):
                print(f"  - {ext}: {cnt}")
        csv_count = ext_map.get(".csv", 0)

    # Bloque de esperados según listas
    if expected is not None:
        print("-" * 60)
        print("📦 Esperados (listas):")
        print(f"  - Aire : {expected.get('aire', 0)}")
        print(f"  - Agua : {expected.get('agua', 0)}")
        print(f"  - Total: {expected.get('total', 0)}")
        if total >= 0:
            print(f"📊 Progreso CSV: {csv_count}/{expected.get('total', 0)}")
    print("=" * 60)
