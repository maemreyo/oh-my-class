import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { OMCLogger } from "@/lib/logger";
import * as loggerModule from "@/lib/logger";
import { useErrorLogger } from "./use-error-logger";

describe("useErrorLogger", () => {
	let mockBoundLogger: OMCLogger;
	let mockBoundLoggerError: ReturnType<typeof vi.fn>;
	let mockFetch: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		mockBoundLogger = new OMCLogger();
		mockBoundLoggerError = vi.fn();
		vi.spyOn(mockBoundLogger, "error").mockImplementation(mockBoundLoggerError);

		vi.spyOn(loggerModule.logger, "bind").mockReturnValue(mockBoundLogger);
		mockFetch = vi.fn().mockResolvedValue(new Response());
		global.fetch = mockFetch;
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("returns logError function", () => {
		const result = useErrorLogger();
		expect(result).toHaveProperty("logError");
		expect(typeof result.logError).toBe("function");
	});

	it("logError calls logger.error with component context", () => {
		const { logError } = useErrorLogger("TestComponent");
		const error = new Error("Test error");

		logError(error);

		expect(loggerModule.logger.bind).toHaveBeenCalledWith({
			component: "TestComponent",
		});
	});

	it("logError includes error message and stack", () => {
		const { logError } = useErrorLogger("TestComponent");
		const error = new Error("Test error");

		logError(error);

		expect(mockBoundLoggerError).toHaveBeenCalledWith("Component error", {
			error_message: "Test error",
			stack: expect.any(String),
		});
	});

	it("logError does not throw when backend POST fails", () => {
		mockFetch.mockRejectedValueOnce(new Error("Network error"));

		const { logError } = useErrorLogger();
		const error = new Error("Test error");

		expect(() => {
			logError(error);
		}).not.toThrow();
	});

	it("defaults componentName to anonymous when not provided", () => {
		const { logError } = useErrorLogger();
		const error = new Error("Test error");

		logError(error);

		expect(loggerModule.logger.bind).toHaveBeenCalledWith({
			component: "anonymous",
		});
	});

	it("includes extra data in logger.error call", () => {
		const { logError } = useErrorLogger("TestComponent");
		const error = new Error("Test error");
		const extra = { userId: "user-123", action: "save" };

		logError(error, extra);

		expect(mockBoundLoggerError).toHaveBeenCalledWith("Component error", {
			error_message: "Test error",
			stack: expect.any(String),
			userId: "user-123",
			action: "save",
		});
	});

	it("POSTs error to backend webhook endpoint", async () => {
		const { logError } = useErrorLogger("TestComponent");
		const error = new Error("Test error");

		logError(error);

		// Give async fetch a moment to execute
		await new Promise((resolve) => setTimeout(resolve, 10));

		expect(mockFetch).toHaveBeenCalledWith(
			"/webhook/error",
			expect.objectContaining({
				method: "POST",
				headers: { "Content-Type": "application/json" },
			}),
		);

		const callArgs = mockFetch.mock.calls[0];
		const body = JSON.parse(callArgs[1].body);
		expect(body.error_message).toBe("Test error");
		expect(body.component).toBe("TestComponent");
	});
});
