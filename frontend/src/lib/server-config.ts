// Somente servidor: nunca importe este arquivo em componentes de cliente.
export const SESSION_COOKIE = "castillo_session";

export function serverConfig() {
  const backend = process.env.BACKEND_URL;
  const secret = process.env.PROXY_SHARED_SECRET;
  if (!backend || !secret) {
    throw new Error("BACKEND_URL e PROXY_SHARED_SECRET precisam estar definidos no servidor.");
  }
  const extra = (process.env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return { backend: backend.replace(/\/$/, ""), secret, extraOrigins: extra };
}
