// TSP-04: client-side read of a TeachingSession role token's claims, for
// role-gating the live cockpit's teacher-only surfaces. Mirrors
// `services/gateway/teaching_session/tokens.py`'s `SessionRole`/
// `SessionTokenPayload` shapes (never the account JWT's `Role`) -- a
// `SlideDeckDisplaySurface`-style hand-mirror (see use-teaching-packs.ts's
// comment on that pattern) since apps/web has no wired import path into the
// Python package.
//
// ponytail: decodes the JWT payload without verifying the signature -- fine
// here because the *value* is only used for a client-side render decision
// (show/hide a panel); every actual privileged action (branch selection,
// preferences) is re-checked server-side against the signed token. Add
// signature verification if this value is ever used for anything more than
// UI gating.

export type SessionRole = "controller" | "display" | "student" | "observer";

export interface SessionTokenClaims {
	readonly session_id: string;
	readonly role: SessionRole;
	readonly exp: number;
}

export function decodeSessionToken(token: string): SessionTokenClaims | null {
	const parts = token.split(".");
	if (parts.length !== 3) return null;
	try {
		const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
		const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
		const decoded = JSON.parse(atob(padded)) as Record<string, unknown>;
		if (typeof decoded.session_id !== "string" || typeof decoded.role !== "string") return null;
		return {
			session_id: decoded.session_id,
			role: decoded.role as SessionRole,
			exp: typeof decoded.exp === "number" ? decoded.exp : 0,
		};
	} catch {
		return null;
	}
}
