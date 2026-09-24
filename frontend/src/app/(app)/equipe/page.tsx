"use client";
import { useState } from "react";
import useSWR from "swr";
import { Plus } from "lucide-react";
import { api, errMsg, fetcher } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import type { Atendente, Papel, User } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { ErrorNote, PageHeader } from "@/components/ui/blocks";
import { Field, Input, Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

type Form = { id?: number; nome: string; email: string; senha: string; papel: Papel; ativo: boolean };
const EMPTY: Form = { nome: "", email: "", senha: "", papel: "ATENDENTE", ativo: true };

export default function EquipePage() {
  const { data: me } = useSWR<User>("auth/me", fetcher);
  const admin = me?.papel === "ADMIN";
  const { data, mutate } = useSWR<{ items: Atendente[] }>(admin ? "equipe" : null, fetcher);
  const [form, setForm] = useState<Form | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (me && !admin) return <p className="text-sm text-muted-foreground">Apenas administradores acessam esta área.</p>;

  async function save() {
    if (!form) return;
    setError(null);
    try {
      if (form.id) {
        await api(`equipe/${form.id}`, { method: "PATCH", body: { nome: form.nome, papel: form.papel, ativo: form.ativo, senha: form.senha || undefined } });
      } else {
        await api("equipe", { method: "POST", body: { nome: form.nome, email: form.email, senha: form.senha, papel: form.papel } });
      }
      setForm(null); mutate();
    } catch (e) { setError(errMsg(e)); }
  }

  return (
    <>
      <PageHeader title="Equipe" subtitle="Quem pode acessar o painel." actions={<Button onClick={() => { setError(null); setForm(EMPTY); }}><Plus /> Novo usuário</Button>} />
      <Card>
        <Table>
          <THead><tr><TH>Nome</TH><TH className="hidden sm:table-cell">E-mail</TH><TH>Papel</TH><TH>Situação</TH><TH className="hidden md:table-cell">Desde</TH><TH><span className="sr-only">Ações</span></TH></tr></THead>
          <TBody>
            {data?.items.map((a) => (
              <TR key={a.id}>
                <TD className="font-medium">{a.nome}</TD>
                <TD className="hidden sm:table-cell">{a.email}</TD>
                <TD>{a.papel === "ADMIN" ? "Administrador" : "Atendente"}</TD>
                <TD><Badge className={a.ativo ? "bg-emerald-100 text-emerald-900 ring-emerald-300" : "bg-zinc-200 text-zinc-700 ring-zinc-300"}>{a.ativo ? "Ativo" : "Inativo"}</Badge></TD>
                <TD className="tabular hidden text-muted-foreground md:table-cell">{fmtDate(a.criado_em)}</TD>
                <TD className="text-right"><Button size="sm" variant="outline" onClick={() => { setError(null); setForm({ id: a.id, nome: a.nome, email: a.email, senha: "", papel: a.papel, ativo: a.ativo }); }}>Editar</Button></TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Card>
      <Dialog open={!!form} onOpenChange={(o) => !o && setForm(null)}>
        <DialogContent title={form?.id ? "Editar usuário" : "Novo usuário"} description={form?.id ? "Desativar ou trocar a senha encerra as sessões abertas do usuário." : undefined}>
          {form && (
            <div className="space-y-4">
              <ErrorNote message={error} />
              <Field label="Nome" htmlFor="en"><Input id="en" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} /></Field>
              <Field label="E-mail" htmlFor="ee"><Input id="ee" type="email" disabled={!!form.id} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
              <Field label={form.id ? "Nova senha (deixe em branco para manter)" : "Senha"} htmlFor="es" hint="Mínimo de 10 caracteres."><Input id="es" type="password" autoComplete="new-password" value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} /></Field>
              <Field label="Papel" htmlFor="ep">
                <Select id="ep" value={form.papel} onChange={(e) => setForm({ ...form, papel: e.target.value as Papel })}>
                  <option value="ATENDENTE">Atendente</option><option value="ADMIN">Administrador</option>
                </Select>
              </Field>
              {form.id && <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-[hsl(var(--primary))]" checked={form.ativo} onChange={(e) => setForm({ ...form, ativo: e.target.checked })} /> Usuário ativo</label>}
            </div>
          )}
          <DialogFooter><Button variant="outline" onClick={() => setForm(null)}>Cancelar</Button><Button onClick={save} disabled={!form || form.nome.trim().length < 2 || (!form.id && (!form.email || form.senha.length < 10))}>Salvar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
