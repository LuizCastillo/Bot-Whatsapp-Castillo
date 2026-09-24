"use client";
import Link from "next/link";
import useSWR from "swr";
import { CalendarCheck, Clock, MessageSquare, UserPlus } from "lucide-react";
import { api, fetcher } from "@/lib/api";
import { dayLabelLong, timeAgo, todayISO } from "@/lib/format";
import type { Dashboard } from "@/lib/types";
import { AppointmentRow } from "@/components/appointment-row";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, PageHeader } from "@/components/ui/blocks";
import { Skeleton } from "@/components/ui/skeleton";

function Stat({ label, value, icon: Icon, href }: { label: string; value: number; icon: typeof Clock; href?: string }) {
  const body = (
    <Card className="p-5 transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="size-4 text-primary" aria-hidden />
      </div>
      <p className="tabular mt-2 text-3xl font-semibold tracking-tight">{value}</p>
    </Card>
  );
  return href ? <Link href={href} className="block rounded-lg">{body}</Link> : body;
}

export default function DashboardPage() {
  const { data, mutate, isLoading } = useSWR<Dashboard>("dashboard", fetcher, { refreshInterval: 60000 });

  async function confirm(id: number) {
    await api(`agenda/agendamentos/${id}`, { method: "PATCH", body: { status: "CONFIRMADO" } });
    mutate();
  }

  if (isLoading || !data) {
    return (<><PageHeader title="Dashboard" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div></>);
  }

  return (
    <>
      <PageHeader title="Dashboard" subtitle={dayLabelLong(todayISO())} actions={<Button asChild><Link href="/agenda">Abrir agenda</Link></Button>} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Avaliações hoje" value={data.avaliacoes_hoje.length} icon={CalendarCheck} href="/agenda" />
        <Stat label="Aguardando ação" value={data.aguardando_acao.length} icon={Clock} href="/avaliacoes?status=PENDENTE" />
        <Stat label="Conversas aguardando equipe" value={data.conversas_aguardando_equipe.length} icon={MessageSquare} href="/conversas" />
        <Stat label="Novos clientes (7 dias)" value={data.novos_clientes_7d} icon={UserPlus} href="/clientes" />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Avaliações de hoje</CardTitle></CardHeader>
          {data.avaliacoes_hoje.length === 0 ? <EmptyState title="Nada agendado para hoje" /> : (
            <ul className="divide-y">{data.avaliacoes_hoje.map((a) => <AppointmentRow key={a.id} ag={a} />)}</ul>
          )}
        </Card>

        <Card>
          <CardHeader><CardTitle>Aguardando ação da equipe</CardTitle></CardHeader>
          {data.aguardando_acao.length === 0 ? <EmptyState title="Tudo em dia" hint="Avaliações pendentes de confirmação aparecem aqui." /> : (
            <ul className="divide-y">
              {data.aguardando_acao.map((a) => (
                <AppointmentRow key={a.id} ag={a} showDate action={<Button size="sm" onClick={() => confirm(a.id)}>Confirmar</Button>} />
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader><CardTitle>Próximas avaliações (7 dias)</CardTitle></CardHeader>
          {data.proximas_avaliacoes.length === 0 ? <EmptyState title="Sem avaliações nos próximos dias" /> : (
            <ul className="divide-y">{data.proximas_avaliacoes.map((a) => <AppointmentRow key={a.id} ag={a} showDate />)}</ul>
          )}
        </Card>

        <Card>
          <CardHeader><CardTitle>Conversas aguardando a equipe</CardTitle></CardHeader>
          {data.conversas_aguardando_equipe.length === 0 ? <EmptyState title="Nenhuma conversa esperando" /> : (
            <ul className="divide-y">
              {data.conversas_aguardando_equipe.map((c) => (
                <li key={c.id}>
                  <Link href={`/conversas/${c.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-muted/40">
                    <span className="text-sm font-medium">{c.cliente.nome ?? c.cliente.telefone}</span>
                    <span className="text-xs text-muted-foreground">{timeAgo(c.desde)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
