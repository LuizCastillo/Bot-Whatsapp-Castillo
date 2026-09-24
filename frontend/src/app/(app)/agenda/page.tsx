"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { ChevronLeft, ChevronRight, Ban, Plus, Settings2 } from "lucide-react";
import { api, errMsg, fetcher } from "@/lib/api";
import { addDays, dayLabelShort, fmtDateTime, fmtTime, hhmmToMinutes, localParts, minutesToHHMM, todayISO, weekStart, zonedToUtc } from "@/lib/format";
import type { AgendaResp, Agendamento, Bloqueio, ClienteDetalhe, ClienteMini, Servico, User } from "@/lib/types";
import { AppointmentActions } from "@/components/appointment-actions";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { ErrorNote, PageHeader } from "@/components/ui/blocks";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const PX_PER_HOUR = 60;
const PPM = PX_PER_HOUR / 60;
const STATUS_BAR: Record<string, string> = {
  PENDENTE: "border-l-amber-500 bg-amber-50", CONFIRMADO: "border-l-emerald-600 bg-emerald-50", REAGENDADO: "border-l-sky-600 bg-sky-50",
  CONCLUIDO: "border-l-indigo-600 bg-indigo-50", NAO_COMPARECEU: "border-l-rose-600 bg-rose-50", CANCELADO: "border-l-zinc-400 bg-zinc-100",
};

