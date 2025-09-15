# -*- coding: utf-8 -*-
"""
Utilidades y listados maestros de datasets esperados para verificación.
"""

from typing import List, Dict
import unicodedata

__all__ = [
    "EXPECTED_DATASETS_AIRE",
    "EXPECTED_DATASETS_AGUA",
    "EXPECTED_BY_SCOPE",
    "get_expected_datasets",
    "safe_name",
    "_norm",
]

# --- Listados "maestros" a verificar ---
EXPECTED_DATASETS_AIRE: List[str] = [
    "Temperatura máxima absoluta",
    "Temperatura mínima absoluta",
    "Temperatura media",
    "Temperatura máxima media",
    "Temperatura mínima media",
    "Humedad relativa media mensual",
    "Radiación global media",
    "Índice UV-B promedio",
    "Concentración de Material Particulado fino respirable (MP2,5) media mensual",
    "Concentración de Material Particulado fino respirable (MP2,5) máxima horaria anual",
    "Concentración de Material Particulado fino respirable (MP2,5) mínima horaria anual",
    "Concentración de Material Particulado fino respirable (MP2,5) al Percentil 50",
    "Concentración de Material Particulado fino respirable (MP2,5) al Percentil 90",
    "Concentración de Material Particulado fino respirable (MP2,5) al Percentil 95",
    "Concentración de Material Particulado fino respirable (MP2,5) al Percentil 98",
    "Concentración de material particulado respirable (MP10) media mensual",
    "Concentración de material particulado respirable (MP10) máxima horaria anual",
    "Concentración de material particulado respirable (MP10) mínima horaria anual",
    "Concentración de material particulado respirable (MP10) al percentil 50",
    "Concentración de material particulado respirable (MP10) al percentil 90",
    "Concentración de material particulado respirable (MP10) al percentil 95",
    "Concentración de material particulado respirable (MP10) al percentil 98",
    "Concentración de ozono (O3) media mensual",
    "Concentración de ozono (O3) máxima horaria anual",
    "Concentración de ozono (O3) mínima horaria anual",
    "Concentración de ozono (O3) al percentil 50",
    "Concentración de ozono (O3) al percentil 90",
    "Concentración de ozono (O3) al percentil 95",
    "Concentración de ozono (O3) al percentil 98",
    "Concentración de ozono (O3) al percentil 99",
    "Concentración de dióxido de azufre (SO2) media mensual",
    "Concentración de dióxido de azufre (SO2) máxima horaria anual",
    "Concentración de dióxido de azufre (SO2) mínima anual",
    "Concentración de dióxido de azufre (SO2) al percentil 50",
    "Concentración de dióxido de azufre (SO2) al percentil 90",
    "Concentración de dióxido de azufre (SO2) al percentil 95",
    "Concentración de dióxido de azufre (SO2) al percentil 99",
    "Concentración de dióxido de nitrógeno (NO2) media mensual",
    "Concentración de dióxido de nitrógeno (NO2) máxima horaria anual",
    "Concentración de dióxido de nitrógeno (NO2) mínima horaria anual",
    "Concentración de dióxido de nitrógeno (NO2) al percentil 50",
    "Concentración de dióxido de nitrógeno (NO2) al percentil 90",
    "Concentración de Dióxido de Nitrógeno (NO2) al percentil 98",
    "Concentración de dióxido de nitrógeno (NO2) al percentil 99",
    "Concentración de monóxido de carbono (CO) media mensual",
    "Concentración de monóxido de carbono (CO) máxima horaria anual",
    "Concentración de monóxido de carbono (CO) mínima horaria anual",
    "Concentración de monóxido de carbono (CO) al percentil 50",
    "Concentración de monóxido de carbono (CO) al percentil 90",
    "Concentración de monóxido de carbono (CO) al percentil 95",
    "Concentración de monóxido de carbono (CO) al percentil 98",
    "Concentración de monóxido de carbono (CO) al percentil 99",
    "Concentración de monóxido de nitrógeno (NO) media mensua",
    "Concentración de monóxido de nitrógeno (NO) máxima horaria anual",
    "Concentración de monóxido de nitrógeno (NO) mínima horaria anual",
    "Concentración de monóxido de nitrógeno (NO) al percentil 50",
    "Concentración de monóxido de nitrógeno (NO) al percentil 90",
    "Concentración de monóxido de nitrógeno (NO) al percentil 98",
    "Concentración de monóxido de nitrógeno (NO) al percentil 99",
    "Concentración de óxidos de nitrógeno (NOx) media mensual",
    "Concentración de óxidos de nitrógeno (NOx) máxima horaria anual",
    "Concentración de óxidos de nitrógeno (NOx) mínima horaria anual",
    "Concentración de óxidos de nitrógeno (NOx) al percentil 50",
    "Concentración de óxidos de nitrógeno (NOx) al percentil 90",
    "Concentración de óxidos de nitrógeno (NOx) al percentil 98",
    "Concentración de óxidos de nitrógeno (NOx) al percentil 99",
    "Concentración de dióxido de azufre (SO2) al percentil 98",
    "Concentración de dióxido de nitrógeno (NO2) al percentil 95",
    "Concentración de monóxido de nitrógeno (NO) al percentil 95",
    "Concentración de óxidos de nitrógeno (NOx) al percentil 95",
    "Número de eventos de olas de calor",
]

EXPECTED_DATASETS_AGUA: List[str] = [
    "Caudal medio de aguas corrientes",
    "Volumen del embalse, según embalse",
    "Nivel estático de aguas subterráneas",
    "Cantidad de agua caída",
    "Altura de nieve equivalente en agua",
    "Evaporación real, según estación",
    "Número de glaciares, según cuenca hidrográfica",
    "Superficie de glaciares, según cuenca hidrográfica",
    "Volumen de hielo glaciar estimado, según cuenca hidrográfica",
    "Volumen de agua de glaciares estimada, según cuenca hidrográfica",
    "Nivel medio del mar",
    "Temperatura superficial del mar",
    "Concentración de metales disueltos en la matriz acuosa",
    "Concentración de coliformes fecales en matriz acuosa",
    "Concentración de metales totales en la matriz sedimentaria",
    "Concentración de coliformes fecales en matriz biológica",
]

# Mapa de listas por "scope" usado en CLI (aire/agua)
EXPECTED_BY_SCOPE: Dict[str, List[str]] = {
    "aire": EXPECTED_DATASETS_AIRE,
    "agua": EXPECTED_DATASETS_AGUA,
}

# --------------------------
# Utilidades complementarias
# --------------------------
def get_expected_datasets(scope: str) -> List[str]:
    """
    Retorna la lista esperada para un scope ('aire', 'agua').
    Si no coincide, retorna la unión de todas.
    """
    scope = (scope or "").strip().lower()
    if scope in EXPECTED_BY_SCOPE:
        return EXPECTED_BY_SCOPE[scope]
    # Unión de todas las listas si el scope no existe
    out: List[str] = []
    for lst in EXPECTED_BY_SCOPE.values():
        out.extend(lst)
    return out

def _norm(s: str) -> str:
    # Normaliza Unicode (NFC) y pasa a minúsculas
    return unicodedata.normalize("NFC", s or "").lower()

def safe_name(dataset_name: str) -> str:
    """
    Sanitiza el nombre como prefijo de archivo (coherente con save_download):
    - Reemplaza espacios por '_'
    - Elimina paréntesis y comas
    - Mantiene tildes y otros caracteres
    """
    return (
        dataset_name
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
    )
