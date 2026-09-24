import type { Modo, Status } from "./types";

export const TZ = "America/Sao_Paulo";

const dtf = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("pt-BR", { timeZone: TZ, ...opts });

export const fmtDate = (iso: string) => dtf({ day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(iso));
export const fmtTime = (iso: string) => dtf({ hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(iso));
export const fmtDateTime = (iso: string) => `${fmtDate(iso)} às ${fmtTime(iso)}`;
export const fmtWeekdayShort = (iso: string) => dtf({ weekday: "short" }).format(new Date(iso)).replace(".", "");
export const fmtDayLabel = (iso: string) => dtf({ weekday: "long", day: "2-digit", month: "long" }).format(new Date(iso));

export function fmtPhone(p: string): string {
  const d = p.replace(/\D/g, "");
  if (d.startsWith("55") && d.length === 13) return `+55 (${d.slice(2, 4)}) ${d.slice(4, 9)}-${d.slice(9)}`;
  if (d.startsWith("55") && d.length === 12) return `+55 (${d.slice(2, 4)}) ${d.slice(4, 8)}-${d.slice(8)}`;
  return `+${d}`;
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "agora";
  if (s < 3600) return `há ${Math.floor(s / 60)} min`;
  if (s < 86400) return `há ${Math.floor(s / 3600)} h`;
  return `há ${Math.floor(s / 86400)} d`;
}

export const STATUS: Record<Status | "RASCUNHO", { label: string; cls: string }> = {
  PENDENTE: { label: "Pendente", cls: "bg-amber-100 text-amber-900 ring-amber-300" },
  CONFIRMADO: { label: "Confirmado", cls: "bg-emerald-100 text-emerald-900 ring-emerald-300" },
  REAGENDADO: { label: "Reagendado", cls: "bg-sky-100 text-sky-900 ring-sky-300" },
  CANCELADO: { label: "Cancelado", cls: "bg-zinc-200 text-zinc-700 ring-zinc-300" },
  CONCLUIDO: { label: "Concluído", cls: "bg-indigo-100 text-indigo-900 ring-indigo-300" },
  NAO_COMPARECEU: { label: "Não compareceu", cls: "bg-rose-100 text-rose-900 ring-rose-300" },
  RASCUNHO: { label: "Rascunho", cls: "bg-stone-100 text-stone-700 ring-stone-300" },
};

export const MODO: Record<Modo, { label: string; cls: string }> = {
  BOT: { label: "Automático", cls: "bg-zinc-100 text-zinc-700 ring-zinc-300" },
  HUMANO: { label: "Com a equipe", cls: "bg-emerald-100 text-emerald-900 ring-emerald-300" },
  AGUARDANDO_EQUIPE: { label: "Aguardando equipe", cls: "bg-amber-100 text-amber-900 ring-amber-300" },
};

// ---- datas "YYYY-MM-DD" (aritmética em UTC para não depender do fuso do navegador)
const pad = (n: number) => String(n).padStart(2, "0");
const toISODate = (d: Date) => `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
const parseISODate = (s: string) => { const [y, m, d] = s.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };

export function todayISO(): string {
  const p = dtf({ year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const g = (t: string) => p.find((x) => x.type === t)!.value;
  return `${g("year")}-${g("month")}-${g("day")}`;
}
export const addDays = (s: string, n: number) => { const d = parseISODate(s); d.setUTCDate(d.getUTCDate() + n); return toISODate(d); };
export const weekStart = (s: string) => addDays(s, -((parseISODate(s).getUTCDay() + 6) % 7)); // segunda-feira
export const dayLabelShort = (s: string) =>
  new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC", weekday: "short", day: "2-digit", month: "2-digit" }).format(parseISODate(s)).replace(".", "");
export const dayLabelLong = (s: string) =>
  new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long" }).format(parseISODate(s));

/** Data (YYYY-MM-DD) e minutos desde 00:00 de um instante, no fuso da oficina. */
export function localParts(iso: string): { date: string; minutes: number } {
  const p = dtf({ year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(iso));
  const g = (t: string) => p.find((x) => x.type === t)!.value;
  return { date: `${g("year")}-${g("month")}-${g("day")}`, minutes: Number(g("hour")) * 60 + Number(g("minute")) };
}

function tzOffsetMinutes(d: Date): number {
  const p = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }).formatToParts(d);
  const v = (t: string) => Number(p.find((x) => x.type === t)!.value);
  return (Date.UTC(v("year"), v("month") - 1, v("day"), v("hour"), v("minute"), v("second")) - d.getTime()) / 60000;
}
/** "2026-09-25" + "14:00" (horário de Brasília) → ISO em UTC. */
export function zonedToUtc(date: string, time: string): string {
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  const guess = Date.UTC(y, m - 1, d, hh, mm);
  return new Date(guess - tzOffsetMinutes(new Date(guess)) * 60000).toISOString();
}
export const minutesToHHMM = (m: number) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
export const hhmmToMinutes = (s: string) => { const [h, m] = s.split(":").map(Number); return h * 60 + m; };
