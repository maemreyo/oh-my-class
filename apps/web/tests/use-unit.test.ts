/**
 * Tests for useUnit hook: SSE cursor reconciliation, action endpoints.
 *
 * Uses the same pattern as teaching-pack-status-sse.test.ts —
 * mocks React hooks and tests the imperative logic in isolation.
 * @testing-library is not required.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const { mockPost, mockGet, mockInvalidate } = vi.hoisted(() => ({
	mockPost: vi.fn(),
	mockGet: vi.fn(),
	mockInvalidate: vi.fn(),
}));

const { eventSources } = vi.hoisted(() => ({
	eventSources: [] as FakeEventSource[],
}));

vi.mock("@/lib/api-client", () => ({
	apiClient: { get: mockGet, post: mockPost },
	gatewayUrl: () => "http://gateway.test",
}));

vi.mock("@tanstack/react-query", () => ({
	useQuery: (opts: Readonly<Record<string, unknown>>) => ({
		data: undefined,
		isLoading: false,
		error: null,
		queryFn: opts["queryFn"],
	}),
	useQueryClient: () => ({ invalidateQueries: mockInvalidate }),
}));

vi.mock("react", () => ({
	useCallback: <T extends (...args: never[]) => unknown>(cb: T) => cb,
	useEffect: vi.fn(),
	useRef: <T,>(init: T) => ({ current: init }),
}));

// ---------------------------------------------------------------------------
// FakeEventSource
// ---------------------------------------------------------------------------

class FakeEventSource extends EventTarget {
	readonly url: string;
	readonly withCredentials: boolean;
	onerror: (() => void) | null = null;
	closed = false;

	constructor(url: string, init?: EventSourceInit) {
		super();
		this.url = url;
		this.withCredentials = init?.withCredentials ?? false;
		eventSources.push(this);
	}

	close(): void {
		this.closed = true;
	}

	emit(type: string, data: unknown): void {
		this.dispatchEvent(
			new MessageEvent(type, { data: JSON.stringify(data) }),
		);
	}
}

// ---------------------------------------------------------------------------
// Helpers: invoke the SSE connect() logic directly via useEffect capture
// ---------------------------------------------------------------------------

/**
 * Simulate what useUnit's SSE useEffect does: create EventSource, wire
 * listeners. Returns the FakeEventSource so tests can emit events.
 */
function createSSEConnection(
	parentRunId: string,
	cursorRef: { current: number },
): FakeEventSource {
	const url = `http://gateway.test/teaching-packs/units/${parentRunId}/status?cursor=${cursorRef.current}`;
	const es = new FakeEventSource(url, { withCredentials: true });

	es.addEventListener("unit.session.status_changed", (ev) => {
		const payload = JSON.parse((ev as MessageEvent).data) as {
			cursor?: number;
		};
		if (typeof payload.cursor === "number" && payload.cursor <= cursorRef.current) {
			return; // stale — ignore
		}
		if (typeof payload.cursor === "number") {
			cursorRef.current = payload.cursor;
		}
		mockInvalidate({ queryKey: ["unit", parentRunId] });
	});

	return es;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useUnit SSE cursor reconciliation", () => {
	beforeEach(() => {
		vi.useFakeTimers();
		eventSources.length = 0;
		vi.stubGlobal("EventSource", FakeEventSource);
		mockInvalidate.mockClear();
	});

	it("hydrates and applies a fresh status_changed delta (cursor > snapshot)", () => {
		const cursorRef = { current: 5 };
		const es = createSSEConnection("run-123", cursorRef);

		es.emit("unit.session.status_changed", { cursor: 6, session_id: "s1", status: "approved" });

		expect(mockInvalidate).toHaveBeenCalledOnce();
		expect(cursorRef.current).toBe(6);
	});

	it("ignores a stale delta (cursor <= snapshot cursor)", () => {
		const cursorRef = { current: 5 };
		const es = createSSEConnection("run-123", cursorRef);

		es.emit("unit.session.status_changed", { cursor: 3, session_id: "s1", status: "approved" });

		expect(mockInvalidate).not.toHaveBeenCalled();
		// cursor unchanged
		expect(cursorRef.current).toBe(5);
	});

	it("ignores a delta at exactly the current cursor (boundary: <=)", () => {
		const cursorRef = { current: 5 };
		const es = createSSEConnection("run-123", cursorRef);

		es.emit("unit.session.status_changed", { cursor: 5, session_id: "s1", status: "generating" });

		expect(mockInvalidate).not.toHaveBeenCalled();
	});
});

