import enum


class Origem(str, enum.Enum):
    SITE = "SITE"
    DIRETO = "DIRETO"


class Modo(str, enum.Enum):
    BOT = "BOT"
    HUMANO = "HUMANO"
    AGUARDANDO_EQUIPE = "AGUARDANDO_EQUIPE"


class Remetente(str, enum.Enum):
    CLIENTE = "CLIENTE"
    BOT = "BOT"
    ATENDENTE = "ATENDENTE"


class StatusAgendamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    REAGENDADO = "REAGENDADO"
    CANCELADO = "CANCELADO"
    CONCLUIDO = "CONCLUIDO"
    NAO_COMPARECEU = "NAO_COMPARECEU"


ACTIVE_STATUSES = (
    StatusAgendamento.PENDENTE,
    StatusAgendamento.CONFIRMADO,
    StatusAgendamento.REAGENDADO,
)


class Papel(str, enum.Enum):
    ADMIN = "ADMIN"
    ATENDENTE = "ATENDENTE"
