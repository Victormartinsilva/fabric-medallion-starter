"""Testes de qualidade de dados, rodados entre as camadas. O resultado vira uma tabela."""
from __future__ import annotations

import pandas as pd

from . import rules


def _linha(camada, tabela, regra, falhas, total) -> dict:
    return {
        "camada": camada,
        "tabela": tabela,
        "regra": regra,
        "falhas": int(falhas),
        "total": int(total),
        "status": "OK" if falhas == 0 else "FALHOU",
    }


def run_checks(silver: dict[str, pd.DataFrame], gold: dict[str, pd.DataFrame]) -> pd.DataFrame:
    freq, alunos, turmas, escolas = (silver[k] for k in ("frequencia", "alunos", "turmas", "escolas"))
    r = []

    # Silver: unicidade, nulos, domínio e integridade referencial
    r.append(_linha("silver", "frequencia", "chave (aluno_id, data) única", freq.duplicated(["aluno_id", "data"]).sum(), len(freq)))
    r.append(_linha("silver", "frequencia", "sem nulos em aluno_id, data, status", freq[["aluno_id", "data", "status"]].isna().any(axis=1).sum(), len(freq)))
    r.append(_linha("silver", "frequencia", f"status em {rules.STATUS_VALIDOS}", (~freq["status"].isin(rules.STATUS_VALIDOS)).sum(), len(freq)))
    r.append(_linha("silver", "frequencia", "aluno_id existe em alunos", (~freq["aluno_id"].isin(alunos["aluno_id"])).sum(), len(freq)))
    r.append(_linha("silver", "alunos", "aluno_id único", alunos["aluno_id"].duplicated().sum(), len(alunos)))
    r.append(_linha("silver", "alunos", "turma_id existe em turmas", (~alunos["turma_id"].isin(turmas["turma_id"])).sum(), len(alunos)))
    r.append(_linha("silver", "turmas", "escola_id existe em escolas", (~turmas["escola_id"].isin(escolas["escola_id"])).sum(), len(turmas)))

    # Gold: faixas de valores e reconciliação com a Silver
    mensal, por_aluno, por_escola = gold["frequencia_mensal_turma"], gold["frequencia_aluno"], gold["resumo_escola"]
    r.append(_linha("gold", "frequencia_mensal_turma", "taxa_presenca entre 0 e 1", (~mensal["taxa_presenca"].between(0, 1)).sum(), len(mensal)))
    r.append(_linha("gold", "frequencia_mensal_turma", "presencas <= registros", (mensal["presencas"] > mensal["registros"]).sum(), len(mensal)))
    r.append(_linha("gold", "frequencia_aluno", "taxa_presenca entre 0 e 1", (~por_aluno["taxa_presenca"].between(0, 1)).sum(), len(por_aluno)))
    r.append(_linha("gold", "resumo_escola", "soma de alunos = alunos com frequência na silver", abs(por_escola["alunos"].sum() - freq["aluno_id"].nunique()), 1))
    r.append(_linha("gold", "frequencia_mensal_turma", "soma de registros = linhas da silver.frequencia", abs(mensal["registros"].sum() - len(freq)), 1))
    return pd.DataFrame(r)
