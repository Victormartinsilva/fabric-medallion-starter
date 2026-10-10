"""Silver: dado limpo, tipado e conformado. O que não passa vai para a quarentena.

Cada função devolve `(limpo, rejeitado)`. O rejeitado mantém as colunas originais mais
`motivo_rejeicao`, então nada some sem explicação.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import rules

META = ["_source_file", "_ingested_at"]


def _texto(s: pd.Series) -> pd.Series:
    """Tira espaços das pontas e transforma vazio em nulo."""
    s = s.astype("string").str.strip()
    return s.mask(s.fillna("") == "", pd.NA)


def _data(s: pd.Series) -> pd.Series:
    return pd.to_datetime(_texto(s), format="%Y-%m-%d", errors="coerce")


def _separar(df: pd.DataFrame, motivo: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide em (linhas sem motivo, linhas rejeitadas com `motivo_rejeicao`)."""
    ok = (motivo == "").to_numpy()
    rejeitado = df.loc[~ok].copy()
    rejeitado["motivo_rejeicao"] = motivo[~ok].to_numpy()
    return df.loc[ok], rejeitado


def _marcar_duplicados(df: pd.DataFrame, motivo: np.ndarray, chave: list[str]) -> np.ndarray:
    """Entre as linhas ainda válidas, marca repetições da chave (fica a primeira)."""
    # object: um array de texto do numpy tem largura fixa e cortaria o motivo mais longo.
    motivo = motivo.astype(object)
    validas = motivo == ""
    repetida = df[validas].duplicated(subset=chave, keep="first").to_numpy()
    posicoes = np.flatnonzero(validas)[repetida]
    motivo[posicoes] = rules.MOTIVO_DUPLICADO
    return motivo


def clean_escolas(bronze: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.DataFrame(
        {
            "escola_id": _texto(bronze["escola_id"]).str.upper(),
            "nome": _texto(bronze["nome"]),
            "municipio": _texto(bronze["municipio"]),
        }
    )
    motivo = np.where(df["escola_id"].isna(), "escola_id nulo", "")
    motivo = _marcar_duplicados(df, motivo, ["escola_id"])
    limpo, rej = _separar(df.join(bronze[META]), pd.Series(motivo, index=df.index))
    return limpo.drop(columns=META).reset_index(drop=True), rej


def clean_turmas(bronze: pd.DataFrame, escolas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.DataFrame(
        {
            "turma_id": _texto(bronze["turma_id"]).str.upper(),
            "escola_id": _texto(bronze["escola_id"]).str.upper(),
            "serie": _texto(bronze["serie"]),
            "turno": _texto(bronze["turno"]),
        }
    )
    motivo = np.select(
        [df["turma_id"].isna(), ~df["escola_id"].isin(escolas["escola_id"])],
        ["turma_id nulo", rules.MOTIVO_ESCOLA_INEXISTENTE],
        default="",
    )
    motivo = _marcar_duplicados(df, motivo, ["turma_id"])
    limpo, rej = _separar(df.join(bronze[META]), pd.Series(motivo, index=df.index))
    return limpo.drop(columns=META).reset_index(drop=True), rej


def clean_alunos(bronze: pd.DataFrame, turmas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    nome = _texto(bronze["nome"]).str.replace(r"\s+", " ", regex=True).str.title()
    df = pd.DataFrame(
        {
            "aluno_id": _texto(bronze["aluno_id"]).str.upper(),
            "turma_id": _texto(bronze["turma_id"]).str.upper(),
            "nome": nome,
            "data_nascimento": _data(bronze["data_nascimento"]),
        }
    )
    motivo = np.select(
        [df["aluno_id"].isna(), ~df["turma_id"].isin(turmas["turma_id"])],
        [rules.MOTIVO_ALUNO_NULO, rules.MOTIVO_TURMA_INEXISTENTE],
        default="",
    )
    motivo = _marcar_duplicados(df, motivo, ["aluno_id"])
    limpo, rej = _separar(df.join(bronze[META]), pd.Series(motivo, index=df.index))
    return limpo.drop(columns=META).reset_index(drop=True), rej


def clean_frequencia(
    bronze: pd.DataFrame, alunos: pd.DataFrame, today: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Regras: aluno informado e cadastrado, data válida e não futura, status P/F/J, sem repetição."""
    df = pd.DataFrame(
        {
            "aluno_id": _texto(bronze["aluno_id"]).str.upper(),
            "data": _data(bronze["data"]),
            "status": _texto(bronze["status"]).str.upper(),
        }
    )
    futura = (df["data"] > pd.Timestamp(today)).fillna(False).to_numpy()
    motivo = np.select(
        [
            df["aluno_id"].isna().to_numpy(),
            df["data"].isna().to_numpy(),
            futura,
            (~df["status"].isin(rules.STATUS_VALIDOS)).to_numpy(),
            (~df["aluno_id"].isin(alunos["aluno_id"])).to_numpy(),
        ],
        [
            rules.MOTIVO_ALUNO_NULO,
            rules.MOTIVO_DATA_INVALIDA,
            rules.MOTIVO_DATA_FUTURA,
            rules.MOTIVO_STATUS_INVALIDO,
            rules.MOTIVO_ALUNO_INEXISTENTE,
        ],
        default="",
    )
    motivo = _marcar_duplicados(df, motivo, ["aluno_id", "data"])
    limpo, rej = _separar(bronze.join(df, rsuffix="_limpo"), pd.Series(motivo, index=df.index))
    limpo = limpo[["aluno_id_limpo", "data_limpo", "status_limpo"]]
    limpo.columns = ["aluno_id", "data", "status"]
    return limpo.reset_index(drop=True), rej[list(bronze.columns) + ["motivo_rejeicao"]]
