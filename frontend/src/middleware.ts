import { NextRequest, NextResponse } from "next/server";

const COOKIE = "castillo_session";

// Barreira de navegação apenas. A validação real da sessão é sempre feita pelo backend.
export function middleware(req: NextRequest) {
  const hasSession = req.cookies.has(COOKIE);
  const { pathname } = req.nextUrl;
  if (pathname === "/login") {
    if (hasSession) return NextResponse.redirect(new URL("/", req.url));
    return NextResponse.next();
  }
  if (!hasSession) {
    const url = new URL("/login", req.url);
    if (pathname !== "/") url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"] };
