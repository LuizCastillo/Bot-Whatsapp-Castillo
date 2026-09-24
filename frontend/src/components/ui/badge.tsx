import { cn } from "@/lib/utils";
import { MODO, STATUS } from "@/lib/format";
import type { Modo, Status } from "@/lib/types";

const base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap";

export function Badge({ className, ...p }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn(base, "bg-muted text-foreground ring-border", className)} {...p} />;
}
export function StatusBadge({ status }: { status: Status | "RASCUNHO" }) {
  const s = STATUS[status];
  return <span className={cn(base, s.cls)}>{s.label}</span>;
}
export function ModoBadge({ modo }: { modo: Modo }) {
  const m = MODO[modo];
  return <span className={cn(base, m.cls)}>{m.label}</span>;
}
