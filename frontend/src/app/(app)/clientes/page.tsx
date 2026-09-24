"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { Search } from "lucide-react";
import { fetcher } from "@/lib/api";
import { fmtDate, fmtPhone } from "@/lib/format";
import type { ClienteMini } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, PageHeader } from "@/components/ui/blocks";
import { Input } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

const PAGE = 20;

export default function ClientesPage() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [offset, setOffset] = useState(0);
  useEffect(() => { const t = setTimeout(() => { setDebounced(q); setOffset(0); }, 300); return () => clearTimeout(t); }, [q]);
  const { data, isLoading } = useSWR<{ total: number; items: (ClienteMini & { criado_em: string })[] }>(
    `clientes?limit=${PAGE}&offset=${offset}&q=${encodeURIComponent(debounced)}`, fetcher, { keepPreviousData: true });

  return (
    <>
      <PageHeader title="Clientes" subtitle="Busque por nome, telefone ou placa do veículo." />
      <div className="relative mb-4 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground" aria-hidden />
        <Input aria-label="Buscar clientes" placeholder="Nome, telefone ou placa…" className="pl-9" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <Card>
        {!data && isLoading ? <p className="p-6 text-sm text-muted-foreground">Carregando…</p> : data && data.items.length === 0 ? (
          <EmptyState title="Nenhum cliente encontrado" hint="Clientes são criados automaticamente quando alguém fala com o bot." />
        ) : (
          <Table>
            <THead><tr><TH>Nome</TH><TH>Telefone</TH><TH className="hidden sm:table-cell">Cliente desde</TH></tr></THead>
            <TBody>
              {data?.items.map((c) => (
                <TR key={c.id}>
                  <TD><Link href={`/clientes/${c.id}`} className="font-medium hover:underline">{c.nome ?? <span className="text-muted-foreground">Sem nome</span>}</Link></TD>
                  <TD className="tabular">{fmtPhone(c.telefone)}</TD>
                  <TD className="tabular hidden text-muted-foreground sm:table-cell">{fmtDate(c.criado_em)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
      {data && data.total > PAGE && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span className="tabular">{offset + 1}–{Math.min(offset + PAGE, data.total)} de {data.total}</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Anterior</Button>
            <Button size="sm" variant="outline" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>Próxima</Button>
          </div>
        </div>
      )}
    </>
  );
}
