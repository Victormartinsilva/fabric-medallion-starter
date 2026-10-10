import pandas as pd

from conftest import b
from medallion import rules, silver

TODAY = "2025-08-01"


def _freq(*linhas):
    return b([{"aluno_id": a, "data": d, "status": s} for a, d, s in linhas], "frequencia")


def test_cada_defeito_cai_na_quarentena_com_o_motivo_certo(cadastro):
    _, _, alunos = cadastro
    bronze_freq = _freq(
        ("A1", "2025-03-03", "P"),  # ok
        ("A1", "2025-03-04", "  p "),  # ok depois de limpar caixa e espaços
        ("", "2025-03-03", "P"),  # aluno nulo
        ("A1", "31/02/2025", "P"),  # data impossível
        ("A1", "2025-09-01", "P"),  # data futura (hoje é 2025-08-01)
        ("A1", "2025-03-05", "X"),  # status inválido
        ("A9", "2025-03-03", "P"),  # aluno inexistente
        ("A2", "2025-03-03", "F"),  # ok
        ("A2", "2025-03-03", "P"),  # duplicado da linha acima (mesmo aluno e dia)
    )
    limpo, rej = silver.clean_frequencia(bronze_freq, alunos, TODAY)

    assert len(limpo) == 3
    assert sorted(limpo["status"]) == ["F", "P", "P"]
    assert dict(rej["motivo_rejeicao"].value_counts()) == {
        rules.MOTIVO_ALUNO_NULO: 1,
        rules.MOTIVO_DATA_INVALIDA: 1,
        rules.MOTIVO_DATA_FUTURA: 1,
        rules.MOTIVO_STATUS_INVALIDO: 1,
        rules.MOTIVO_ALUNO_INEXISTENTE: 1,
        rules.MOTIVO_DUPLICADO: 1,
    }


def test_nada_se_perde_entre_bronze_e_silver(cadastro):
    _, _, alunos = cadastro
    bronze_freq = _freq(
        ("A1", "2025-03-03", "P"), ("A1", "2025-03-03", "P"), ("", "2025-03-03", "P"), ("A2", "2025-03-04", "J")
    )
    limpo, rej = silver.clean_frequencia(bronze_freq, alunos, TODAY)

    assert len(limpo) + len(rej) == len(bronze_freq)


def test_duplicado_mantem_a_primeira_ocorrencia(cadastro):
    _, _, alunos = cadastro
    limpo, rej = silver.clean_frequencia(_freq(("A1", "2025-03-03", "F"), ("A1", "2025-03-03", "P")), alunos, TODAY)

    assert limpo["status"].tolist() == ["F"]
    assert rej["motivo_rejeicao"].tolist() == [rules.MOTIVO_DUPLICADO]


def test_motivo_longo_nao_e_cortado(cadastro):
    """Regressão: o np.select usa texto de largura fixa e cortava 'registro duplicado'."""
    _, _, alunos = cadastro
    _, rej = silver.clean_frequencia(_freq(("A1", "2025-03-03", "P"), ("A1", "2025-03-03", "P")), alunos, TODAY)

    assert rej["motivo_rejeicao"].iloc[0] == "registro duplicado"


def test_alunos_normaliza_nome_e_rejeita_duplicado_e_turma_inexistente(cadastro):
    _, turmas, _ = cadastro
    bronze_alunos = b(
        [
            {"aluno_id": "a1", "turma_id": "E01-T01", "nome": "  ANA   LIMA ", "data_nascimento": "2014-01-01"},
            {"aluno_id": "A1", "turma_id": "E01-T01", "nome": "Ana Lima", "data_nascimento": "2014-01-01"},
            {"aluno_id": "A3", "turma_id": "E99-T01", "nome": "Sem Turma", "data_nascimento": "2014-01-01"},
        ],
        "alunos",
    )
    limpo, rej = silver.clean_alunos(bronze_alunos, turmas)

    assert limpo["nome"].tolist() == ["Ana Lima"]
    assert limpo["aluno_id"].tolist() == ["A1"]
    assert sorted(rej["motivo_rejeicao"]) == sorted([rules.MOTIVO_DUPLICADO, rules.MOTIVO_TURMA_INEXISTENTE])


def test_turma_de_escola_inexistente_vai_para_quarentena(cadastro):
    escolas, _, _ = cadastro
    bronze_turmas = b(
        [
            {"turma_id": "E01-T01", "escola_id": "E01", "serie": "6º ano", "turno": "Manhã"},
            {"turma_id": "E09-T01", "escola_id": "E09", "serie": "6º ano", "turno": "Manhã"},
        ],
        "turmas",
    )
    limpo, rej = silver.clean_turmas(bronze_turmas, escolas)

    assert limpo["turma_id"].tolist() == ["E01-T01"]
    assert rej["motivo_rejeicao"].tolist() == [rules.MOTIVO_ESCOLA_INEXISTENTE]
