"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Wrench } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { ErrorNote } from "@/components/ui/blocks";

function LoginForm() {
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api("auth/login", { method: "POST", body: { email, senha } });
      const next = params.get("next");
      // só caminhos internos (evita open redirect)
      window.location.href = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
    } catch (err) {
      setError(errMsg(err));
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="w-full max-w-sm space-y-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Entrar no painel</h2>
        <p className="mt-1 text-sm text-muted-foreground">Acesso exclusivo da equipe da oficina.</p>
      </div>
      <ErrorNote message={error} />
      <Field label="E-mail" htmlFor="email">
        <Input id="email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </Field>
      <Field label="Senha" htmlFor="senha">
        <Input id="senha" type="password" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
      </Field>
      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? "Entrando…" : "Entrar"}
      </Button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-sidebar p-12 text-sidebar-foreground lg:flex">
        <div className="hatch pointer-events-none absolute inset-0 opacity-20" aria-hidden />
        <div className="relative flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-md bg-primary text-primary-foreground"><Wrench className="size-5" /></span>
          <span className="text-lg font-semibold tracking-tight">Oficina Castillo</span>
        </div>
        <div className="relative max-w-md">
          <p className="text-3xl font-semibold leading-tight tracking-tight">O bot organiza. O banco registra. Você tem o controle.</p>
          <p className="mt-4 text-sm text-sidebar-muted">Agenda de avaliações, clientes, fotos e conversas em um só lugar.</p>
        </div>
      </section>
      <section className="flex items-center justify-center p-6">
        <Suspense>
          <LoginForm />
        </Suspense>
      </section>
    </main>
  );
}
