"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import { api, errMsg, fetcher } from "@/lib/api";
import { fmtDateTime, fmtPhone, STATUS } from "@/lib/format";
import type { AvaliacaoDetalhe, Servico, Status } from "@/lib/types";
import { AppointmentActions } from "@/components/appointment-actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EmptyState, ErrorNote, PageHeader } from "@/components/ui/blocks";
import { Field, Select, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const Row = ({ k, children }: { k: string; children: React.ReactNode }) => (
  <div className="flex justify-between gap-4 py-2 text-sm"><dt className="text-muted-foreground">{k}</dt><dd className="text-right font-medium">{children}</dd></div>
);

export default function AvaliacaoPage() {
  const { id } = useParams<{ id: string }>();
  const { data, mutate } = useSWR<AvaliacaoDetalhe>(`avaliacoes/${id}`, fetcher);
  const { data: servicos } = useSWR<{ items: Servico[] }>("servicos", fetcher);
  const [ident, setIdent] = useState<string | null>(null);
  const [obs, setObs] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [zoom, setZoom] = useState<string | null>(null);

  if (!data) return <Skeleton className="h-48" />;
  const identValue = ident ?? (data.servico_identificado ? String(data.servico_identificado.id) : "");
  const obsValue = obs ?? data.observacoes_internas ?? "";
  const current = data.agendamentos[0];
  const active = data.agendamentos.find((a) => ["PENDENTE", "CONFIRMADO", "REAGENDADO"].includes(a.status)) ?? current;

  async function save() {
    setSaving(true); setError(null); setSaved(false);
    try {
      await api(`avaliacoes/${id}`, { method: "PATCH", body: { servico_identificado_id: identValue ? Number(identValue) : null, observacoes_internas: obsValue } });
      setIdent(null); setObs(null); setSaved(true); mutate();
    } catch (e) { setError(errMsg(e)); } finally { setSaving(false); }
  }

  return (
    <>
      <PageHeader title={`Avaliação #${data.id}`} subtitle={active ? fmtDateTime(active.inicio) : "Ainda sem horário definido"} actions={<StatusBadge status={data.status} />} />

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <CardHeader><CardTitle>Atendimento</CardTitle></CardHeader>
            <CardContent>
              <dl className="divide-y">
                <Row k="Cliente"><Link href={`/clientes/${data.cliente.id}`} className="hover:underline">{data.cliente.nome ?? "Sem nome"}</Link> · <span className="tabular">{fmtPhone(data.cliente.telefone)}</span></Row>
                <Row k="Veículo">{data.veiculo?.descricao ?? "Não informado"}</Row>
                <Row k="Serviço pretendido">{data.servico_pretendido?.nome ?? "A definir na avaliação"}</Row>
                {data.conversa_id && <Row k="Conversa"><Link href={`/conversas/${data.conversa_id}`} className="text-primary hover:underline">Ver conversa</Link></Row>}
              </dl>
              <div className="mt-4">
                <p className="text-sm text-muted-foreground">Descrição do problema</p>
                <p className="mt-1 whitespace-pre-wrap text-sm">{data.descricao_problema ?? "Não informada."}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Fotos enviadas pelo cliente</CardTitle></CardHeader>
            {data.fotos.length === 0 ? <EmptyState title="Nenhuma foto" hint="Fotos ajudam a equipe a se preparar; não geram orçamento." /> : (
              <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                {data.fotos.map((f) => f.url ? (
                  <button key={f.id} onClick={() => setZoom(f.url)} className="group aspect-square overflow-hidden rounded-md border bg-muted">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={f.url} alt={`Foto ${f.id} da avaliação`} className="size-full object-cover transition-transform group-hover:scale-105" loading="lazy" />
                  </button>
                ) : <div key={f.id} className="grid aspect-square place-items-center rounded-md border text-xs text-muted-foreground">Indisponível</div>)}
              </CardContent>
            )}
          </Card>

          <Card>
            <CardHeader><CardTitle>Histórico</CardTitle></CardHeader>
            {data.historico.length === 0 ? <EmptyState title="Sem registros" /> : (
              <ul className="divide-y">
                {data.historico.map((h, i) => (
                  <li key={i} className="px-5 py-3 text-sm">
                    <p className="font-medium">
                      {h.status_anterior ? `${STATUS[h.status_anterior as Status]?.label ?? h.status_anterior} → ` : ""}{STATUS[h.status_novo as Status]?.label ?? h.status_novo}
                      {h.inicio_anterior && h.inicio_novo && h.inicio_anterior !== h.inicio_novo && <span className="tabular font-normal text-muted-foreground"> · {fmtDateTime(h.inicio_anterior)} → {fmtDateTime(h.inicio_novo)}</span>}
                    </p>
                    <p className="text-xs text-muted-foreground">{fmtDateTime(h.criado_em)} · {h.autor === "BOT" ? "Bot" : h.autor.startsWith("atendente") ? "Equipe" : h.autor}{h.motivo ? ` · ${h.motivo}` : ""}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          {active && (
            <Card>
              <CardHeader><CardTitle>Agendamento</CardTitle><StatusBadge status={active.status} /></CardHeader>
              <CardContent className="space-y-4">
                <p className="tabular text-lg font-semibold">{fmtDateTime(active.inicio)}</p>
                <AppointmentActions ag={active} onChanged={mutate} />
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader><CardTitle>Classificação interna</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <ErrorNote message={error} />
              <Field label="Serviço identificado pela equipe" htmlFor="si" hint="Apenas classifica o atendimento. Não é orçamento.">
                <Select id="si" value={identValue} onChange={(e) => setIdent(e.target.value)}>
                  <option value="">Ainda não identificado</option>
                  {servicos?.items.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                </Select>
              </Field>
              <Field label="Observações internas" htmlFor="ob"><Textarea id="ob" value={obsValue} onChange={(e) => setObs(e.target.value)} maxLength={4000} /></Field>
              <Button onClick={save} disabled={saving || (ident === null && obs === null)}>{saving ? "Salvando…" : "Salvar"}</Button>
              {saved && <p role="status" className="text-xs text-emerald-700">Alterações salvas.</p>}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={!!zoom} onOpenChange={(o) => !o && setZoom(null)}>
        <DialogContent title="Foto do veículo" className="max-w-3xl">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {zoom && <img src={zoom} alt="Foto ampliada do veículo" className="max-h-[70vh] w-full rounded-md object-contain" />}
        </DialogContent>
      </Dialog>
    </>
  );
}
