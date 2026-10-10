"""Ponte com o Microsoft Fabric: grava e lê tabelas Delta do Lakehouse a partir de pandas.

Nada aqui importa o Spark no topo, então o módulo carrega fora do Fabric. Quem passa o
objeto `spark` é o notebook (no Fabric ele já existe como variável global).

A lógica de negócio fica em bronze/silver/gold/quality; este arquivo só faz o I/O.
"""
from __future__ import annotations

import pandas as pd

# Caminho do Lakehouse padrão montado nos notebooks do Fabric.
LAKEHOUSE_FILES = "/lakehouse/default/Files"


def sanitize_for_spark(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara um DataFrame pandas para `spark.createDataFrame`.

    Colunas de texto do pandas (dtype 'string') viram `object`, e nulos viram `None`,
    que é o que o Spark entende como NULL.
    """
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_string_dtype(out[col]) or out[col].dtype == object:
            out[col] = out[col].astype(object)
    return out.astype(object).where(out.notna(), None)


def save_delta(spark, df: pd.DataFrame, table: str, mode: str = "overwrite") -> None:
    """Grava `df` como tabela Delta gerenciada no Lakehouse."""
    sdf = spark.createDataFrame(sanitize_for_spark(df))
    sdf.write.mode(mode).format("delta").saveAsTable(table)


def read_delta(spark, table: str) -> pd.DataFrame:
    """Lê uma tabela Delta do Lakehouse como pandas."""
    return spark.read.table(table).toPandas()
