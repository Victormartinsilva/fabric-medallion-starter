import pandas as pd

from medallion import bronze


def test_bronze_guarda_o_dado_como_chegou():
    raw = pd.DataFrame({"aluno_id": ["  a1 "], "status": ["p"], "data": ["31/02/2025"]})
    out = bronze.to_bronze(raw, "frequencia.csv", "2025-08-01T00:00:00+00:00")

    assert out.loc[0, "aluno_id"] == "  a1 "  # espaços e caixa intactos
    assert out.loc[0, "data"] == "31/02/2025"  # data inválida não é corrigida nem descartada
    assert len(out) == len(raw)


def test_bronze_adiciona_linhagem_e_tudo_e_texto():
    raw = pd.DataFrame({"n": [1, 2]})
    out = bronze.to_bronze(raw, "x.csv", "2025-08-01T00:00:00+00:00")

    assert (out["_source_file"] == "x.csv").all()
    assert (out["_ingested_at"] == "2025-08-01T00:00:00+00:00").all()
    assert all(pd.api.types.is_string_dtype(out[c]) for c in out.columns)
