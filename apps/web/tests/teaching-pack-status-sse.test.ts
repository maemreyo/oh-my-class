import { beforeEach, describe, expect, it, vi } from "vitest";

type EventHandler = (event: Event) => void;

const { eventSources } = vi.hoisted(() => ({
	eventSources: [] as FakeEventSource[],
}));

vi.mock("react", () => ({
	useCallback: <T extends (...args: never[]) => unknown>(callback: T) => callback,
	useRef: <T,>(initial: T) => ({ current: initial }),
}));

vi.mock("@/lib/api-client", () => ({
	apiClient: { get: vi.fn(), post: vi.fn() },
	gatewayUrl: () => "http://gateway.test",
}));

vi.mock("@tanstack/react-query", () => ({
	useMutation: (opts: Readonly<Record<string, unknown>>) => ({
		mutateAsync: opts["mutationFn"],
		isPending: false,
	}),
	useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

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

	emitMessage(type: string, data: string, lastEventId: string): void {
		this.dispatchEvent(new MessageEvent(type, { data, lastEventId }));
	}
}

describe("useTeachingPackStatus", () => {
	beforeEach(() => {
		vi.useFakeTimers();
		eventSources.length = 0;
		vi.stubGlobal("EventSource", FakeEventSource);
	});

	it("reconnects with last_event_id after receiving a status event", async () => {
		const { useTeachingPackStatus } = await import("@/hooks/use-teaching-packs");
		const received: string[] = [];

		const { subscribe } = useTeachingPackStatus("run-1");
		const cleanup = subscribe((event) => received.push(event.name));

		expect(eventSources).toHaveLength(1);
		expect(eventSources[0]?.url).toBe("http://gateway.test/teaching-packs/runs/run-1/status");
		expect(eventSources[0]?.withCredentials).toBe(true);

		eventSources[0]?.emitMessage(
			"teaching_pack.content_approval.opened",
			'{"gate_id":"gate-1"}',
			"42",
		);
		eventSources[0]?.onerror?.();
		vi.advanceTimersByTime(1_000);

		expect(received).toEqual(["teaching_pack.content_approval.opened"]);
		expect(eventSources).toHaveLength(2);
		expect(eventSources[1]?.url).toBe(
			"http://gateway.test/teaching-packs/runs/run-1/status?last_event_id=42",
		);
		cleanup();
		expect(eventSources[1]?.closed).toBe(true);
	});
});
