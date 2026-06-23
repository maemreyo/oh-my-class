import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * JWT middleware — check auth on protected routes.
 * Public routes: /, /api/auth/login
 * Protected: everything under /(dashboard)
 */
export function middleware(request: NextRequest) {
	const token = request.cookies.get("auth-token")?.value;

	// Public routes — no auth required
	if (
		request.nextUrl.pathname === "/" ||
		request.nextUrl.pathname.startsWith("/api/auth")
	) {
		return NextResponse.next();
	}

	// Protected routes — require valid JWT
	if (!token) {
		const loginUrl = new URL("/", request.url);
		loginUrl.searchParams.set("redirect", request.nextUrl.pathname);
		return NextResponse.redirect(loginUrl);
	}

	// TODO: Verify JWT token (call Gateway /auth/verify or verify locally)
	// For now, just check token exists
	return NextResponse.next();
}

export const config = {
	matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
