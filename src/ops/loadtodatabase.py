# src/ops/loadtodatabase.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, List
import re

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.ops.standardize import to_sql_identifier
from config.settings import DATABASE_URL  # <- desde .env vía settings.py


def _normalize_columns(cols: List[str]) -> List[str]:
    seen: Dict[str, int] = {}
    out: List[str] = []
    for c in cols:
        base = to_sql_identifier(c or "col")
        if base not in seen:
            seen[base] = 1
            out.append(base)
        else:
            seen[base] += 1
            out.append(f"{base}_{seen[base]}")
    return out


def _infer_types(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    # Numéricos
    for col in df2.columns:
        if pd.api.types.is_object_dtype(df2[col]):
            conv = pd.to_numeric(df2[col], errors="coerce", downcast="integer")
            if conv.notna().sum() > 0:
                df2[col] = conv
    # Fechas por nombre
    date_like = [c for c in df2.columns if re.search(r"(fecha|date|time|datetime|anio|ano|year|mes|month)", c)]
    for col in date_like:
        if pd.api.types.is_object_dtype(df2[col]):
            dt = pd.to_datetime(df2[col], errors="coerce", infer_datetime_format=True)
            if dt.notna().sum() > 0:
                df2[col] = dt
    return df2


def _resolve_table_name(csv_path: Path, table_name: Optional[str]) -> str:
    return to_sql_identifier(table_name) if table_name else to_sql_identifier(csv_path.stem)


def _ensure_schema(engine: Engine, schema: str) -> None:
    if not schema:
        return
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


def load_csv_to_postgres(
    csv_path: Path | str,
    conn_url: Optional[str] = None,
    schema: str = "public",
    table_name: Optional[str] = None,
    if_exists: str = "append",
    chunksize: int = 10_000,
    sep: str = ",",
    encoding: str = "utf-8-sig",
) -> int:
    """
    Carga un CSV a PostgreSQL. Devuelve filas insertadas (aprox).
    Si conn_url es None, usa DATABASE_URL desde settings.py (.env).
    """
    csv_path = Path(csv_path).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {csv_path}")

    url = (conn_url or DATABASE_URL or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL no definida. Configura tu .env o pasa conn_url explícitamente."
        )

    df = pd.read_csv(
        csv_path,
        sep=sep,
        encoding=encoding,
        low_memory=False,
        dtype_backend="numpy_nullable" if hasattr(pd, "options") else None,
    )

    df.columns = _normalize_columns(list(df.columns))
    df = _infer_types(df)

    table = _resolve_table_name(csv_path, table_name)
    engine = create_engine(url, pool_pre_ping=True)
    _ensure_schema(engine, schema)

    df.to_sql(
        name=table,
        con=engine,
        schema=schema,
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=chunksize,
    )
    return int(len(df))


def load_directory_to_postgres(
    target_dir: Path | str,
    conn_url: Optional[str] = None,
    schema: str = "public",
    if_exists: str = "append",
    recursive: bool = True,
    sep: str = ",",
    encoding: str = "utf-8-sig",
) -> List[tuple[Path, int]]:
    """
    Carga todos los .csv de target_dir (recursivo por defecto).
    Retorna lista de tuplas [(ruta_csv, filas_insertadas)].
    """
    url = (conn_url or DATABASE_URL or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL no definida. Configura tu .env o pasa conn_url explícitamente.")

    target = Path(target_dir).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise NotADirectoryError(f"Carpeta no válida: {target}")

    pattern = "**/*.csv" if recursive else "*.csv"
    paths = sorted(target.glob(pattern), key=lambda p: p.name.lower())

    results: List[tuple[Path, int]] = []
    for p in paths:
        rows = load_csv_to_postgres(
            csv_path=p,
            conn_url=url,
            schema=schema,
            table_name=None,    # usa stem normalizado como nombre de tabla
            if_exists=if_exists,
            sep=sep,
            encoding=encoding,
        )
        results.append((p, rows))
    return results
