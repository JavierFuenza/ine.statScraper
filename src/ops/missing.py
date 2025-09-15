# -*- coding: utf-8 -*-
"""
Ops: verificación de faltantes vs listas maestras y detección de archivos extra.
Genera 'missingfiles.txt' en la carpeta analizada.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

from src.utils.expectedfiles import get_expected_datasets, safe_name, _norm


def scan_downloaded_filenames(downloads_root: Path) -> List[str]:
    """Recolecta nombres de todos los CSV bajo downloads_root (recursivo)."""
    if not downloads_root.exists() or not downloads_root.is_dir():
        return []
    return [p.name for p in downloads_root.rglob("*.csv")]


def matches_any_expected(filename_norm: str, expected: List[str]) -> bool:
    """True si filename_norm coincide con algún dataset esperado (crudo/safe, exacto/prefijo)."""
    for ds in expected:
        raw_base = ds
        safe_base = safe_name(ds)
        if (
            filename_norm == _norm(f"{raw_base}.csv")
            or filename_norm == _norm(f"{safe_base}.csv")
            or filename_norm.startswith(_norm(f"{raw_base}_"))
            or filename_norm.startswith(_norm(f"{safe_base}_"))
        ):
            return True
    return False


def compute_extras(expected_all: List[str], present_filenames: List[str]) -> List[str]:
    """Devuelve la lista de archivos CSV presentes que NO corresponden a ningún esperado."""
    present_norm = [_norm(name) for name in present_filenames]
    extras: List[str] = []
    for orig_name, norm_name in zip(present_filenames, present_norm):
        if not matches_any_expected(norm_name, expected_all):
            extras.append(orig_name)
    return extras


def compute_missing(expected: List[str], present_filenames: List[str]) -> List[str]:
    """
    Un dataset se considera 'presente' si existe al menos uno de estos patrones en los archivos:
      - exacto crudo:  "{dataset}.csv"
      - exacto safe:   "{safe_name(dataset)}.csv"
      - prefijo crudo: "{dataset}_..."
      - prefijo safe:  "{safe_name(dataset)}_..."
    Comparación normalizada y case-insensitive.
    """
    present_norm = [_norm(name) for name in present_filenames]
    missing: List[str] = []

    for ds in expected:
        raw_base = ds
        safe_base = safe_name(ds)

        candidates_exact = {_norm(f"{raw_base}.csv"), _norm(f"{safe_base}.csv")}
        candidates_prefix = {_norm(f"{raw_base}_"), _norm(f"{safe_base}_")}

        found = any(n in candidates_exact for n in present_norm) or \
                any(any(n.startswith(pref) for n in present_norm) for pref in candidates_prefix)

        if not found:
            missing.append(ds)

    return missing


def write_missing_report(
    target_dir: Path,
    missing_by_module: Dict[str, List[str]],
    extras: List[str],
) -> Path:
    """Crea missingfiles.txt con faltantes por módulo y sección de archivos extra."""
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / "missingfiles.txt"
    lines: List[str] = []
    total_missing = sum(len(v) for v in missing_by_module.values())
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(f"REPORTE DE ARCHIVOS FALTANTES - generado {stamp}")
    lines.append(f"Carpeta analizada: {target_dir}")
    lines.append("=" * 72)
    for module, items in missing_by_module.items():
        lines.append(f"[{module}]  Faltantes: {len(items)}")
        if items:
            lines.extend(f" - {name}" for name in items)
        else:
            lines.append(" - (sin faltantes)")
        lines.append("")
    lines.append("-" * 72)
    lines.append(f"TOTAL FALTANTES: {total_missing}")
    lines.append("=" * 72)
    lines.append("")
    lines.append("ARCHIVOS CSV EXTRA (no esperados)")
    lines.append(f"Total extras: {len(extras)}")
    if extras:
        lines.extend(f" - {x}" for x in sorted(extras))
    else:
        lines.append(" - (sin extras)")
    lines.append("=" * 72)

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def handle_missingfiles(target_dir: Path, scope: str = "all") -> int:
    """Lógica principal del flag --missingfiles."""
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"⚠️  La carpeta objetivo no existe o no es un directorio: {target_dir}")
        return 3

    present = scan_downloaded_filenames(target_dir)

    modules: List[Tuple[str, List[str]]] = []
    expected_all: List[str] = []
    if scope in ("all", "aire"):
        aire = get_expected_datasets("aire")
        modules.append(("Módulo VBA - Estado - Aire", aire))
        expected_all.extend(aire)
    if scope in ("all", "agua"):
        agua = get_expected_datasets("agua")
        modules.append(("Módulo VBA - Estado - Agua", agua))
        expected_all.extend(agua)

    missing_by_module: Dict[str, List[str]] = {
        module_name: compute_missing(expected_list, present)
        for module_name, expected_list in modules
    }

    extras = compute_extras(expected_all, present)

    # Consola
    total_missing = sum(len(v) for v in missing_by_module.values())
    print("=" * 72)
    print("🔎 Verificación de faltantes")
    print(f"📁 Carpeta: {target_dir}")
    print("=" * 72)
    for module, items in missing_by_module.items():
        print(f"\n{module}: faltantes = {len(items)}")
        for i, ds in enumerate(items, 1):
            print(f"  {i:02d}. {ds}")
    print("\n" + "-" * 72)
    print(f"TOTAL FALTANTES: {total_missing}")
    print(f"CSV EXTRAS (no esperados): {len(extras)}")
    if extras:
        for x in sorted(extras):
            print(f"  - {x}")
    print("=" * 72)

    # Archivo
    out_path = write_missing_report(target_dir, missing_by_module, extras)
    print(f"\n📝 Archivo generado: {out_path}")

    # Exit code 0 si está perfecto; 2 si hay faltantes o extras
    return 0 if total_missing == 0 and not extras else 2
