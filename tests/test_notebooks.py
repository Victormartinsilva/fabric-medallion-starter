"""Executa as células dos notebooks do Fabric, em ordem, contra um Spark falso em memória.

Isso não substitui rodar no Fabric, mas pega o que quebra de verdade: nome errado, import
que não existe, tabela lida antes de ser gravada, coluna que sumiu entre as etapas.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from medallion import fabric

FABRIC_DIR = Path(__file__).resolve().parents[1] / "fabric"


class _Writer:
    def __init__(self, store, pdf):
        self.store, self.pdf, self._mode = store, pdf, "overwrite"

    def mode(self, m):
        self._mode = m
        return self

    def format(self, f):
        assert f == "delta"
        return self

    def saveAsTable(self, name):
        self.store[name] = self.pdf.copy()


class _Table:
    def __init__(self, pdf):
        self.pdf = pdf

    def toPandas(self):
        # O Spark devolve colunas já tipadas (datas como datetime64); infer_objects imita isso.
        return self.pdf.infer_objects()


class FakeLakehouse:
    def __init__(self):
        self.tables: dict[str, pd.DataFrame] = {}
        self.read = type("Reader", (), {"table": lambda _, name: _Table(self.tables[name])})()

    def createDataFrame(self, pdf):
        return type("SDF", (), {"write": _Writer(self.tables, pdf)})()


def _codigo(caminho: Path) -> list[str]:
    nb = json.loads(caminho.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_notebooks_rodam_em_sequencia(tmp_path, monkeypatch):
    monkeypatch.setattr(fabric, "LAKEHOUSE_FILES", str(tmp_path))
    spark = FakeLakehouse()

    notebooks = sorted(FABRIC_DIR.glob("*.ipynb"))
    assert [n.name[:2] for n in notebooks] == ["00", "01", "02", "03"]

    for nb in notebooks:
        ns = {"spark": spark, "display": lambda *_a, **_k: None}  # cada notebook é um kernel novo
        for celula in _codigo(nb):
            exec(compile(celula, str(nb), "exec"), ns)

    t = spark.tables
    for nome in ("bronze_frequencia", "silver_frequencia", "quarentena_frequencia", "gold_resumo_escola", "qualidade"):
        assert nome in t, f"tabela {nome} não foi gravada"

    # Mesmas garantias do pipeline local
    for tabela in ("escolas", "turmas", "alunos", "frequencia"):
        assert len(t[f"silver_{tabela}"]) + len(t[f"quarentena_{tabela}"]) == len(t[f"bronze_{tabela}"])
    assert (t["qualidade"]["status"] == "OK").all()
    assert len(t["gold_resumo_escola"]) == 5
