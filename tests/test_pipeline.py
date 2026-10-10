import pandas as pd

from medallion import pipeline
from medallion.generate import generate_raw

FIXO = "2025-08-01T00:00:00+00:00"


def test_gerador_e_deterministico(tmp_path):
    a = generate_raw(tmp_path / "a", seed=7)
    b = generate_raw(tmp_path / "b", seed=7)
    c = generate_raw(tmp_path / "c", seed=8)

    for tabela in a:
        assert a[tabela].read_bytes() == b[tabela].read_bytes()
    assert a["frequencia"].read_bytes() != c["frequencia"].read_bytes()


def test_gerador_injeta_a_sujeira_prometida(tmp_path):
    arquivos = generate_raw(tmp_path, seed=1)
    freq = pd.read_csv(arquivos["frequencia"], dtype=str, keep_default_na=False)

    assert freq.duplicated().any()
    assert (freq["status"] == "X").any()
    assert (freq["aluno_id"] == "").any()
    assert (freq["aluno_id"] == "A99999").any()
    assert (freq["data"] == "31/02/2025").any()


def test_pipeline_ponta_a_ponta(tmp_path):
    out = pipeline.run(tmp_path, ingested_at=FIXO)

    # Nada se perde: o que entra no Bronze é o que sai na Silver + quarentena
    for tabela in ("escolas", "turmas", "alunos", "frequencia"):
        assert out["silver"][tabela] + out["quarentena"][tabela] == out["bronze"][tabela]

    # A quarentena tem coisa (a sujeira foi pega) e a Silver ficou limpa
    assert out["quarentena"]["frequencia"] > 0
    assert (out["qualidade"]["status"] == "OK").all()
    assert (tmp_path / "gold" / "resumo_escola.parquet").exists()


def test_pipeline_e_idempotente(tmp_path):
    pipeline.run(tmp_path / "um", ingested_at=FIXO)
    pipeline.run(tmp_path / "dois", ingested_at=FIXO)

    for tabela in ("frequencia_aluno", "frequencia_mensal_turma", "resumo_escola"):
        um = pd.read_parquet(tmp_path / "um" / "gold" / f"{tabela}.parquet")
        dois = pd.read_parquet(tmp_path / "dois" / "gold" / f"{tabela}.parquet")
        pd.testing.assert_frame_equal(um, dois)


def test_aluno_em_risco_so_existe_com_taxa_abaixo_do_limite(tmp_path):
    pipeline.run(tmp_path, ingested_at=FIXO)
    alunos = pd.read_parquet(tmp_path / "gold" / "frequencia_aluno.parquet")

    assert alunos["em_risco"].equals(alunos["taxa_presenca"] < 0.75)
    assert 0 < alunos["em_risco"].mean() < 0.25  # existe risco, mas não é a maioria
