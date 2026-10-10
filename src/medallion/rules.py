"""Regras de negócio e nomes de tabelas, num lugar só."""

# P = presente, F = falta, J = falta justificada
STATUS_VALIDOS = ("P", "F", "J")

# Frequência mínima exigida (75% das aulas, como na LDB, art. 24).
LIMITE_FREQUENCIA = 0.75

TABELAS_RAW = ("escolas", "turmas", "alunos", "frequencia")

# Motivos de rejeição gravados na quarentena (Silver).
MOTIVO_ALUNO_NULO = "aluno_id nulo"
MOTIVO_DATA_INVALIDA = "data invalida"
MOTIVO_DATA_FUTURA = "data futura"
MOTIVO_STATUS_INVALIDO = "status invalido"
MOTIVO_ALUNO_INEXISTENTE = "aluno inexistente"
MOTIVO_DUPLICADO = "registro duplicado"
MOTIVO_TURMA_INEXISTENTE = "turma inexistente"
MOTIVO_ESCOLA_INEXISTENTE = "escola inexistente"
