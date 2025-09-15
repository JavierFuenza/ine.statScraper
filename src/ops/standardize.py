# src/ops/standardize.py
# -*- coding: utf-8 -*-
"""
Ops: estandarización de nombres de archivos a identificadores PostgreSQL-safe.
- Reducción SEMÁNTICA (abreviaciones de dominio) para conservar detalle útil.
- Normalización robusta (tildes, underscores, variantes con/sin paréntesis).
- Soporte de timestamp final (_YYYYMMDD_HHMMSS) con opción para eliminarlo.
- Agrupación estable y versionado (_v2, _v3, ...) para evitar colisiones.
- Renombrado en DOS FASES para evitar "ping-pong".
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Set
import re
import unicodedata
from uuid import uuid4
import time


# -----------------------------
# Normalización a identificador
# -----------------------------

POSTGRES_RESERVED = {
    "user","table","select","where","group","order","limit","offset","insert",
    "update","delete","having","join","on","from","into","as","and","or","not",
    "by","in","is","null","true","false"
}

def _asciiize(text: str) -> str:
    """Quita tildes/diacríticos y normaliza Unicode a ASCII."""
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))

def _to_snake_ascii(s: str) -> str:
    """ASCII, minúsculas, snake_case, sin dobles '__' ni guiones finales."""
    s = _asciiize(s).lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s

def to_sql_identifier(raw: str, max_len: int = 63) -> str:
    """Convierte a identificador PostgreSQL-safe con límite 63 chars."""
    s = _to_snake_ascii(raw)
    # 2,5 -> 2_5 (por si viniera de texto)
    s = re.sub(r'(\d),(\d)', r'\1_\2', s)
    if not s:
        s = 't'
    if s[0].isdigit() or s in POSTGRES_RESERVED:
        s = f"t_{s}"
    s = re.sub(r'_+', '_', s).strip('_')
    return s[:max_len]


# --------------------------------------------
# Timestamp final y versión (_vN) en el nombre
# --------------------------------------------

# Acepta '_' o '-', con espacios residuales al final
_TS_RE  = re.compile(r'[\-_](\d{8})[\-_](\d{6})\s*$', re.UNICODE)
_VER_RE = re.compile(r'_v(\d+)$', re.IGNORECASE)

def _strip_version(stem: str) -> tuple[str, int | None]:
    """Quita sufijo _vN si existe. Devuelve (stem_sin_v, N|None)."""
    m = _VER_RE.search(stem)
    if not m:
        return stem, None
    return stem[:m.start()], int(m.group(1))

def _strip_timestamp(stem: str) -> tuple[str, str | None]:
    """Quita sufijo final timestamp (_YYYYMMDD_HHMMSS o -YYYYMMDD-HHMMSS)."""
    m = _TS_RE.search(stem)
    if not m:
        return stem, None
    ts = f"{m.group(1)}_{m.group(2)}"
    return stem[:m.start()], ts

def _parse_stem(stem: str) -> tuple[str, str | None, int | None]:
    """
    Separa base, ts y ver del *stem* (sin extensión):
      - base: sin _vN ni timestamp final
      - ts:   'YYYYMMDD_HHMMSS' si existía al final
      - ver:  entero si terminaba en _vN
    """
    s, ver = _strip_version(stem)
    base, ts = _strip_timestamp(s)
    return base, ts, ver

def _ts_to_int(ts: str | None) -> int:
    """YYYYMMDD_HHMMSS -> entero comparable; None -> 0."""
    if not ts:
        return 0
    return int(ts.replace('_', ''))


# --------------------------------------------
# Reducción semántica (reglas de dominio)
# --------------------------------------------

# Todas las regex se aplican sobre texto ASCII/lower con separadores normalizados a ESPACIO.
# Para robustez, se aceptan variantes con o sin paréntesis en contaminantes.
_SEMANTIC_RULES: List[tuple[re.Pattern, str]] = [
    # 0) Encabezado poco informativo
    (re.compile(r'^\s*concentracion\s+de\s+'), ''),

    # 1) Contaminantes
    (re.compile(r'\bozono\s*(?:\((?:o3)\)|\s+o3)?\b'), 'o3'),
    (re.compile(r'dioxido\s+de\s+azufre\s*(?:\((?:so2)\)|\s+so2)?\b'), 'so2'),
    (re.compile(r'dioxido\s+de\s+nitrogeno\s*(?:\((?:no2)\)|\s+no2)?\b'), 'no2'),
    (re.compile(r'oxidos\s+de\s+nitrogeno\s*(?:\((?:nox)\)|\s+nox)?\b'), 'nox'),
    (re.compile(r'monoxido\s+de\s+carbono\s*(?:\((?:co)\)|\s+co)?\b'), 'co'),
    (re.compile(r'monoxido\s+de\s+nitrogeno\s*(?:\((?:no)\)|\s+no)?\b'), 'no'),
    # MP2,5 / MP25 (con/sin paréntesis, con coma o punto, con/sin espacio)
    (re.compile(
        r'material\s+particulado(?:\s+fino)?\s+respirable\s*'
        r'(?:\(\s*mp\s*2[,\.]?\s*5\s*\)|mp\s*2[,\.]?\s*5|mp\s*25|mp25)\b'
    ), 'mp25'),

    # MP10 (con/sin paréntesis, con/sin espacio)
    (re.compile(
        r'material\s+particulado\s+respirable\s*'
        r'(?:\(\s*mp\s*10\s*\)|mp\s*10|mp10)\b'
    ), 'mp10'),

    # (opcional, redundante con las dos anteriores, pero no estorba)
    (re.compile(r'material\s+particulado\s+fino\s+respirable\s*\(mp\s*2[,\.]?\s*5\)'), 'mp25'),


    # 2) Estadísticos / periodos
    (re.compile(r'\bmensua\b'), 'mensual'),
    (re.compile(r'\b(?:al|a\s+el)?\s*percentil\s*(\d+)\b'), r'perc\1'),
    (re.compile(r'\bmedia\s+mensual\b'), 'med_mens'),
    (re.compile(r'\bpromedio\b'), 'prom'),
    (re.compile(r'\bmedia\b'), 'med'),
    (re.compile(r'\bmensual\b'), 'mens'),
    (re.compile(r'\banual\b'), 'anual'),
    (re.compile(r'\bmaxima\s+horaria\s+anual\b'), 'max_hor_anual'),
    (re.compile(r'\bminima\s+horaria\s+anual\b'), 'min_hor_anual'),
    (re.compile(r'\bmaxima\s+horaria\b'), 'max_hor'),
    (re.compile(r'\bminima\s+horaria\b'), 'min_hor'),
    (re.compile(r'\bmaxima\b'), 'max'),
    (re.compile(r'\bminima\b'), 'min'),

    # 3) Variables comunes
    (re.compile(r'\btemperatura\b'), 'temp'),
    (re.compile(r'\bhumedad\s+relativa\b'), 'humedad_rel'),
    (re.compile(r'\bradiacion\s+global\b'), 'rad_global'),
    (re.compile(r'\bindice\s+uv[-_ ]?b\b'), 'uvb'),
    (re.compile(r'\bnumero\s+de\s+\b'), 'num_'),
    (re.compile(r'\bevaporacion\s+real\b'), 'evaporacion_real'),

    # 4) Alcances “según …” → “por_*”
    (re.compile(r'\bsegun\s+cuenca(?:\s+hidrografica)?\b'), 'por_cuenca'),
    (re.compile(r'\bsegun\s+estacion\b'), 'por_estacion'),
    (re.compile(r'\bsegun\s+embalse\b'), 'por_embalse'),

    # 5) Hidrología (ajustables)
    (re.compile(r'\bcantidad\s+de\s+agua\s+ca[ií]da\b'), 'cantidad_de_agua_caida'),
    (re.compile(r'\baltura\s+de\s+nieve\s+equivalente\s+en\s+agua\b'), 'altura_nieve_equivalente_en_agua'),

]

# --------------------------------------------
# Normalizaciones específicas post-reglas
# --------------------------------------------

# Colapsa duplicaciones de prefijo del contaminante: co_co_* -> co_*
# Cubre variantes con o sin '_' intermedio: so2so2_*, noxnox_*, etc.
_DUP_PREFIX_RE = re.compile(r'^(co|no2|o3|nox|no|so2|mp10|mp25)(?:_?\1)+(?:_)?', re.IGNORECASE)

def _collapse_dup_prefix(s: str) -> str:
    if not s:
        return s
    return _DUP_PREFIX_RE.sub(r'\1_', s)


def semantic_shorten(raw: str) -> str:
    """
    Aplica reducción semántica robusta, manteniendo detalle útil.
    - Convierte '_' y separadores a espacio para que las regex coincidan.
    - Inserta alcance 'por_*' si estaba el “según …”.
    - Devuelve una cadena en snake_case informativa y compacta.
    """
    if not raw:
        return ''

    # Base ASCII y a espacios
    s = _asciiize(raw).lower().strip()
    s = re.sub(r'[_\s]+', ' ', s).strip()

    # Señales de alcance por si las reglas no lo dejan explícito
    had_cuenca = bool(re.search(r'\bcuenca\b', s) and re.search(r'hidrograf', s))
    had_estac  = bool(re.search(r'\bestacion\b', s))
    had_embal  = bool(re.search(r'\bembalse\b', s))

    # Normaliza MP 2.5 → MP2,5 para capturar regla
    s = re.sub(r'\(mp\s*2\.5\)', '(mp2,5)', s)

    # Aplica reglas
    for pat, repl in _SEMANTIC_RULES:
        s = pat.sub(repl, s)

    # Limpieza de espacios
    s = re.sub(r'\s+', ' ', s).strip()

    # Si el alcance estaba y aún no quedó, agrégalo
    if had_cuenca and 'por_cuenca' not in s:
        s = f"{s} por_cuenca"
    if had_estac and 'por_estacion' not in s:
        s = f"{s} por_estacion"
    if had_embal and 'por_embalse' not in s:
        s = f"{s} por_embalse"

    # A snake_case final
    out = _to_snake_ascii(s) or _to_snake_ascii(raw)

    # Colapsa duplicaciones de prefijo del contaminante (co_co, o3o3, noxnox, so2so2, nono, mp10mp10, mp25mp25)
    out = _collapse_dup_prefix(out)

    return out


# --------------------------------------------
# Planificación de destinos (sin tocar disco)
# --------------------------------------------

def _plan_targets(paths: List[Path], drop_timestamp: bool) -> Dict[Path, Path]:
    """
    Calcula destinos {src -> dst}:
      - Reduce semánticamente y pasa a SQL-safe.
      - Si drop_timestamp=True: agrupa por base SIN timestamp.
        El más reciente (por timestamp si hay; si no, por mtime) = base.csv;
        Resto: base_v2.csv, base_v3.csv, ...
      - Si drop_timestamp=False: conserva el timestamp en la clave y en el nombre.
    """
    # 1) Registros enriquecidos
    recs = []
    for p in paths:
        stem = p.stem
        base_raw, ts, ver = _parse_stem(stem)
        base_sem = semantic_shorten(base_raw)
        base_sql = to_sql_identifier(base_sem)
        try:
            mtime = p.stat().st_mtime
        except Exception:
            mtime = time.time()
        recs.append({
            "path": p,
            "base_raw": base_raw,
            "base_sem": base_sem,
            "base_sql": base_sql,
            "ts": ts,
            "ver": ver,
            "ts_int": _ts_to_int(ts),
            "mtime": mtime,
        })

    # 2) Agrupa
    groups: Dict[str, List[dict]] = {}
    for r in recs:
        if drop_timestamp:
            gkey = r["base_sql"]                       # sin timestamp
        else:
            gkey = r["base_sql"] + (f"_{r['ts']}" if r["ts"] else "")  # con timestamp si existe
        groups.setdefault(gkey, []).append(r)

    # 3) Dentro de cada grupo: ordena más reciente primero
    plan: Dict[Path, Path] = {}
    for gkey, items in groups.items():
        items.sort(key=lambda r: (-r["ts_int"], -r["mtime"], r["path"].name.lower()))
        # Base del grupo para el nombre final
        base = gkey
        for idx, r in enumerate(items, start=1):
            stem_final = base if idx == 1 else f"{base}_v{idx}"
            if drop_timestamp:
                # Cinturón y tirantes: si se coló un TS, lo quitamos del stem final
                stem_final, _ = _strip_timestamp(stem_final)
            dst = r["path"].with_name(f"{stem_final}.csv")
            plan[r["path"]] = dst

    # 4) Resolver colisiones globales entre grupos
    used: Set[Path] = set()
    for src, dst in list(plan.items()):
        if dst not in used:
            used.add(dst)
            continue
        # colisión: versiona determinísticamente
        base = dst.stem
        m = _VER_RE.search(base)
        base_wo_v = base[:m.start()] if m else base
        n = 2
        while True:
            alt = dst.with_name(f"{base_wo_v}_v{n}.csv")
            if alt not in used:
                plan[src] = alt
                used.add(alt)
                break
            n += 1

    return plan


# --------------------------------------------
# Renombrado en dos fases (seguro)
# --------------------------------------------

def standardize_directory_names(
    target_dir: Path,
    drop_timestamp: bool = False,
    dry_run: bool = False
) -> List[Tuple[Path, Path]]:
    """
    Estandariza nombres de todos los .csv de target_dir:
      - Reducción semántica + SQL-safe.
      - Si drop_timestamp=True: elimina timestamps y agrupa por base.
      - Resuelve colisiones con versionado estable (_v2, _v3, ...).
      - Renombra en dos fases para evitar ciclos.
    Retorna lista [(src, dst)] de cambios.
    """
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    csv_paths = sorted(target_dir.glob("*.csv"), key=lambda p: p.name.lower())
    if not csv_paths:
        return []

    plan = _plan_targets(csv_paths, drop_timestamp=drop_timestamp)

    # Filtra solo los que cambian
    changes = [(src, dst) for src, dst in plan.items() if src.name != dst.name]
    if not changes:
        return []

    if dry_run:
        return changes

    # Fase 1: mover a temporales únicos
    temp_map: Dict[Path, Path] = {}
    for src, _ in changes:
        tmp = src.with_name(f".__tmp__{uuid4().hex}__.csv")
        src.rename(tmp)
        temp_map[src] = tmp

    # Fase 2: temporales -> destino final
    for src, dst in changes:
        tmp = temp_map[src]
        if dst.exists():
            base = dst.stem
            m = _VER_RE.search(base)
            base_wo_v = base[:m.start()] if m else base
            n = 2
            while True:
                alt = dst.with_name(f"{base_wo_v}_v{n}.csv")
                if not alt.exists():
                    dst = alt
                    break
                n += 1
        tmp.rename(dst)

    return changes
