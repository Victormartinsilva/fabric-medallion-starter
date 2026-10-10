import pandas as pd
import pytest

from medallion import bronze

INGESTED = "2025-08-01T00:00:00+00:00"


def b(rows: list[dict], nome: str) -> pd.DataFrame:
    """Monta uma tabela Bronze a partir de linhas de texto."""
    return bronze.to_bronze(pd.DataFrame(rows), f"{nome}.csv", INGESTED)


@pytest.fixture
def cadastro():
    """Cadastro mínimo e limpo: 1 escola, 1 turma, 2 alunos."""
    escolas = pd.DataFrame({"escola_id": ["E01"], "nome": ["EM Teste"], "municipio": ["Vale Verde"]})
    turmas = pd.DataFrame({"turma_id": ["E01-T01"], "escola_id": ["E01"], "serie": ["6º ano"], "turno": ["Manhã"]})
    alunos = pd.DataFrame(
        {
            "aluno_id": ["A1", "A2"],
            "turma_id": ["E01-T01", "E01-T01"],
            "nome": ["Ana Lima", "Bruno Dias"],
            "data_nascimento": pd.to_datetime(["2014-01-01", "2014-02-02"]),
        }
    )
    return escolas, turmas, alunos
