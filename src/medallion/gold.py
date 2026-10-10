"""Gold: tabelas prontas para consumo (Power BI, Direct Lake, relatórios).

Cada tabela responde uma pergunta de negócio e tem o grão dito no nome.
"""
from __future__ import annotations

import pandas as pd

from . import rules


def _presente(status: pd.Series, justificada_conta_como_presenca: bool) -> pd.Series:
    contam = ["P", "J"] if justificada_conta_como_presenca else ["P"]
    return status.isin(contam).astype(int)


def _base(frequencia, alunos, turmas, escolas) -> pd.DataFrame:
    df = (
        frequencia.merge(alunos[["aluno_id", "nome", "turma_id"]], on="aluno_id")
        .merge(turmas[["turma_id", "escola_id", "serie", "turno"]], on="turma_id")
        .merge(escolas[["escola_id", "nome", "municipio"]].rename(columns={"nome": "escola"}), on="escola_id")
    )
    return df.rename(columns={"nome": "aluno"})


def frequencia_mensal_turma(
    frequencia, alunos, turmas, escolas, *, justificada_conta_como_presenca: bool = False
) -> pd.DataFrame:
    """Grão: uma linha por turma e mês. Responde: qual a taxa de presença de cada turma?"""
    df = _base(frequencia, alunos, turmas, escolas)
    df["mes"] = df["data"].dt.strftime("%Y-%m")
    df["presente"] = _presente(df["status"], justificada_conta_como_presenca)
    out = (
        df.groupby(["escola_id", "escola", "turma_id", "serie", "turno", "mes"], as_index=False)
        .agg(
            alunos=("aluno_id", "nunique"),
            dias_letivos=("data", "nunique"),
            registros=("status", "size"),
            presencas=("presente", "sum"),
        )
    )
    out["taxa_presenca"] = (out["presencas"] / out["registros"]).round(4)
    return out


def frequencia_aluno(
    frequencia,
    alunos,
    turmas,
    escolas,
    *,
    limite: float = rules.LIMITE_FREQUENCIA,
    justificada_conta_como_presenca: bool = False,
) -> pd.DataFrame:
    """Grão: uma linha por aluno. Responde: quem está abaixo da frequência mínima?"""
    df = _base(frequencia, alunos, turmas, escolas)
    df["presente"] = _presente(df["status"], justificada_conta_como_presenca)
    out = (
        df.groupby(["aluno_id", "aluno", "turma_id", "escola_id", "escola"], as_index=False)
        .agg(
            registros=("status", "size"),
            presencas=("presente", "sum"),
            faltas=("status", lambda s: int((s == "F").sum())),
            faltas_justificadas=("status", lambda s: int((s == "J").sum())),
        )
    )
    out["taxa_presenca"] = (out["presencas"] / out["registros"]).round(4)
    out["em_risco"] = out["taxa_presenca"] < limite
    return out.sort_values(["taxa_presenca", "aluno_id"]).reset_index(drop=True)


def resumo_escola(freq_aluno: pd.DataFrame) -> pd.DataFrame:
    """Grão: uma linha por escola. Responde: como está cada escola, no geral?"""
    out = freq_aluno.groupby(["escola_id", "escola"], as_index=False).agg(
        alunos=("aluno_id", "nunique"),
        registros=("registros", "sum"),
        presencas=("presencas", "sum"),
        alunos_em_risco=("em_risco", "sum"),
    )
    out["taxa_presenca"] = (out["presencas"] / out["registros"]).round(4)
    out["pct_alunos_em_risco"] = (out["alunos_em_risco"] / out["alunos"]).round(4)
    out["alunos_em_risco"] = out["alunos_em_risco"].astype(int)
    return out.drop(columns=["registros", "presencas"])
