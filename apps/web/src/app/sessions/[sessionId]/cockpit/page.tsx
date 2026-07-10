"use client";

import { useParams, useSearchParams } from "next/navigation";
import { TeachingCockpit } from "@/components/teaching-session/teaching-cockpit";
import { decodeSessionToken } from "@/lib/session-token";

/**
 * TSP-04: the live teaching cockpit route. There's no join/session-launch UI
 * built in apps/web yet (TSP-02/03 are gateway-only so far), so the session
 * token travels as a `?token=` query param for now -- the same value TSP-02's
 * join flow (`teaching_session/tokens.py::mint_session_token`) already
 * returns to whatever minted it. Swap this for a proper join-flow redirect
 * once one exists; the cockpit itself doesn't care how the token arrived.
 */
export default function TeachingCockpitPage() {
	const params = useParams();
	const sessionId = params.sessionId as string;
	const searchParams = useSearchParams();
	const token = searchParams.get("token");

	if (!token) {
		return (
			<div className="mx-auto max-w-2xl p-8 text-sm text-muted-foreground">
				Missing session token. Open this page via a session join link.
			</div>
		);
	}

	const claims = decodeSessionToken(token);
	if (!claims) {
		return (
			<div className="mx-auto max-w-2xl p-8 text-sm text-destructive">
				Invalid or expired session token.
			</div>
		);
	}

	return (
		<div className="mx-auto flex max-w-3xl flex-col gap-4 p-4 md:p-8">
			<h1 className="text-xl font-semibold">Live cockpit</h1>
			<TeachingCockpit sessionId={sessionId} sessionToken={token} role={claims.role} />
		</div>
	);
}
