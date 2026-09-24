"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { fmtDate, fmtTime, STATUS } from "@/lib/format";
import type { Agendamento, Status } from "@/lib/types";
import { StatusBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState, PageHeader } from "@/components/ui/blocks";
import { Field, Input, Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

function List() {
  const params = useSearchParams();
  const [status, setStatus] = useState<string>(params.get("status") ?? "");
  const [data, setData] = useState("");
  const qs = new URLSearchParams({ limit: "100" });
  if (status) qs.set("status", status);
  if (data) qs.set("data", data);
  const { data: res, isLoading } = useSWR<{ items: Agendamento[] }>(`avaliacoes?${qs}`, fetcher, { keepPreviousData: true });

  return (
    <>
      <PageHeader title="Avaliações" subtitle="Avaliações presenciais agendadas pelo bot ou pela equipe." />
      <div className="mb-4 flex flex-wrap gap-4">
        <Field label="Situação" htmlFor="fs">
          <Select id="fs" className="w-52" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todas</option>
            {(Object.keys(STATUS) as (Status | "RASCUNHO")[]).filter((s) => s !== "RASCUNHO").map((s) => <option key={s} value={s}>{STATUS[s].label}</option>)}
          </Select>
        </Field>
        <Field label="Data" htmlFor="fd"><Input id="fd" type="date" className="w-44" value={data} onChange={(e) => setData(e.target.value)} /></Field>
      </div>
      <Card>
        {isLoading && !res ? <p className="p-6 text-sm text-muted-foreground">Carregando…</p> : !res || res.items.length === 0 ? (
          <EmptyState title="Nenhuma avaliação encontrada" hint="Ajuste os filtros ou aguarde novos agendamentos." />
        ) : (
          <Table>
            <THead><tr><TH>Data</TH><TH>Cliente</TH><TH className="hidden md:table-cell">Veículo</TH><TH className="hidden lg:table-cell">Serviço</TH><TH>Situação</TH></tr></THead>
            <TBody>
              {res.items.map((a) => (
                <TR key={a.id}>
                  <TD className="tabular whitespace-nowrap"><Link href={`/avaliacoes/${a.avaliacao_id}`} className="font-medium hover:underline">{fmtDate(a.inicio)} · {fmtTime(a.inicio)}</Link></TD>
                  <TD>{a.cliente.nome ?? a.cliente.telefone}</TD>
                  <TD className="hidden md:table-cell">{a.veiculo?.descricao ?? "—"}</TD>
                  <TD className="hidden lg:table-cell">{a.servico_identificado ?? a.servico_pretendido ?? "A definir"}</TD>
                  <TD><StatusBadge status={a.status} /></TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </>
  );
}

export default function AvaliacoesPage() {
  return <Suspense><List /></Suspense>;
}
