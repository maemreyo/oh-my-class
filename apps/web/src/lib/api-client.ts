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

	async request<T>(method: string, path: string, body?: unknown): Promise<T> {
		const token = this.getToken();
		const headers: Record<string, string> = {
			"Content-Type": "application/json",
		};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const response = await fetch(`${this.baseUrl}${path}`, {
			method,
			headers,
			body: body ? JSON.stringify(body) : undefined,
		});

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }));
			throw new Error(error.detail || `HTTP ${response.status}`);
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
