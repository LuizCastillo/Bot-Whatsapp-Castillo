"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { Send } from "lucide-react";
import { api, errMsg, fetcher } from "@/lib/api";
import { fmtPhone, fmtTime, fmtDate } from "@/lib/format";
import type { ConversaDetalhe } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ModoBadge } from "@/components/ui/badge";
import { ErrorNote, PageHeader } from "@/components/ui/blocks";
import { Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const WHO = { CLIENTE: "Cliente", BOT: "Bot", ATENDENTE: "Equipe" } as const;

export default function ConversaPage() {
  const { id } = useParams<{ id: string }>();
  const { data, mutate } = useSWR<ConversaDetalhe>(`conversas/${id}`, fetcher, { refreshInterval: 5000 });
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const count = data?.mensagens.length ?? 0;
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [count]);

  if (!data) return <Skeleton className="h-64" />;

  async function act(path: string) {
    setBusy(true); setError(null);
    try { await api(`conversas/${id}/${path}`, { method: "POST" }); await mutate(); } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  }
  async function send() {
    if (!text.trim()) return;
    setBusy(true); setError(null);
    try { await api(`conversas/${id}/mensagens`, { method: "POST", body: { texto: text.trim() } }); setText(""); await mutate(); } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  }

  const canReply = data.modo === "HUMANO" && data.janela_24h_aberta;
  let lastDay = "";

  return (
    <>
      <PageHeader
        title={data.cliente.nome ?? fmtPhone(data.cliente.telefone)}
        subtitle={fmtPhone(data.cliente.telefone)}
        actions={<>
          <ModoBadge modo={data.modo} />
          <Button variant="outline" asChild><Link href={`/clientes/${data.cliente.id}`}>Ver cliente</Link></Button>
          {data.modo !== "HUMANO" && <Button disabled={busy} onClick={() => act("assumir")}>Assumir conversa</Button>}
          {data.modo !== "BOT" && <Button variant="outline" disabled={busy} onClick={() => act("devolver")}>Retomar atendimento automático</Button>}
        </>}
      />
      <ErrorNote message={error} className="mb-4" />
      <Card className="flex h-[65vh] flex-col overflow-hidden">
        <div className="flex-1 space-y-3 overflow-y-auto bg-muted/40 p-4" aria-live="polite">
          {data.mensagens.map((m) => {
            const day = fmtDate(m.criado_em);
            const sep = day !== lastDay; lastDay = day;
            const mine = m.remetente !== "CLIENTE";
            return (
              <div key={m.id}>
                {sep && <p className="tabular my-2 text-center text-xs text-muted-foreground">{day}</p>}
                <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
                  <div className={cn("max-w-[80%] rounded-lg px-3 py-2 text-sm shadow-sm", m.remetente === "CLIENTE" ? "bg-card" : m.remetente === "BOT" ? "bg-secondary" : "bg-primary text-primary-foreground")}>
                    <p className={cn("mb-0.5 text-[11px] font-semibold uppercase tracking-wide", m.remetente === "ATENDENTE" ? "text-primary-foreground/80" : "text-muted-foreground")}>{WHO[m.remetente]}</p>
                    <p className="whitespace-pre-wrap break-words">{m.tipo === "IMAGE" ? `📷 ${m.conteudo}` : m.conteudo}</p>
                    <p className={cn("tabular mt-1 text-right text-[11px]", m.remetente === "ATENDENTE" ? "text-primary-foreground/80" : "text-muted-foreground")}>{fmtTime(m.criado_em)}</p>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>
        <div className="border-t bg-card p-3">
          {canReply ? (
            <div className="flex items-end gap-2">
              <Textarea aria-label="Mensagem" className="min-h-[44px]" rows={2} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Escreva uma resposta… (Enter envia)" />
              <Button onClick={send} disabled={busy || !text.trim()} aria-label="Enviar"><Send /></Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {data.modo !== "HUMANO" ? "Assuma a conversa para responder pelo painel." : "Passaram mais de 24h desde a última mensagem do cliente: o WhatsApp só permite templates aprovados fora dessa janela."}
            </p>
          )}
        </div>
      </Card>
    </>
  );
}
