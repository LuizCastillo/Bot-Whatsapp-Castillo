import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, serverConfig } from "@/lib/server-config";

/**
 * Proxy autenticado: navegador → Next.js (este arquivo) → FastAPI (Render).
 *
 * - O token de sessão do backend vive apenas em cookie HttpOnly deste domínio.
 * - O navegador nunca conhece a URL do backend, o token nem o segredo do proxy.
 * - Tudo é encaminhado somente para /panel/* (o /webhook da Meta nunca passa aqui).
 */
export const dynamic = "force-dynamic";
const MAX_BODY = 1_000_000; // 1 MB
const isProd = process.env.NODE_ENV === "production";

function json(status: number, detail: string) {
  return NextResponse.json({ detail }, { status });
}

function sameOrigin(req: NextRequest, extra: string[]): boolean {
  const origin = req.headers.get("origin");
  if (!origin) return false;
  try {
    const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
    return new URL(origin).host === host || extra.includes(origin);
  } catch {
    return false;
  }
}

async function handle(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  let cfg;
  try {
    cfg = serverConfig();
  } catch {
    return json(500, "Servidor mal configurado.");
  }
  const { path } = await ctx.params;
  if (!path.length || path.some((s) => !s || s === "." || s === ".." || /[\\%]/.test(s))) {
    return json(400, "Caminho inválido.");
  }
  const method = req.method;
  const mutating = !["GET", "HEAD"].includes(method);
  if (mutating && !sameOrigin(req, cfg.extraOrigins)) return json(403, "Origem não permitida.");

  const joined = path.join("/");
  const isLogin = joined === "auth/login";
  const token = req.cookies.get(SESSION_COOKIE)?.value;

  const headers: Record<string, string> = {
    "X-Proxy-Secret": cfg.secret,
    "X-Client-IP": req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "",
    Accept: "application/json",
  };
  if (token && !isLogin) headers.Authorization = `Bearer ${token}`;

  let body: ArrayBuffer | undefined;
  if (mutating) {
    body = await req.arrayBuffer();
    if (body.byteLength > MAX_BODY) return json(413, "Corpo da requisição muito grande.");
    const ct = req.headers.get("content-type");
    if (ct) headers["Content-Type"] = ct;
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${cfg.backend}/panel/${joined}${req.nextUrl.search}`, {
      method,
      headers,
      body: body && body.byteLength ? body : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(25_000),
    });
  } catch {
    return json(502, "Não foi possível falar com o servidor. Tente novamente em instantes.");
  }

  if (isLogin && upstream.ok) {
    const data = await upstream.json();
    const res = NextResponse.json({ usuario: data.usuario });
    res.cookies.set(SESSION_COOKIE, data.token, {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",
      path: "/",
      expires: new Date(data.expira_em),
    });
    return res;
  }

  const res =
    upstream.status === 204
      ? new NextResponse(null, { status: 204 })
      : new NextResponse(upstream.body, {
          status: upstream.status,
          headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
        });
  res.headers.set("Cache-Control", "no-store");
  // Logout ou sessão inválida: apaga o cookie
  if (joined === "auth/logout" || upstream.status === 401) res.cookies.delete(SESSION_COOKIE);
  return res;
}

export { handle as GET, handle as POST, handle as PUT, handle as PATCH, handle as DELETE };
