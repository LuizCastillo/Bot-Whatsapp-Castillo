export type Papel = "ADMIN" | "ATENDENTE";
export type Status = "PENDENTE" | "CONFIRMADO" | "REAGENDADO" | "CANCELADO" | "CONCLUIDO" | "NAO_COMPARECEU";
export type Modo = "BOT" | "HUMANO" | "AGUARDANDO_EQUIPE";

export interface User { id: number; nome: string; email: string; papel: Papel }
export interface ClienteMini { id: number; nome: string | null; telefone: string }
export interface Veiculo { id: number; marca: string; modelo: string; ano: number | null; placa: string | null; descricao: string }

export interface Agendamento {
  id: number; avaliacao_id: number; inicio: string; fim: string; status: Status; criado_por: string;
  cliente: ClienteMini; veiculo: Veiculo | null;
  servico_pretendido: string | null; servico_identificado: string | null;
}
export interface Bloqueio { id: number; inicio: string; fim: string; motivo: string | null }
export interface Horario { id: number; dia_semana: number; abre: string; fecha: string }
export interface AgendaConfig { slot_minutos: number; antecedencia_minima_horas: number; janela_dias: number }
export interface AgendaResp { agendamentos: Agendamento[]; bloqueios: Bloqueio[]; horarios: Horario[]; config: AgendaConfig; timezone: string }

export interface Dashboard {
  avaliacoes_hoje: Agendamento[]; proximas_avaliacoes: Agendamento[]; aguardando_acao: Agendamento[];
  novos_clientes_7d: number;
  conversas_aguardando_equipe: { id: number; cliente: ClienteMini; desde: string }[];
}

export interface ClienteDetalhe extends ClienteMini {
  criado_em: string; veiculos: Veiculo[]; agendamentos: Agendamento[];
  conversas: { id: number; modo: Modo; origem: string; estado: string; atualizado_em: string }[];
}

export interface Servico { id: number; slug: string; nome: string; descricao: string; ativo: boolean; ordem: number }
export interface Atendente { id: number; nome: string; email: string; papel: Papel; ativo: boolean; criado_em: string }

export interface Conversa {
  id: number; modo: Modo; origem: string; intencao: string | null; estado: string; atendente_id: number | null;
  atualizado_em: string; criado_em: string; janela_24h_aberta: boolean; cliente: ClienteMini;
  ultima_mensagem?: string | null;
}
export interface Mensagem { id: number; remetente: "CLIENTE" | "BOT" | "ATENDENTE"; tipo: string; conteudo: string; criado_em: string }
export interface ConversaDetalhe extends Conversa { mensagens: Mensagem[] }

export interface Foto { id: number; url: string | null; mime_type: string; tamanho: number; criado_em: string }
export interface Historico {
  agendamento_id: number; status_anterior: string | null; status_novo: string; inicio_anterior: string | null;
  inicio_novo: string | null; motivo: string | null; autor: string; criado_em: string;
}
export interface AvaliacaoDetalhe {
  id: number; status: Status | "RASCUNHO"; cliente: ClienteMini & { criado_em: string }; veiculo: Veiculo | null;
  servico_pretendido: { id: number; nome: string } | null; servico_identificado: { id: number; nome: string } | null;
  descricao_problema: string | null; observacoes_internas: string | null; conversa_id: number | null; criado_em: string;
  agendamentos: Agendamento[]; fotos: Foto[]; historico: Historico[];
}
