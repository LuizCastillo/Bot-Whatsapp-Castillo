"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import { CalendarDays, ClipboardCheck, LayoutDashboard, LogOut, Menu, MessageSquare, ShieldCheck, Users, Wrench, X } from "lucide-react";
import { api, fetcher } from "@/lib/api";
import type { Conversa, User } from "@/lib/types";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agenda", label: "Agenda", icon: CalendarDays },
  { href: "/avaliacoes", label: "Avaliações", icon: ClipboardCheck },
  { href: "/clientes", label: "Clientes", icon: Users },
  { href: "/conversas", label: "Conversas", icon: MessageSquare },
  { href: "/servicos", label: "Serviços", icon: Wrench },
  { href: "/equipe", label: "Equipe", icon: ShieldCheck, admin: true },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { data: user } = useSWR<User>("auth/me", fetcher);
  const { data: waiting } = useSWR<{ items: Conversa[] }>("conversas?modo=AGUARDANDO_EQUIPE", fetcher, { refreshInterval: 30000 });
  const waitingCount = waiting?.items.length ?? 0;

  async function logout() {
    try { await api("auth/logout", { method: "POST" }); } finally { router.replace("/login"); router.refresh(); }
  }

  const nav = (
    <nav className="flex-1 space-y-1 px-3" aria-label="Principal">
      {NAV.filter((n) => !n.admin || user?.papel === "ADMIN").map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link key={href} href={href} onClick={() => setOpen(false)} aria-current={active ? "page" : undefined}
            className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active ? "bg-white/10 text-white" : "text-sidebar-muted hover:bg-white/5 hover:text-white")}>
            <Icon className="size-4" aria-hidden />
            <span className="flex-1">{label}</span>
            {href === "/conversas" && waitingCount > 0 && (
              <span className="rounded-full bg-primary px-2 py-0.5 text-[11px] font-semibold text-primary-foreground" aria-label={`${waitingCount} aguardando`}>{waitingCount}</span>
            )}
          </Link>
        );
      })}
    </nav>
  );

  const brand = (
    <div className="flex items-center gap-3 px-6 py-5">
      <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground"><Wrench className="size-4" /></span>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-white">Oficina Castillo</p>
        <p className="text-[11px] text-sidebar-muted">Painel da equipe</p>
      </div>
    </div>
  );

  const footer = (
    <div className="border-t border-white/10 p-4">
      <p className="truncate text-sm font-medium text-white">{user?.nome ?? "…"}</p>
      <p className="truncate text-xs text-sidebar-muted">{user ? (user.papel === "ADMIN" ? "Administrador" : "Atendente") : ""}</p>
      <button onClick={logout} className="mt-3 flex items-center gap-2 text-xs text-sidebar-muted hover:text-white">
        <LogOut className="size-3.5" aria-hidden /> Sair
      </button>
    </div>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col bg-sidebar text-sidebar-foreground lg:flex">
        {brand}{nav}{footer}
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between bg-sidebar px-4 py-3 text-white lg:hidden">
        <div className="flex items-center gap-2"><Wrench className="size-4 text-primary" aria-hidden /><span className="text-sm font-semibold">Oficina Castillo</span></div>
        <button onClick={() => setOpen(true)} aria-label="Abrir menu" className="rounded p-1.5 hover:bg-white/10"><Menu className="size-5" /></button>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-64 flex-col bg-sidebar text-sidebar-foreground">
            <button onClick={() => setOpen(false)} aria-label="Fechar menu" className="absolute right-3 top-4 rounded p-1 text-sidebar-muted hover:text-white"><X className="size-5" /></button>
            {brand}{nav}{footer}
          </div>
        </div>
      )}

      <main className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">{children}</main>
    </div>
  );
}
