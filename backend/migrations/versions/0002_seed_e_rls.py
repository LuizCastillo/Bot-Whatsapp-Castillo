"""seed dos serviços, agenda padrão e RLS

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SERVICOS = [
    ("funilaria", "Funilaria", "Reparo de amassados e deformações na lataria do veículo."),
    ("recuperacao-de-colisoes", "Recuperação de Colisões", "Recuperação estrutural e estética após colisões."),
    ("pintura-geral", "Pintura Geral / Completa", "Pintura completa do veículo."),
    ("pintura-localizada", "Pintura Localizada", "Pintura de partes específicas da carroceria."),
    ("preparo-de-superficie", "Preparo de Superfície", "Preparação da superfície para receber a pintura."),
    ("polimento-automotivo", "Polimento Automotivo", "Polimento para recuperar o brilho e reduzir riscos superficiais."),
    ("polimento-de-farois", "Polimento de Faróis", "Recuperação da transparência de faróis opacos."),
    ("substituicao-de-pecas", "Substituição de Peças", "Troca de peças da carroceria."),
    ("revitalizacao-de-para-choques", "Revitalização de Para-choques", "Recuperação estética de para-choques."),
]

TABLES = [
    "clientes", "veiculos", "servicos", "atendentes", "sessoes", "conversas", "mensagens",
    "avaliacoes", "agendamentos", "historico_agendamento", "fotos_avaliacao",
    "horarios_funcionamento", "bloqueios", "configuracao_agenda",
]


def upgrade() -> None:
    servicos = sa.table("servicos", sa.column("slug", sa.String), sa.column("nome", sa.String), sa.column("descricao", sa.Text),
                        sa.column("ativo", sa.Boolean), sa.column("ordem", sa.Integer))
    op.bulk_insert(servicos, [
        {"slug": s, "nome": n, "descricao": d, "ativo": True, "ordem": i + 1}
        for i, (s, n, d) in enumerate(SERVICOS)
    ])
    from datetime import time
    horarios = sa.table("horarios_funcionamento", sa.column("dia_semana", sa.Integer), sa.column("abre", sa.Time), sa.column("fecha", sa.Time))
    rows = []
    for dia in range(5):  # seg-sex
        rows.append({"dia_semana": dia, "abre": time(8, 0), "fecha": time(12, 0)})
        rows.append({"dia_semana": dia, "abre": time(13, 0), "fecha": time(17, 0)})
    rows.append({"dia_semana": 5, "abre": time(8, 0), "fecha": time(12, 0)})  # sábado
    op.bulk_insert(horarios, rows)
    cfg = sa.table("configuracao_agenda", sa.column("id", sa.Integer), sa.column("slot_minutos", sa.Integer),
                   sa.column("antecedencia_minima_horas", sa.Integer), sa.column("janela_dias", sa.Integer))
    op.bulk_insert(cfg, [{"id": 1, "slot_minutos": 60, "antecedencia_minima_horas": 2, "janela_dias": 14}])

    # Somente o backend acessa o banco (role de serviço ignora RLS); bloqueia a API pública.
    if op.get_bind().dialect.name == "postgresql":
        for t in TABLES:
            op.execute(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for t in TABLES:
            op.execute(f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY')
    op.execute("DELETE FROM servicos")
    op.execute("DELETE FROM horarios_funcionamento")
    op.execute("DELETE FROM configuracao_agenda")
