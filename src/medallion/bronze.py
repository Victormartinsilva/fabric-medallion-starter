"""Bronze: o dado como chegou, tudo como texto, mais metadados de ingestão.

Regra da camada: não corrige, não filtra, não converte tipos. Se o arquivo de origem
veio sujo, o Bronze guarda a sujeira, para que dê para reprocessar tudo depois.
"""
from __future__ import annotations

import pandas as pd


def to_bronze(df: pd.DataFrame, source_file: str, ingested_at: str) -> pd.DataFrame:
    """Devolve uma cópia com todas as colunas como texto e duas colunas de linhagem."""
    out = df.astype("string").copy()
    out["_source_file"] = source_file
    out["_ingested_at"] = ingested_at
    return out
