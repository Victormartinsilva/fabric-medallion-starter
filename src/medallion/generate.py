"""Gera os arquivos 'brutos' (CSV) com dados sintéticos e sujeira injetada de propósito.

Nada aqui é real: nomes, escolas e municípios são fictícios. A sujeira existe para o
pipeline ter o que limpar: duplicados, status inválidos, datas futuras, chaves nulas.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MUNICIPIOS = ["Vale Verde", "Serra Azul", "Porto Claro", "Campo Alto", "Lagoa Dourada"]
PATRONOS = ["Machado de Assis", "Cecília Meireles", "Santos Dumont", "Carolina de Jesus", "Paulo Freire"]
PRIMEIROS = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabriela", "Hugo", "Isabela", "João",
              "Karina", "Lucas", "Marina", "Nicolas", "Olívia", "Pedro", "Rafaela", "Sofia", "Tiago", "Vitória"]
SOBRENOMES = ["Almeida", "Barros", "Cardoso", "Dias", "Esteves", "Farias", "Gomes", "Lima", "Moraes",
              "Nogueira", "Oliveira", "Pereira", "Queiroz", "Ribeiro", "Souza", "Teixeira"]
SERIES = ["6º ano", "7º ano", "8º ano", "9º ano"]
TURNOS = ["Manhã", "Tarde"]


def _pct(rng: np.random.Generator, n: int, pct: float) -> np.ndarray:
    """Índices de ~pct das n linhas (pelo menos 1), sem repetição."""
    k = max(1, int(n * pct))
    return rng.choice(n, size=k, replace=False)


def generate_raw(
    out_dir: str | Path,
    *,
    n_escolas: int = 5,
    turmas_por_escola: int = 4,
    alunos_por_turma: int = 25,
    dias_letivos: int = 60,
    seed: int = 42,
    start: str = "2025-03-03",
    today: str = "2025-08-01",
    sujeira: bool = True,
) -> dict[str, Path]:
    """Cria escolas.csv, turmas.csv, alunos.csv e frequencia.csv em `out_dir`.

    Com a mesma `seed`, os arquivos saem idênticos. `today` é a data de referência usada
    para fabricar datas futuras (e depois detectá-las no Silver).
    """
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    escolas = pd.DataFrame(
        {
            "escola_id": [f"E{i:02d}" for i in range(1, n_escolas + 1)],
            "nome": [f"EM {PATRONOS[i % len(PATRONOS)]}" for i in range(n_escolas)],
            "municipio": [MUNICIPIOS[i % len(MUNICIPIOS)] for i in range(n_escolas)],
        }
    )

    turmas_rows = []
    for escola_id in escolas["escola_id"]:
        for j in range(turmas_por_escola):
            turmas_rows.append(
                {
                    "turma_id": f"{escola_id}-T{j + 1:02d}",
                    "escola_id": escola_id,
                    "serie": SERIES[j % len(SERIES)],
                    "turno": TURNOS[j % len(TURNOS)],
                }
            )
    turmas = pd.DataFrame(turmas_rows)

    alunos_rows = []
    contador = 0
    for turma in turmas.itertuples():
        ano_base = 2014 - SERIES.index(turma.serie)
        for _ in range(alunos_por_turma):
            contador += 1
            nome = f"{rng.choice(PRIMEIROS)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"
            nasc = pd.Timestamp(year=ano_base, month=1, day=1) + pd.Timedelta(days=int(rng.integers(0, 365)))
            alunos_rows.append(
                {
                    "aluno_id": f"A{contador:05d}",
                    "turma_id": turma.turma_id,
                    "nome": nome,
                    "data_nascimento": nasc.strftime("%Y-%m-%d"),
                }
            )
    alunos = pd.DataFrame(alunos_rows)

    # Frequência: um registro por aluno e por dia útil.
    dias = pd.bdate_range(start, periods=dias_letivos)
    n_alunos = len(alunos)
    # Cada aluno tem a sua propensão a comparecer (média ~91%); ~8% são alunos em risco.
    propensao = rng.beta(30, 3, size=n_alunos)
    em_risco = rng.random(n_alunos) < 0.08
    propensao[em_risco] = rng.uniform(0.45, 0.72, size=em_risco.sum())

    ids = np.repeat(alunos["aluno_id"].to_numpy(), len(dias))
    datas = np.tile(dias.strftime("%Y-%m-%d").to_numpy(), n_alunos)
    p = np.repeat(propensao, len(dias))
    presente = rng.random(len(p)) < p
    falta_justificada = rng.random(len(p)) < 0.25
    status = np.where(presente, "P", np.where(falta_justificada, "J", "F"))
    frequencia = pd.DataFrame({"aluno_id": ids, "data": datas, "status": status})

    if sujeira:
        escolas, turmas, alunos, frequencia = _sujar(rng, escolas, turmas, alunos, frequencia, today)

    arquivos = {}
    for nome_tabela, df in (
        ("escolas", escolas),
        ("turmas", turmas),
        ("alunos", alunos),
        ("frequencia", frequencia),
    ):
        caminho = out / f"{nome_tabela}.csv"
        df.to_csv(caminho, index=False)
        arquivos[nome_tabela] = caminho
    return arquivos


def _sujar(rng, escolas, turmas, alunos, frequencia, today):
    frequencia = frequencia.copy().astype(str)
    alunos = alunos.copy().astype(str)
    n = len(frequencia)

    # 1) status com caixa e espaços diferentes (válidos depois de limpar)
    idx = _pct(rng, n, 0.03)
    frequencia.loc[idx, "status"] = frequencia.loc[idx, "status"].str.lower() + " "
    # 2) status inválido
    frequencia.loc[_pct(rng, n, 0.01), "status"] = "X"
    # 3) data no futuro
    futuro = (pd.Timestamp(today) + pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    frequencia.loc[_pct(rng, n, 0.005), "data"] = futuro
    # 4) data impossível
    frequencia.loc[_pct(rng, n, 0.003), "data"] = "31/02/2025"
    # 5) aluno_id vazio
    frequencia.loc[_pct(rng, n, 0.005), "aluno_id"] = ""
    # 6) aluno que não existe no cadastro
    frequencia.loc[_pct(rng, n, 0.005), "aluno_id"] = "A99999"
    # 7) registros duplicados
    frequencia = pd.concat([frequencia, frequencia.iloc[_pct(rng, n, 0.02)]], ignore_index=True)

    # nomes bagunçados no cadastro
    m = len(alunos)
    idx = _pct(rng, m, 0.10)
    alunos.loc[idx, "nome"] = "  " + alunos.loc[idx, "nome"].str.upper() + "  "
    # aluno duplicado
    alunos = pd.concat([alunos, alunos.iloc[_pct(rng, m, 0.01)]], ignore_index=True)
    return escolas, turmas, alunos, frequencia
