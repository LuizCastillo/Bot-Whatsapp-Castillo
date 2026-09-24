from datetime import datetime, time

from sqlalchemy import JSON, Boolean, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime, utcnow
from app.database.enums import Modo, Origem, Papel, Remetente, StatusAgendamento


def enum_col(e):
    return SAEnum(e, native_enum=False, length=30, create_constraint=False, values_callable=lambda x: [m.value for m in x])


class Cliente(Base, TimestampMixin):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    telefone: Mapped[str] = mapped_column(String(20), unique=True)  # canônico (E.164 sem +)
    wa_id: Mapped[str | None] = mapped_column(String(20))  # id original da Meta, usado para responder
    nome: Mapped[str | None] = mapped_column(String(120))


class Veiculo(Base, TimestampMixin):
    __tablename__ = "veiculos"
    __table_args__ = (UniqueConstraint("cliente_id", "placa", name="uq_veiculo_cliente_placa"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    marca: Mapped[str] = mapped_column(String(60))
    modelo: Mapped[str] = mapped_column(String(80))
    ano: Mapped[int | None] = mapped_column(Integer)
    placa: Mapped[str | None] = mapped_column(String(8))


class Servico(Base):
    __tablename__ = "servicos"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    nome: Mapped[str] = mapped_column(String(80))
    descricao: Mapped[str] = mapped_column(Text, default="")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)


class Atendente(Base):
    __tablename__ = "atendentes"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(300))
    papel: Mapped[Papel] = mapped_column(enum_col(Papel), default=Papel.ATENDENTE)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Sessao(Base):
    __tablename__ = "sessoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    atendente_id: Mapped[int] = mapped_column(ForeignKey("atendentes.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expira_em: Mapped[datetime] = mapped_column(UTCDateTime)
    ultimo_uso: Mapped[datetime | None] = mapped_column(UTCDateTime)
    ip: Mapped[str | None] = mapped_column(String(64))
    revogada: Mapped[bool] = mapped_column(Boolean, default=False)


class Conversa(Base, TimestampMixin):
    __tablename__ = "conversas"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    origem: Mapped[Origem] = mapped_column(enum_col(Origem), default=Origem.DIRETO)
    intencao: Mapped[str | None] = mapped_column(String(30))
    estado_atual: Mapped[str] = mapped_column(String(50), default="INICIO")
    contexto: Mapped[dict] = mapped_column(JSON, default=dict)
    modo: Mapped[Modo] = mapped_column(enum_col(Modo), default=Modo.BOT, index=True)
    atendente_id: Mapped[int | None] = mapped_column(ForeignKey("atendentes.id", ondelete="SET NULL"))
    ultima_msg_cliente_em: Mapped[datetime | None] = mapped_column(UTCDateTime)


class Mensagem(Base):
    __tablename__ = "mensagens"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversa_id: Mapped[int] = mapped_column(ForeignKey("conversas.id", ondelete="CASCADE"), index=True)
    remetente: Mapped[Remetente] = mapped_column(enum_col(Remetente))
    tipo: Mapped[str] = mapped_column(String(20), default="TEXT")
    conteudo: Mapped[str] = mapped_column(Text, default="")
    wa_message_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    midia_ref: Mapped[str | None] = mapped_column(String(300))
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Avaliacao(Base, TimestampMixin):
    __tablename__ = "avaliacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    veiculo_id: Mapped[int | None] = mapped_column(ForeignKey("veiculos.id", ondelete="SET NULL"))
    servico_pretendido_id: Mapped[int | None] = mapped_column(ForeignKey("servicos.id"))
    servico_identificado_id: Mapped[int | None] = mapped_column(ForeignKey("servicos.id"))
    conversa_id: Mapped[int | None] = mapped_column(ForeignKey("conversas.id", ondelete="SET NULL"))
    descricao_problema: Mapped[str | None] = mapped_column(Text)
    observacoes_internas: Mapped[str | None] = mapped_column(Text)


_ACTIVE = "status IN ('PENDENTE','CONFIRMADO','REAGENDADO')"


class Agendamento(Base, TimestampMixin):
    __tablename__ = "agendamentos"
    __table_args__ = (
        # Garantia final contra duas reservas no mesmo horário (capacidade 1).
        Index("uq_agendamento_slot_ativo", "data_hora_inicio", unique=True,
              postgresql_where=text(_ACTIVE), sqlite_where=text(_ACTIVE)),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    avaliacao_id: Mapped[int] = mapped_column(ForeignKey("avaliacoes.id", ondelete="CASCADE"), index=True)
    data_hora_inicio: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    data_hora_fim: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[StatusAgendamento] = mapped_column(enum_col(StatusAgendamento), default=StatusAgendamento.PENDENTE)
    criado_por: Mapped[str] = mapped_column(String(40), default="BOT")


class HistoricoAgendamento(Base):
    __tablename__ = "historico_agendamento"
    id: Mapped[int] = mapped_column(primary_key=True)
    agendamento_id: Mapped[int] = mapped_column(ForeignKey("agendamentos.id", ondelete="CASCADE"), index=True)
    status_anterior: Mapped[str | None] = mapped_column(String(30))
    status_novo: Mapped[str] = mapped_column(String(30))
    inicio_anterior: Mapped[datetime | None] = mapped_column(UTCDateTime)
    inicio_novo: Mapped[datetime | None] = mapped_column(UTCDateTime)
    motivo: Mapped[str | None] = mapped_column(String(300))
    autor: Mapped[str] = mapped_column(String(40))
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class FotoAvaliacao(Base):
    __tablename__ = "fotos_avaliacao"
    id: Mapped[int] = mapped_column(primary_key=True)
    avaliacao_id: Mapped[int] = mapped_column(ForeignKey("avaliacoes.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(50))
    tamanho: Mapped[int] = mapped_column(Integer)
    wa_media_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    criado_em: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class HorarioFuncionamento(Base):
    __tablename__ = "horarios_funcionamento"
    id: Mapped[int] = mapped_column(primary_key=True)
    dia_semana: Mapped[int] = mapped_column(Integer)  # 0 = segunda
    abre: Mapped[time] = mapped_column(Time)
    fecha: Mapped[time] = mapped_column(Time)


class Bloqueio(Base):
    __tablename__ = "bloqueios"
    id: Mapped[int] = mapped_column(primary_key=True)
    inicio: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    fim: Mapped[datetime] = mapped_column(UTCDateTime)
    motivo: Mapped[str | None] = mapped_column(String(200))
    criado_por: Mapped[int | None] = mapped_column(ForeignKey("atendentes.id", ondelete="SET NULL"))


class ConfiguracaoAgenda(Base):
    __tablename__ = "configuracao_agenda"
    id: Mapped[int] = mapped_column(primary_key=True)
    slot_minutos: Mapped[int] = mapped_column(Integer, default=60)
    antecedencia_minima_horas: Mapped[int] = mapped_column(Integer, default=2)
    janela_dias: Mapped[int] = mapped_column(Integer, default=14)