export default function AgendaPage() {
  const [start, setStart] = useState(() => weekStart(todayISO()));
  const end = addDays(start, 6);
  const { data, mutate } = useSWR<AgendaResp>(`agenda?inicio=${start}&fim=${end}`, fetcher, { refreshInterval: 30000, keepPreviousData: true });
  const { data: me } = useSWR<User>("auth/me", fetcher);
  const [selected, setSelected] = useState<Agendamento | null>(null);
  const [selBlock, setSelBlock] = useState<Bloqueio | null>(null);
  const [newAt, setNewAt] = useState<{ date: string; time: string } | null>(null);
  const [blockOpen, setBlockOpen] = useState(false);
  const [settings, setSettings] = useState(false);
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(start, i)), [start]);
  const today = todayISO();

  const visible = (data?.agendamentos ?? []).filter((a) => a.status !== "CANCELADO");
  const { startMin, endMin } = useMemo(() => {
    let lo = 8 * 60, hi = 18 * 60;
    if (data?.horarios.length) { lo = Math.min(...data.horarios.map((h) => hhmmToMinutes(h.abre))); hi = Math.max(...data.horarios.map((h) => hhmmToMinutes(h.fecha))); }
    for (const a of visible) { lo = Math.min(lo, localParts(a.inicio).minutes); const e = localParts(a.fim); hi = Math.max(hi, e.minutes === 0 ? 1440 : e.minutes); }
    return { startMin: Math.floor(lo / 60) * 60, endMin: Math.ceil(hi / 60) * 60 };
  }, [data, visible]);
  const hours = Array.from({ length: (endMin - startMin) / 60 }, (_, i) => startMin + i * 60);
  const height = (endMin - startMin) * PPM;
  const nowParts = localParts(new Date().toISOString());

  function clickColumn(e: React.MouseEvent<HTMLDivElement>, day: string) {
    const rect = e.currentTarget.getBoundingClientRect();
    const slot = data?.config.slot_minutos ?? 60;
    const minutes = Math.floor((startMin + (e.clientY - rect.top) / PPM) / slot) * slot;
    setNewAt({ date: day, time: minutesToHHMM(minutes) });
  }

  return (
    <>
      <PageHeader title="Agenda" subtitle="Avaliações presenciais. O bot e o painel usam esta mesma agenda."
        actions={<>
          <Button variant="outline" size="icon" aria-label="Semana anterior" onClick={() => setStart(addDays(start, -7))}><ChevronLeft /></Button>
          <Button variant="outline" onClick={() => setStart(weekStart(today))}>Hoje</Button>
          <Button variant="outline" size="icon" aria-label="Próxima semana" onClick={() => setStart(addDays(start, 7))}><ChevronRight /></Button>
          <Button variant="outline" onClick={() => setBlockOpen(true)}><Ban /> Bloquear</Button>
          <Button onClick={() => setNewAt({ date: today > start ? today : start, time: "" })}><Plus /> Nova avaliação</Button>
          {me?.papel === "ADMIN" && <Button variant="ghost" size="icon" aria-label="Configurar agenda" onClick={() => setSettings(true)}><Settings2 /></Button>}
        </>} />

      <p className="mb-3 text-sm font-medium capitalize text-muted-foreground">{dayLabelShort(start)} — {dayLabelShort(end)}</p>

      <div className="overflow-x-auto rounded-lg border bg-card shadow-sm">
        <div className="min-w-[760px]">
          <div className="grid grid-cols-[3.5rem_repeat(7,1fr)] border-b bg-muted/60">
            <div />
            {days.map((d) => (
              <div key={d} className={cn("px-2 py-2.5 text-center text-xs font-semibold capitalize", d === today && "text-primary")}>
                {dayLabelShort(d)}{d === today && <span className="ml-1.5 inline-block size-1.5 rounded-full bg-primary align-middle" aria-label="hoje" />}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-[3.5rem_repeat(7,1fr)]">
            <div className="relative" style={{ height }}>
              {hours.map((h) => <span key={h} className="tabular absolute right-2 -translate-y-1/2 text-[11px] text-muted-foreground" style={{ top: (h - startMin) * PPM + (h === startMin ? 8 : 0) }}>{minutesToHHMM(h)}</span>)}
            </div>
            {days.map((day, idx) => {
              const wd = idx; // segunda = 0
              const open = (data?.horarios ?? []).filter((h) => h.dia_semana === wd);
              return (
                <div key={day} className="relative cursor-cell border-l bg-muted/70" style={{ height }} onClick={(e) => clickColumn(e, day)} role="gridcell" aria-label={`Dia ${day}`}>
                  {open.map((h) => (
                    <div key={h.id} className="absolute inset-x-0 bg-card" style={{ top: (hhmmToMinutes(h.abre) - startMin) * PPM, height: (hhmmToMinutes(h.fecha) - hhmmToMinutes(h.abre)) * PPM }} />
                  ))}
                  {hours.map((h) => <div key={h} className="pointer-events-none absolute inset-x-0 border-t border-border/70" style={{ top: (h - startMin) * PPM }} />)}

                  {(data?.bloqueios ?? []).map((b) => {
                    const s = localParts(b.inicio), e = localParts(b.fim);
                    if (e.date < day || s.date > day) return null;
                    const from = s.date < day ? 0 : s.minutes, to = e.date > day ? 1440 : e.minutes;
                    if (to <= from) return null;
                    return (
                      <button key={b.id} onClick={(ev) => { ev.stopPropagation(); setSelBlock(b); }} title={b.motivo ?? "Bloqueado"}
                        className="hatch absolute inset-x-0 overflow-hidden border-y border-zinc-400/40 px-1.5 py-0.5 text-left text-[11px] font-medium text-zinc-700"
                        style={{ top: (from - startMin) * PPM, height: (to - from) * PPM }}>
                        <span className="rounded bg-card/80 px-1">{b.motivo ?? "Bloqueado"}</span>
                      </button>
                    );
                  })}

                  {visible.filter((a) => localParts(a.inicio).date === day).map((a) => {
                    const s = localParts(a.inicio), e = localParts(a.fim);
                    const to = e.date > s.date || e.minutes === 0 ? 1440 : e.minutes;
                    return (
                      <button key={a.id} onClick={(ev) => { ev.stopPropagation(); setSelected(a); }}
                        className={cn("absolute inset-x-1 overflow-hidden rounded-md border border-l-4 px-2 py-1 text-left shadow-sm transition-shadow hover:shadow-md", STATUS_BAR[a.status])}
                        style={{ top: (s.minutes - startMin) * PPM + 1, height: Math.max(30, (to - s.minutes) * PPM - 2) }}>
                        <p className="tabular text-[11px] font-semibold leading-tight">{fmtTime(a.inicio)}</p>
                        <p className="truncate text-xs font-medium leading-tight">{a.cliente.nome ?? "Sem nome"}</p>
                        <p className="truncate text-[11px] leading-tight text-muted-foreground">{a.veiculo?.descricao ?? ""}</p>
                      </button>
                    );
                  })}

                  {day === today && nowParts.minutes >= startMin && nowParts.minutes <= endMin && (
                    <div className="pointer-events-none absolute inset-x-0 z-10 border-t-2 border-destructive" style={{ top: (nowParts.minutes - startMin) * PPM }}><span className="absolute -left-1 -top-[5px] size-2 rounded-full bg-destructive" /></div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Clique em um horário livre para criar uma avaliação. Áreas listradas estão bloqueadas; áreas cinza estão fora do expediente.</p>

      <AppointmentDialog ag={selected} onClose={() => setSelected(null)} onChanged={() => { setSelected(null); mutate(); }} />
      <BlockInfoDialog b={selBlock} onClose={() => setSelBlock(null)} onDone={() => { setSelBlock(null); mutate(); }} />
      <NewAppointmentDialog prefill={newAt} onClose={() => setNewAt(null)} onDone={() => { setNewAt(null); mutate(); }} />
      <BlockDialog open={blockOpen} defaultDate={today} onClose={() => setBlockOpen(false)} onDone={() => { setBlockOpen(false); mutate(); }} />
      {data && <SettingsDialog open={settings} data={data} onClose={() => setSettings(false)} onDone={() => { setSettings(false); mutate(); }} />}
    </>
  );
}

function AppointmentDialog({ ag, onClose, onChanged }: { ag: Agendamento | null; onClose: () => void; onChanged: () => void }) {
  return (
    <Dialog open={!!ag} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Avaliação presencial" description={ag ? fmtDateTime(ag.inicio) : undefined}>
        {ag && (
          <div className="space-y-4">
            <div className="flex items-center justify-between"><p className="font-medium">{ag.cliente.nome ?? "Cliente sem nome"}</p><StatusBadge status={ag.status} /></div>
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between"><dt className="text-muted-foreground">Veículo</dt><dd>{ag.veiculo?.descricao ?? "Não informado"}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">Serviço pretendido</dt><dd>{ag.servico_pretendido ?? "A definir"}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">Criado por</dt><dd>{ag.criado_por === "BOT" ? "Bot" : "Equipe"}</dd></div>
            </dl>
            <AppointmentActions ag={ag} onChanged={onChanged} />
            <Button variant="outline" asChild className="w-full"><Link href={`/avaliacoes/${ag.avaliacao_id}`}>Abrir avaliação (fotos, observações, histórico)</Link></Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function BlockInfoDialog({ b, onClose, onDone }: { b: Bloqueio | null; onClose: () => void; onDone: () => void }) {
  const [error, setError] = useState<string | null>(null);
  async function release() { try { await api(`agenda/bloqueios/${b!.id}`, { method: "DELETE" }); onDone(); } catch (e) { setError(errMsg(e)); } }
  return (
    <Dialog open={!!b} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Horário bloqueado" description={b ? `${fmtDateTime(b.inicio)} até ${fmtDateTime(b.fim)}` : undefined}>
        <ErrorNote message={error} />
        <p className="text-sm">{b?.motivo ?? "Sem motivo informado."}</p>
        <DialogFooter><Button variant="outline" onClick={onClose}>Fechar</Button><Button onClick={release}>Liberar horário</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function BlockDialog({ open, defaultDate, onClose, onDone }: { open: boolean; defaultDate: string; onClose: () => void; onDone: () => void }) {
  const [f, setF] = useState({ date: defaultDate, from: "08:00", to: "12:00", motivo: "" });
  const [error, setError] = useState<string | null>(null);
  async function save() {
    try {
      await api("agenda/bloqueios", { method: "POST", body: { inicio: zonedToUtc(f.date, f.from), fim: zonedToUtc(f.date, f.to), motivo: f.motivo || undefined } });
      onDone();
    } catch (e) { setError(errMsg(e)); }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Bloquear horário" description="O bot deixa de oferecer os horários bloqueados.">
        <div className="grid gap-4 sm:grid-cols-3">
          <ErrorNote message={error} className="sm:col-span-3" />
          <Field label="Data" htmlFor="bd"><Input id="bd" type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
          <Field label="Das" htmlFor="bf"><Input id="bf" type="time" value={f.from} onChange={(e) => setF({ ...f, from: e.target.value })} /></Field>
          <Field label="Às" htmlFor="bt"><Input id="bt" type="time" value={f.to} onChange={(e) => setF({ ...f, to: e.target.value })} /></Field>
          <div className="sm:col-span-3"><Field label="Motivo (opcional)" htmlFor="bm"><Input id="bm" value={f.motivo} onChange={(e) => setF({ ...f, motivo: e.target.value })} maxLength={200} /></Field></div>
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Cancelar</Button><Button onClick={save} disabled={!f.date || !f.from || !f.to || f.to <= f.from}>Bloquear</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NewAppointmentDialog({ prefill, onClose, onDone }: { prefill: { date: string; time: string } | null; onClose: () => void; onDone: () => void }) {
  const [q, setQ] = useState("");
  const [client, setClient] = useState<ClienteMini | null>(null);
  const [veiculo, setVeiculo] = useState("");
  const [servico, setServico] = useState("");
  const [date, setDate] = useState("");
  const [slot, setSlot] = useState("");
  const [status, setStatus] = useState("CONFIRMADO");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState<unknown>(null);
  if (prefill !== key) { setKey(prefill); if (prefill) { setQ(""); setClient(null); setVeiculo(""); setServico(""); setDate(prefill.date); setSlot(""); setStatus("CONFIRMADO"); setDesc(""); setError(null); } }

  const open = !!prefill;
  const { data: found } = useSWR<{ items: ClienteMini[] }>(open && !client && q.trim().length >= 2 ? `clientes?limit=5&q=${encodeURIComponent(q.trim())}` : null, fetcher);
  const { data: detail } = useSWR<ClienteDetalhe>(open && client ? `clientes/${client.id}` : null, fetcher);
  const { data: servicos } = useSWR<{ items: Servico[] }>(open ? "servicos" : null, fetcher);
  const { data: slots } = useSWR<{ slots: string[] }>(open && date ? `agenda/slots?data=${date}` : null, fetcher, {
    onSuccess: (r) => { if (prefill?.time && !slot) { const m = r.slots.find((s) => fmtTime(s) === prefill.time); if (m) setSlot(m); } },
  });

  async function save() {
    setBusy(true); setError(null);
    try {
      await api("agenda/agendamentos", { method: "POST", body: { cliente_id: client!.id, veiculo_id: veiculo ? Number(veiculo) : undefined, servico_id: servico ? Number(servico) : undefined, inicio: slot, descricao: desc || undefined, status } });
      onDone();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Nova avaliação" description="Só horários livres são oferecidos: o bot enxerga este agendamento como ocupado.">
        <div className="space-y-4">
          <ErrorNote message={error} />
          {!client ? (
            <Field label="Cliente" htmlFor="nc" hint="Busque por nome, telefone ou placa. O cliente precisa já ter falado com o bot.">
              <Input id="nc" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Digite ao menos 2 caracteres" />
              {found && found.items.length > 0 && (
                <ul className="mt-1 divide-y rounded-md border bg-card">
                  {found.items.map((c) => <li key={c.id}><button className="w-full px-3 py-2 text-left text-sm hover:bg-muted" onClick={() => setClient(c)}>{c.nome ?? "Sem nome"} <span className="tabular text-xs text-muted-foreground">{c.telefone}</span></button></li>)}
                </ul>
              )}
              {found && found.items.length === 0 && <p className="mt-1 text-xs text-muted-foreground">Nenhum cliente encontrado.</p>}
            </Field>
          ) : (
            <div className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-sm"><span className="font-medium">{client.nome ?? client.telefone}</span><button className="text-xs text-primary hover:underline" onClick={() => { setClient(null); setVeiculo(""); }}>Trocar</button></div>
          )}
          {client && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Veículo" htmlFor="nv"><Select id="nv" value={veiculo} onChange={(e) => setVeiculo(e.target.value)}><option value="">Não informado</option>{detail?.veiculos.map((v) => <option key={v.id} value={v.id}>{v.descricao}</option>)}</Select></Field>
              <Field label="Serviço pretendido" htmlFor="ns"><Select id="ns" value={servico} onChange={(e) => setServico(e.target.value)}><option value="">A definir na avaliação</option>{servicos?.items.filter((s) => s.ativo).map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}</Select></Field>
              <Field label="Data" htmlFor="nd"><Input id="nd" type="date" value={date} onChange={(e) => { setDate(e.target.value); setSlot(""); }} /></Field>
              <Field label="Horário livre" htmlFor="nh" hint={slots && slots.slots.length === 0 ? "Sem horários livres neste dia." : undefined}>
                <Select id="nh" value={slot} onChange={(e) => setSlot(e.target.value)}><option value="">Selecione…</option>{slots?.slots.map((s) => <option key={s} value={s}>{fmtTime(s)}</option>)}</Select>
              </Field>
              <Field label="Situação inicial" htmlFor="nst"><Select id="nst" value={status} onChange={(e) => setStatus(e.target.value)}><option value="CONFIRMADO">Confirmado</option><option value="PENDENTE">Pendente</option></Select></Field>
              <div className="sm:col-span-2"><Field label="Observação (opcional)" htmlFor="nde"><Textarea id="nde" value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={1000} /></Field></div>
            </div>
          )}
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Cancelar</Button><Button onClick={save} disabled={!client || !slot || busy}>Criar avaliação</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

function SettingsDialog({ open, data, onClose, onDone }: { open: boolean; data: AgendaResp; onClose: () => void; onDone: () => void }) {
  const [cfg, setCfg] = useState(data.config);
  const [rows, setRows] = useState(data.horarios.map((h) => ({ dia_semana: h.dia_semana, abre: h.abre, fecha: h.fecha })));
  const [error, setError] = useState<string | null>(null);
  const [key, setKey] = useState(open);
  if (open !== key) { setKey(open); if (open) { setCfg(data.config); setRows(data.horarios.map((h) => ({ dia_semana: h.dia_semana, abre: h.abre, fecha: h.fecha }))); setError(null); } }

  async function save() {
    try {
      await api("agenda/config", { method: "PUT", body: cfg });
      await api("agenda/horarios", { method: "PUT", body: rows });
      onDone();
    } catch (e) { setError(errMsg(e)); }
  }
  const num = (v: string) => (v === "" ? 0 : Number(v));
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Configurar agenda" description="Vale para o bot e para o painel. Avaliações já marcadas não são alteradas.">
        <div className="space-y-5">
          <ErrorNote message={error} />
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Duração (min)" htmlFor="c1"><Input id="c1" type="number" min={15} max={240} step={15} value={cfg.slot_minutos} onChange={(e) => setCfg({ ...cfg, slot_minutos: num(e.target.value) })} /></Field>
            <Field label="Antecedência (h)" htmlFor="c2"><Input id="c2" type="number" min={0} max={72} value={cfg.antecedencia_minima_horas} onChange={(e) => setCfg({ ...cfg, antecedencia_minima_horas: num(e.target.value) })} /></Field>
            <Field label="Janela (dias)" htmlFor="c3"><Input id="c3" type="number" min={1} max={90} value={cfg.janela_dias} onChange={(e) => setCfg({ ...cfg, janela_dias: num(e.target.value) })} /></Field>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">Expediente</p>
            <ul className="space-y-2">
              {rows.map((r, i) => (
                <li key={i} className="flex items-center gap-2">
                  <Select aria-label="Dia da semana" className="w-32" value={r.dia_semana} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, dia_semana: Number(e.target.value) } : x))}>{DIAS.map((d, n) => <option key={n} value={n}>{d}</option>)}</Select>
                  <Input aria-label="Abre" type="time" className="w-28" value={r.abre} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, abre: e.target.value } : x))} />
                  <span className="text-muted-foreground">–</span>
                  <Input aria-label="Fecha" type="time" className="w-28" value={r.fecha} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, fecha: e.target.value } : x))} />
                  <Button size="sm" variant="ghost" onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label="Remover faixa">Remover</Button>
                </li>
              ))}
            </ul>
            <Button size="sm" variant="outline" className="mt-2" onClick={() => setRows([...rows, { dia_semana: 0, abre: "08:00", fecha: "12:00" }])}><Plus /> Adicionar faixa</Button>
          </div>
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Cancelar</Button><Button onClick={save}>Salvar</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
