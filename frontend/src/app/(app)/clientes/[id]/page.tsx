"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api, errMsg, fetcher } from "@/lib/api";
import { fmtDateTime, fmtPhone, timeAgo } from "@/lib/format";
import type { ClienteDetalhe, Veiculo } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge, ModoBadge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { EmptyState, ErrorNote, PageHeader } from "@/components/ui/blocks";
import { Field, Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export default function ClienteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, mutate } = useSWR<ClienteDetalhe>(`clientes/${id}`, fetcher);
  const [editName, setEditName] = useState(false);
  const [vehicle, setVehicle] = useState<Partial<Veiculo> | null>(null);

  if (!data) return <Skeleton className="h-40" />;

  async function removeVehicle(v: Veiculo) {
    if (!confirm(`Remover ${v.descricao}? Avaliações antigas são mantidas.`)) return;
    await api(`veiculos/${v.id}`, { method: "DELETE" });
    mutate();
  }

  return (
    <>
      <PageHeader title={data.nome ?? "Cliente sem nome"} subtitle={fmtPhone(data.telefone)}
        actions={<Button variant="outline" onClick={() => setEditName(true)}><Pencil /> Editar dados</Button>} />

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Veículos</CardTitle>
            <Button size="sm" variant="outline" onClick={() => setVehicle({})}><Plus /> Adicionar</Button>
          </CardHeader>
          {data.veiculos.length === 0 ? <EmptyState title="Nenhum veículo cadastrado" /> : (
            <ul className="divide-y">
              {data.veiculos.map((v) => (
                <li key={v.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <div>
                    <p className="text-sm font-medium">{v.marca} {v.modelo}</p>
                    <p className="tabular text-xs text-muted-foreground">{[v.ano, v.placa].filter(Boolean).join(" · ") || "Sem ano/placa"}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" aria-label={`Editar ${v.descricao}`} onClick={() => setVehicle(v)}><Pencil /></Button>
                    <Button size="icon" variant="ghost" aria-label={`Remover ${v.descricao}`} onClick={() => removeVehicle(v)}><Trash2 /></Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader><CardTitle>Conversas</CardTitle></CardHeader>
          {data.conversas.length === 0 ? <EmptyState title="Sem conversas" /> : (
            <ul className="divide-y">
              {data.conversas.map((c) => (
                <li key={c.id}>
                  <Link href={`/conversas/${c.id}`} className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-muted/40">
                    <div className="text-sm">
                      <span className="font-medium">{c.origem === "SITE" ? "Veio pelo site" : "Direto no WhatsApp"}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{timeAgo(c.atualizado_em)}</span>
                    </div>
                    <ModoBadge modo={c.modo} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader><CardTitle>Histórico de avaliações</CardTitle></CardHeader>
          {data.agendamentos.length === 0 ? <EmptyState title="Nenhuma avaliação ainda" /> : (
            <ul className="divide-y">
              {data.agendamentos.map((a) => (
                <li key={a.id}>
                  <Link href={`/avaliacoes/${a.avaliacao_id}`} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 hover:bg-muted/40">
                    <div>
                      <p className="tabular text-sm font-medium">{fmtDateTime(a.inicio)}</p>
                      <p className="text-xs text-muted-foreground">{a.veiculo?.descricao ?? "Veículo não informado"} · {a.servico_identificado ?? a.servico_pretendido ?? "Serviço a definir"}</p>
                    </div>
                    <StatusBadge status={a.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <NameDialog open={editName} initial={data.nome ?? ""} onClose={() => setEditName(false)} clienteId={data.id} onSaved={() => { setEditName(false); mutate(); }} />
      <VehicleDialog vehicle={vehicle} clienteId={data.id} onClose={() => setVehicle(null)} onSaved={() => { setVehicle(null); mutate(); }} />
    </>
  );
}

function NameDialog({ open, initial, clienteId, onClose, onSaved }: { open: boolean; initial: string; clienteId: number; onClose: () => void; onSaved: () => void }) {
  const [nome, setNome] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  async function save() {
    try { await api(`clientes/${clienteId}`, { method: "PATCH", body: { nome } }); onSaved(); } catch (e) { setError(errMsg(e)); }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Editar cliente">
        <div className="space-y-4"><ErrorNote message={error} />
          <Field label="Nome" htmlFor="cn"><Input id="cn" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={120} /></Field>
          <p className="text-xs text-muted-foreground">O telefone é a identificação do cliente no WhatsApp e não pode ser alterado.</p>
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Cancelar</Button><Button onClick={save} disabled={nome.trim().length < 2}>Salvar</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function VehicleDialog({ vehicle, clienteId, onClose, onSaved }: { vehicle: Partial<Veiculo> | null; clienteId: number; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ marca: "", modelo: "", ano: "", placa: "" });
  const [error, setError] = useState<string | null>(null);
  const [key, setKey] = useState<unknown>(null);
  if (vehicle !== key) { setKey(vehicle); setError(null); setF({ marca: vehicle?.marca ?? "", modelo: vehicle?.modelo ?? "", ano: vehicle?.ano ? String(vehicle.ano) : "", placa: vehicle?.placa ?? "" }); }
  const editing = !!vehicle?.id;
  async function save() {
    const body = { marca: f.marca, modelo: f.modelo, ano: f.ano ? Number(f.ano) : null, placa: f.placa || null };
    try {
      await api(editing ? `veiculos/${vehicle!.id}` : `clientes/${clienteId}/veiculos`, { method: editing ? "PATCH" : "POST", body });
      onSaved();
    } catch (e) { setError(errMsg(e)); }
  }
  return (
    <Dialog open={vehicle !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title={editing ? "Editar veículo" : "Novo veículo"}>
        <div className="grid gap-4 sm:grid-cols-2">
          <ErrorNote message={error} className="sm:col-span-2" />
          <Field label="Marca" htmlFor="vm"><Input id="vm" value={f.marca} onChange={(e) => setF({ ...f, marca: e.target.value })} /></Field>
          <Field label="Modelo" htmlFor="vmo"><Input id="vmo" value={f.modelo} onChange={(e) => setF({ ...f, modelo: e.target.value })} /></Field>
          <Field label="Ano" htmlFor="va"><Input id="va" inputMode="numeric" value={f.ano} onChange={(e) => setF({ ...f, ano: e.target.value.replace(/\D/g, "").slice(0, 4) })} /></Field>
          <Field label="Placa" htmlFor="vp" hint="ABC1234 ou ABC1D23"><Input id="vp" value={f.placa} onChange={(e) => setF({ ...f, placa: e.target.value.toUpperCase() })} maxLength={8} /></Field>
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Cancelar</Button><Button onClick={save} disabled={!f.marca.trim() || !f.modelo.trim()}>Salvar</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
