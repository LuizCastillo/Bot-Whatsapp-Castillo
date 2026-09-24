from datetime import datetime, time

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.database.enums import Papel, StatusAgendamento


class AwareModel(BaseModel):
    @field_validator("inicio", "fim", check_fields=False)
    @classmethod
    def _aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("Informe data/hora com fuso horário (ex.: 2026-09-25T14:00:00-03:00).")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=200)


class ClienteUpdate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)


class VeiculoIn(BaseModel):
    marca: str = Field(min_length=1, max_length=60)
    modelo: str = Field(min_length=1, max_length=80)
    ano: int | None = Field(default=None, ge=1950, le=2100)
    placa: str | None = Field(default=None, max_length=8)


class VeiculoUpdate(BaseModel):
    marca: str | None = Field(default=None, min_length=1, max_length=60)
    modelo: str | None = Field(default=None, min_length=1, max_length=80)
    ano: int | None = Field(default=None, ge=1950, le=2100)
    placa: str | None = Field(default=None, max_length=8)


class AgendamentoCreate(AwareModel):
    cliente_id: int
    veiculo_id: int | None = None
    servico_id: int | None = None
    inicio: datetime
    descricao: str | None = Field(default=None, max_length=1000)
    status: StatusAgendamento = StatusAgendamento.CONFIRMADO


class AgendamentoUpdate(AwareModel):
    status: StatusAgendamento | None = None
    inicio: datetime | None = None
    motivo: str | None = Field(default=None, max_length=300)


class BloqueioIn(AwareModel):
    inicio: datetime
    fim: datetime
    motivo: str | None = Field(default=None, max_length=200)


class ConfigAgendaIn(BaseModel):
    slot_minutos: int = Field(ge=15, le=240)
    antecedencia_minima_horas: int = Field(ge=0, le=72)
    janela_dias: int = Field(ge=1, le=90)


class HorarioIn(BaseModel):
    dia_semana: int = Field(ge=0, le=6)
    abre: time
    fecha: time


class MensagemIn(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class AvaliacaoUpdate(BaseModel):
    servico_identificado_id: int | None = None
    observacoes_internas: str | None = Field(default=None, max_length=4000)
    descricao_problema: str | None = Field(default=None, max_length=4000)


class ServicoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=1000)
    ativo: bool | None = None
    ordem: int | None = Field(default=None, ge=0, le=999)


class AtendenteCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=10, max_length=200)
    papel: Papel = Papel.ATENDENTE


class AtendenteUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    papel: Papel | None = None
    ativo: bool | None = None
    senha: str | None = Field(default=None, min_length=10, max_length=200)
