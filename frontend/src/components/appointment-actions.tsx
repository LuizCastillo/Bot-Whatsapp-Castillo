"use client";
import { useState } from "react";
import useSWR from "swr";
import { api, errMsg, fetcher } from "@/lib/api";
import { addDays, fmtTime, todayISO, TZ } from "@/lib/format";
import type { Agendamento, Status } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { Field, Input, Select, Textarea } from "@/components/ui/input";
import { ErrorNote } from "@/components/ui/blocks";

const ACTIVE: Status[] = ["PENDENTE", "CONFIRMADO", "REAGENDADO"];

export function AppointmentActions({ ag, onChanged }: { ag: Agendamento; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<null | "cancel" | "reschedule">(null);

  async function setStatus(status: Status, motivo?: string) {
    setBusy(true);
    setError(null);
    try {
      await api(`agenda/agendamentos/${ag.id}`, { method: "PATCH", body: { status, motivo: motivo || undefined } });
      setDialog(null);
      onChanged();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <ErrorNote message={error} />
      <div className="flex flex-wrap gap-2">
        {ag.status === "PENDENTE" && <Button size="sm" disabled={busy} onClick={() => setStatus("CONFIRMADO")}>Confirmar</Button>}
        {(ag.status === "CONFIRMADO" || ag.status === "REAGENDADO") && (
          <>
            <Button size="sm" disabled={busy} onClick={() => setStatus("CONCLUIDO")}>Marcar como concluída</Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => setStatus("NAO_COMPARECEU")}>Não compareceu</Button>
          </>
        )}
        {ACTIVE.includes(ag.status) && (
          <>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => setDialog("reschedule")}>Reagendar</Button>
            <Button size="sm" variant="outline" className="text-destructive" disabled={busy} onClick={() => setDialog("cancel")}>Cancelar</Button>
          </>
        )}
        {ag.status === "CANCELADO" && <Button size="sm" variant="outline" disabled={busy} onClick={() => setStatus("PENDENTE", "Reativado pela equipe")}>Reativar</Button>}
      </div>
      <CancelDialog open={dialog === "cancel"} onClose={() => setDialog(null)} busy={busy} onConfirm={(m) => setStatus("CANCELADO", m)} />
      <RescheduleDialog ag={ag} open={dialog === "reschedule"} onClose={() => setDialog(null)} onDone={() => { setDialog(null); onChanged(); }} />
    </div>
  );
}

function CancelDialog({ open, onClose, onConfirm, busy }: { open: boolean; onClose: () => void; onConfirm: (m: string) => void; busy: boolean }) {
  const [motivo, setMotivo] = useState("");
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Cancelar avaliação" description="O registro é mantido no histórico com o status Cancelado; o horário volta a ficar disponível.">
        <Field label="Motivo (opcional)" htmlFor="motivo"><Textarea id="motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={300} /></Field>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Voltar</Button>
          <Button variant="destructive" disabled={busy} onClick={() => onConfirm(motivo)}>Cancelar avaliação</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RescheduleDialog({ ag, open, onClose, onDone }: { ag: Agendamento; open: boolean; onClose: () => void; onDone: () => void }) {
  const [date, setDate] = useState(() => addDays(todayISO(), 1));
  const [slot, setSlot] = useState("");
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { data } = useSWR<{ slots: string[] }>(open ? `agenda/slots?data=${date}&excluir=${ag.id}` : null, fetcher);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api(`agenda/agendamentos/${ag.id}`, { method: "PATCH", body: { inicio: slot, motivo: motivo || undefined } });
      onDone();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent title="Reagendar avaliação" description="O horário anterior fica registrado no histórico.">
        <div className="space-y-4">
          <ErrorNote message={error} />
          <Field label="Nova data" htmlFor="rdate"><Input id="rdate" type="date" min={todayISO()} value={date} onChange={(e) => { setDate(e.target.value); setSlot(""); }} /></Field>
          <Field label="Horário disponível" htmlFor="rslot" hint={data && data.slots.length === 0 ? "Nenhum horário livre nesta data." : undefined}>
            <Select id="rslot" value={slot} onChange={(e) => setSlot(e.target.value)}>
              <option value="">Selecione…</option>
              {data?.slots.map((s) => <option key={s} value={s}>{fmtTime(s)}</option>)}
            </Select>
          </Field>
          <Field label="Motivo (opcional)" htmlFor="rmot"><Input id="rmot" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={300} /></Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Voltar</Button>
          <Button disabled={!slot || busy} onClick={save}>Reagendar</Button>
        </DialogFooter>
        <p className="sr-only">Fuso {TZ}</p>
      </DialogContent>
    </Dialog>
  );
}
