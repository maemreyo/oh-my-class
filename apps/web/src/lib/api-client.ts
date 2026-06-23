/**
 * API client wrapper for Gateway communication.
 * All requests go through this client with proper error handling.
 */

const GATEWAY_URL =
	process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8001";

class APIClient {
	private baseUrl: string;

	constructor(baseUrl: string) {
		this.baseUrl = baseUrl;
	}

	private getToken(): string | null {
		if (typeof window === "undefined") return null;
		return (
			document.cookie
				.split("; ")
				.find((row) => row.startsWith("auth-token="))
				?.split("=")[1] ?? null
		);
	}

	private generateRequestId(): string {
		// Use crypto.randomUUID() if available (modern browsers, SSR-safe)
		if (typeof window !== "undefined" && window.crypto?.randomUUID) {
			return window.crypto.randomUUID();
		}
		// Fallback for environments without crypto.randomUUID()
		return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
	}

	async request<T>(method: string, path: string, body?: unknown): Promise<T> {
		const token = this.getToken();
		const requestId = this.generateRequestId();
		const headers: Record<string, string> = {
			"Content-Type": "application/json",
			"X-Request-ID": requestId,
		};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const response = await fetch(`${this.baseUrl}${path}`, {
			method,
			headers,
			body: body ? JSON.stringify(body) : undefined,
		});

		// Extract X-Request-ID from response headers for tracing
		const responseRequestId = response.headers.get("X-Request-ID") || requestId;

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }));
			const errorMessage = error.detail || `HTTP ${response.status}`;
			throw new Error(`${errorMessage} (request: ${responseRequestId})`);
		}

		return response.json() as Promise<T>;
	}

	get<T>(path: string): Promise<T> {
		return this.request<T>("GET", path);
	}

	post<T>(path: string, body?: unknown): Promise<T> {
		return this.request<T>("POST", path, body);
	}

	put<T>(path: string, body?: unknown): Promise<T> {
		return this.request<T>("PUT", path, body);
	}
}

export const apiClient = new APIClient(GATEWAY_URL);
