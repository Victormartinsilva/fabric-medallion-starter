"""Orquestra Bronze → Silver → Gold localmente, gravando Parquet.

No Fabric, os notebooks chamam as mesmas funções e trocam só a gravação (Delta).

    python -m medallion.pipeline --base data
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import bronze, gold, quality, rules, silver
from .generate import generate_raw


def run(
    base_dir: str | Path = "data",
    *,
    regenerate: bool = True,
    seed: int = 42,
    today: str = "2025-08-01",
    ingested_at: str | None = None,
    fail_on_error: bool = True,
) -> dict:
    base = Path(base_dir)
    raw_dir = base / "raw"
    ingested_at = ingested_at or datetime.now(timezone.utc).isoformat(timespec="seconds")

    if regenerate:
        generate_raw(raw_dir, seed=seed, today=today)

    # Bronze
    b = {}
    for tabela in rules.TABELAS_RAW:
        raw = pd.read_csv(raw_dir / f"{tabela}.csv", dtype=str, keep_default_na=False)
        b[tabela] = bronze.to_bronze(raw, f"{tabela}.csv", ingested_at)
        _gravar(b[tabela], base / "bronze" / f"{tabela}.parquet")

    # Silver (a ordem importa: cada tabela depende das anteriores)
    escolas, rej_escolas = silver.clean_escolas(b["escolas"])
    turmas, rej_turmas = silver.clean_turmas(b["turmas"], escolas)
    alunos, rej_alunos = silver.clean_alunos(b["alunos"], turmas)
    freq, rej_freq = silver.clean_frequencia(b["frequencia"], alunos, today)
    s = {"escolas": escolas, "turmas": turmas, "alunos": alunos, "frequencia": freq}
    q = {"escolas": rej_escolas, "turmas": rej_turmas, "alunos": rej_alunos, "frequencia": rej_freq}
    for nome, df in s.items():
        _gravar(df, base / "silver" / f"{nome}.parquet")
    for nome, df in q.items():
        _gravar(df, base / "quarentena" / f"{nome}.parquet")

    # Gold
    por_aluno = gold.frequencia_aluno(freq, alunos, turmas, escolas)
    g = {
        "frequencia_mensal_turma": gold.frequencia_mensal_turma(freq, alunos, turmas, escolas),
        "frequencia_aluno": por_aluno,
        "resumo_escola": gold.resumo_escola(por_aluno),
    }
    for nome, df in g.items():
        _gravar(df, base / "gold" / f"{nome}.parquet")

    # Qualidade
    relatorio = quality.run_checks(s, g)
    relatorio.to_csv(base / "qualidade.csv", index=False)
    falhas = relatorio[relatorio["status"] != "OK"]
    if fail_on_error and not falhas.empty:
        raise AssertionError(f"Checagens de qualidade falharam:\n{falhas.to_string(index=False)}")

    return {
        "bronze": {k: len(v) for k, v in b.items()},
        "silver": {k: len(v) for k, v in s.items()},
        "quarentena": {k: len(v) for k, v in q.items()},
        "gold": {k: len(v) for k, v in g.items()},
        "qualidade": relatorio,
    }


def _gravar(df: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(caminho, index=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="Roda o pipeline Medallion local.")
    ap.add_argument("--base", default="data", help="pasta de trabalho (raw, bronze, silver, gold)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-regenerate", action="store_true", help="reaproveita os CSVs de data/raw")
    args = ap.parse_args()

    out = run(args.base, regenerate=not args.no_regenerate, seed=args.seed)
    for camada in ("bronze", "silver", "quarentena", "gold"):
        print(f"{camada:>10}: " + ", ".join(f"{k}={v}" for k, v in out[camada].items()))
    print()
    print(out["qualidade"].to_string(index=False))


if __name__ == "__main__":
    main()
