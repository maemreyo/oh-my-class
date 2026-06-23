import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { logger } from "@/lib/logger";
import { ErrorBoundary } from "./error-boundary";

describe("ErrorBoundary", () => {
	beforeEach(() => {
		vi.spyOn(console, "error").mockImplementation(() => {});
		vi.spyOn(logger, "error").mockImplementation(() => {});
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("getDerivedStateFromError returns error state", () => {
		const testError = new Error("Test error message");
		const state = ErrorBoundary.getDerivedStateFromError(testError);

		expect(state).toEqual({
			hasError: true,
			error: testError,
		});
	});

	it("resetError calls setState with cleared error state", () => {
		const boundary = new ErrorBoundary({
			children: React.createElement("div", {}, "test"),
		});

		const setStateSpy = vi.spyOn(boundary, "setState");

		boundary.resetError();

		expect(setStateSpy).toHaveBeenCalledWith({
			hasError: false,
			error: null,
		});
	});

	it("componentDidCatch logs error with component stack", () => {
		const testError = new Error("Component error");
		const errorInfo: React.ErrorInfo = {
			componentStack: "at TestComponent (test.tsx:10)",
		};

		const boundary = new ErrorBoundary({
			children: React.createElement("div", {}, "test"),
		});

		boundary.componentDidCatch(testError, errorInfo);

		expect(logger.error).toHaveBeenCalledTimes(1);
		expect(logger.error).toHaveBeenCalledWith("React component error caught", {
			component_stack: errorInfo.componentStack,
			error_message: testError.message,
		});
	});

	it("renders children when no error", () => {
		const boundary = new ErrorBoundary({
			children: React.createElement("div", { key: "test" }, "Test content"),
		});

		const rendered = boundary.render();
		expect(rendered).toBeDefined();
		// When there's no error, it should render children
		expect(boundary.state.hasError).toBe(false);
	});

	it("uses custom fallback when provided", () => {
		const customFallback = vi.fn((error: Error, _resetError: () => void) =>
			React.createElement("div", {}, `Custom: ${error.message}`),
		);

		const boundary = new ErrorBoundary({
			children: React.createElement("div", {}, "test"),
			fallback: customFallback,
		});

		const testError = new Error("Test error");
		boundary.state = {
			hasError: true,
			error: testError,
		};

		const rendered = boundary.render();
		expect(customFallback).toHaveBeenCalledWith(
			testError,
			expect.any(Function),
		);
		expect(React.isValidElement(rendered)).toBe(true);
	});

	it("renders default ErrorFallback when no custom fallback provided", () => {
		const boundary = new ErrorBoundary({
			children: React.createElement("div", {}, "test"),
		});

		const testError = new Error("Test error");
		boundary.setState({
			hasError: true,
			error: testError,
		});

		const rendered = boundary.render();
		expect(rendered).toBeDefined();
		// ErrorFallback should be rendered (it's a React component)
		expect(React.isValidElement(rendered)).toBe(true);
	});
});
