"use client";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { fmtPhone, timeAgo } from "@/lib/format";
import type { Conversa, Modo } from "@/lib/types";
import { ModoBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState, PageHeader } from "@/components/ui/blocks";
import { cn } from "@/lib/utils";

const FILTERS: { value: "" | Modo; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "AGUARDANDO_EQUIPE", label: "Aguardando equipe" },
  { value: "HUMANO", label: "Com a equipe" },
  { value: "BOT", label: "Automático" },
];

export default function ConversasPage() {
  const [modo, setModo] = useState<"" | Modo>("");
  const { data, isLoading } = useSWR<{ items: Conversa[] }>(`conversas?limit=100${modo ? `&modo=${modo}` : ""}`, fetcher, { refreshInterval: 15000, keepPreviousData: true });

  return (
    <>
      <PageHeader title="Conversas" subtitle="Quando o bot passa o atendimento, ele para de responder até a equipe devolver." />
      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Filtrar por modo">
        {FILTERS.map((f) => (
          <button key={f.value} role="tab" aria-selected={modo === f.value} onClick={() => setModo(f.value)}
            className={cn("rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors", modo === f.value ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-muted")}>
            {f.label}
          </button>
        ))}
      </div>
      <Card>
        {isLoading && !data ? <p className="p-6 text-sm text-muted-foreground">Carregando…</p> : !data || data.items.length === 0 ? (
          <EmptyState title="Nenhuma conversa" />
        ) : (
          <ul className="divide-y">
            {data.items.map((c) => (
              <li key={c.id}>
                <Link href={`/conversas/${c.id}`} className="flex items-center gap-4 px-5 py-4 hover:bg-muted/40">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{c.cliente.nome ?? fmtPhone(c.cliente.telefone)}</p>
                    <p className="truncate text-xs text-muted-foreground">{c.ultima_mensagem ?? "Sem mensagens"}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    <ModoBadge modo={c.modo} />
                    <span className="text-xs text-muted-foreground">{timeAgo(c.atualizado_em)}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
