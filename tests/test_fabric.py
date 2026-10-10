import pandas as pd

from medallion import fabric


class FakeWriter:
    def __init__(self, calls):
        self.calls = calls

    def mode(self, m):
        self.calls.append(("mode", m))
        return self

    def format(self, f):
        self.calls.append(("format", f))
        return self

    def saveAsTable(self, name):
        self.calls.append(("saveAsTable", name))


class FakeSpark:
    """Substituto mínimo do SparkSession, só para verificar o que o código pede."""

    def __init__(self):
        self.calls = []
        self.received = None

    def createDataFrame(self, pdf):
        self.received = pdf
        return type("SDF", (), {"write": FakeWriter(self.calls)})()


def test_sanitize_troca_nulos_por_none_e_tira_dtype_string():
    df = pd.DataFrame({"a": pd.array(["x", pd.NA], dtype="string"), "n": [1.0, float("nan")]})
    out = fabric.sanitize_for_spark(df)

    assert out["a"].tolist() == ["x", None]
    assert out["n"].tolist() == [1.0, None]
    assert all(dtype == object for dtype in out.dtypes)


def test_save_delta_grava_como_delta_na_tabela_pedida():
    spark = FakeSpark()
    fabric.save_delta(spark, pd.DataFrame({"a": [1]}), "silver_frequencia")

    assert spark.calls == [("mode", "overwrite"), ("format", "delta"), ("saveAsTable", "silver_frequencia")]
    assert len(spark.received) == 1
