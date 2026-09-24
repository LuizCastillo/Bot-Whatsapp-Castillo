export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function detailOf(data: unknown, fallback: string): string {
  const d = (data as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e) => (e as { msg?: string }).msg ?? "").filter(Boolean).join("; ") || fallback;
  }
  return fallback;
}

/** Todas as chamadas vão para /api/* (proxy do Next.js). O navegador nunca fala com o backend. */
export async function api<T = unknown>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`/api/${path.replace(/^\//, "")}`, {
    method: init.method ?? "GET",
    headers: init.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    credentials: "same-origin",
  });
  if (res.status === 401 && !path.startsWith("auth/login") && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new ApiError(401, "Sessão expirada.");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, detailOf(data, "Algo deu errado. Tente novamente."));
  return data as T;
}

export const fetcher = <T,>(path: string) => api<T>(path);
export const errMsg = (e: unknown) => (e instanceof Error ? e.message : "Algo deu errado.");
