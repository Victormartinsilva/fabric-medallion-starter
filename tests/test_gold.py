import pandas as pd
import pytest

from medallion import gold


@pytest.fixture
def freq():
    # A1: P P P F  -> 3/4 = 0.75   (exatamente no limite: NÃO está em risco)
    # A2: P F F J  -> 1/4 = 0.25   (em risco; com J contando como presença seria 2/4 = 0.50)
    dias = pd.to_datetime(["2025-03-03", "2025-03-04", "2025-03-05", "2025-03-06"])
    linhas = [("A1", d, s) for d, s in zip(dias, "PPPF")] + [("A2", d, s) for d, s in zip(dias, "PFFJ")]
    return pd.DataFrame(linhas, columns=["aluno_id", "data", "status"])


def test_frequencia_aluno_calcula_taxa_e_risco(freq, cadastro):
    escolas, turmas, alunos = cadastro
    out = gold.frequencia_aluno(freq, alunos, turmas, escolas).set_index("aluno_id")

    assert out.loc["A1", "taxa_presenca"] == 0.75
    assert not out.loc["A1", "em_risco"]  # 75% é o mínimo: abaixo disso é risco
    assert out.loc["A2", "taxa_presenca"] == 0.25
    assert out.loc["A2", ["faltas", "faltas_justificadas"]].tolist() == [2, 1]
    assert out.loc["A2", "em_risco"]


def test_justificada_pode_contar_como_presenca(freq, cadastro):
    escolas, turmas, alunos = cadastro
    out = gold.frequencia_aluno(freq, alunos, turmas, escolas, justificada_conta_como_presenca=True)

    assert out.set_index("aluno_id").loc["A2", "taxa_presenca"] == 0.5


def test_mensal_por_turma(freq, cadastro):
    escolas, turmas, alunos = cadastro
    out = gold.frequencia_mensal_turma(freq, alunos, turmas, escolas)

    assert len(out) == 1  # uma turma, um mês
    row = out.iloc[0]
    assert row["mes"] == "2025-03"
    assert (row["alunos"], row["dias_letivos"], row["registros"], row["presencas"]) == (2, 4, 8, 4)
    assert row["taxa_presenca"] == 0.5  # (3 + 1) / 8


def test_resumo_da_escola(freq, cadastro):
    escolas, turmas, alunos = cadastro
    resumo = gold.resumo_escola(gold.frequencia_aluno(freq, alunos, turmas, escolas))

    row = resumo.iloc[0]
    assert (row["alunos"], row["alunos_em_risco"]) == (2, 1)
    assert row["pct_alunos_em_risco"] == 0.5
    assert row["taxa_presenca"] == 0.5