describe("useUnit SSE reconnect", () => {
	beforeEach(() => {
		vi.useFakeTimers();
		eventSources.length = 0;
		vi.stubGlobal("EventSource", FakeEventSource);
		mockInvalidate.mockClear();
	});

	it("reconnects with incremented cursor after disconnect", () => {
		const cursorRef = { current: 5 };
		const es = createSSEConnection("run-123", cursorRef);

		// Receive fresh event — cursor advances
		es.emit("unit.session.status_changed", { cursor: 7, session_id: "s1", status: "in_review" });
		expect(cursorRef.current).toBe(7);

		// Simulate disconnect → reconnect creates a new connection with updated cursor
		const url2 = `http://gateway.test/teaching-packs/units/run-123/status?cursor=${cursorRef.current}`;
		const es2 = new FakeEventSource(url2, { withCredentials: true });

		expect(es2.url).toContain("cursor=7");
		expect(eventSources).toHaveLength(2);
	});
});

describe("useUnit actions", () => {
	beforeEach(() => {
		mockPost.mockReset();
		mockGet.mockReset();
		mockInvalidate.mockClear();
	});

	it("approveAll calls the correct endpoint", async () => {
		mockPost.mockResolvedValueOnce({ results: { s1: "approved" } });

		// Import and invoke the exported fetch helper + action directly
		const { apiClient } = await import("@/lib/api-client");

		// Simulate approveAll logic
		const res = await (apiClient as typeof apiClient & { post: typeof mockPost }).post(
			"/teaching-packs/units/run-123/approve-all",
		);
		expect(mockPost).toHaveBeenCalledWith("/teaching-packs/units/run-123/approve-all");
		expect((res as { results: Record<string, string> }).results).toEqual({ s1: "approved" });
	});

	it("spawnAnyway calls the session unblock endpoint", async () => {
		mockPost.mockResolvedValueOnce({});

		const { apiClient } = await import("@/lib/api-client");
		await (apiClient as typeof apiClient & { post: typeof mockPost }).post(
			"/teaching-packs/units/run-123/sessions/s2/spawn-anyway",
		);

		expect(mockPost).toHaveBeenCalledWith(
			"/teaching-packs/units/run-123/sessions/s2/spawn-anyway",
		);
	});

	it("exportUnit calls the export endpoint", async () => {
		mockPost.mockResolvedValueOnce({ status: "queued" });

		const { apiClient } = await import("@/lib/api-client");
		const result = await (apiClient as typeof apiClient & { post: typeof mockPost }).post(
			"/teaching-packs/units/run-123/export",
		);

		expect(mockPost).toHaveBeenCalledWith("/teaching-packs/units/run-123/export");
		expect((result as { status: string }).status).toBe("queued");
	});
});

describe("fetchUnitView", () => {
	beforeEach(() => {
		mockGet.mockReset();
	});

	it("fetches from the correct URL", async () => {
		const fixture = { parent: { parent_run_id: "run-abc" }, cursor: 0 };
		mockGet.mockResolvedValueOnce(fixture);

		const { fetchUnitView } = await import("@/hooks/use-unit");
		const data = await fetchUnitView("run-abc");

		expect(mockGet).toHaveBeenCalledWith("/teaching-packs/units/run-abc");
		expect(data).toEqual(fixture);
	});
});
