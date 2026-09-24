import Link from "next/link";
import type { Agendamento } from "@/lib/types";
import { fmtDate, fmtTime } from "@/lib/format";
import { StatusBadge } from "@/components/ui/badge";

export function AppointmentRow({ ag, showDate = false, action }: { ag: Agendamento; showDate?: boolean; action?: React.ReactNode }) {
  return (
    <li className="flex items-center gap-4 px-5 py-3">
      <div className="w-16 shrink-0 text-right">
        <p className="tabular text-sm font-semibold">{fmtTime(ag.inicio)}</p>
        {showDate && <p className="tabular text-xs text-muted-foreground">{fmtDate(ag.inicio).slice(0, 5)}</p>}
      </div>
      <Link href={`/avaliacoes/${ag.avaliacao_id}`} className="min-w-0 flex-1 rounded-sm">
        <p className="truncate text-sm font-medium">{ag.cliente.nome ?? "Cliente sem nome"}</p>
        <p className="truncate text-xs text-muted-foreground">
          {ag.veiculo?.descricao ?? "Veículo não informado"} · {ag.servico_identificado ?? ag.servico_pretendido ?? "Serviço a definir"}
        </p>
      </Link>
      <StatusBadge status={ag.status} />
      {action}
    </li>
  );
}
