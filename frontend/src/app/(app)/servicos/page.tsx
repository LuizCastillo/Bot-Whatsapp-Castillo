"use client";
import { useState } from "react";
import useSWR from "swr";
import { Pencil } from "lucide-react";
import { api, errMsg, fetcher } from "@/lib/api";
import type { Servico, User } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { ErrorNote, PageHeader } from "@/components/ui/blocks";
import { Field, Input, Textarea } from "@/components/ui/input";

export default function ServicosPage() {
  const { data, mutate } = useSWR<{ items: Servico[] }>("servicos", fetcher);
  const { data: me } = useSWR<User>("auth/me", fetcher);
  const admin = me?.papel === "ADMIN";
  const [edit, setEdit] = useState<Servico | null>(null);
  const [f, setF] = useState({ nome: "", descricao: "", ordem: "0", ativo: true });
  const [error, setError] = useState<string | null>(null);

  function open(s: Servico) { setEdit(s); setError(null); setF({ nome: s.nome, descricao: s.descricao, ordem: String(s.ordem), ativo: s.ativo }); }
  async function save() {
    try { await api(`servicos/${edit!.id}`, { method: "PATCH", body: { nome: f.nome, descricao: f.descricao, ordem: Number(f.ordem), ativo: f.ativo } }); setEdit(null); mutate(); } catch (e) { setError(errMsg(e)); }
  }

  return (
    <>
      <PageHeader title="Serviços" subtitle={admin ? "Serviços desativados deixam de aparecer para o cliente no WhatsApp." : "Somente administradores podem editar os serviços."} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.items.map((s) => (
          <Card key={s.id} className="flex flex-col p-5">
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-semibold tracking-tight">{s.nome}</h2>
              <Badge className={s.ativo ? "bg-emerald-100 text-emerald-900 ring-emerald-300" : ""}>{s.ativo ? "Ativo" : "Inativo"}</Badge>
            </div>
            <p className="mt-2 flex-1 text-sm text-muted-foreground">{s.descricao}</p>
            <div className="mt-4 flex items-center justify-between">
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{s.slug}</code>
              {admin && <Button size="sm" variant="outline" onClick={() => open(s)}><Pencil /> Editar</Button>}
            </div>
          </Card>
        ))}
      </div>
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent title="Editar serviço" description="O identificador (slug) é usado pelo site e não pode ser alterado.">
          <div className="space-y-4">
            <ErrorNote message={error} />
            <Field label="Nome" htmlFor="sn"><Input id="sn" value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} maxLength={80} /></Field>
            <Field label="Descrição" htmlFor="sd"><Textarea id="sd" value={f.descricao} onChange={(e) => setF({ ...f, descricao: e.target.value })} maxLength={1000} /></Field>
            <Field label="Ordem no menu" htmlFor="so"><Input id="so" type="number" min={0} max={999} value={f.ordem} onChange={(e) => setF({ ...f, ordem: e.target.value })} /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-[hsl(var(--primary))]" checked={f.ativo} onChange={(e) => setF({ ...f, ativo: e.target.checked })} /> Serviço ativo</label>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setEdit(null)}>Cancelar</Button><Button onClick={save} disabled={f.nome.trim().length < 2}>Salvar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
