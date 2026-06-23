import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type LogContext, type LogLevel, OMCLogger } from "./logger";

describe("OMCLogger", () => {
	beforeEach(() => {
		vi.spyOn(console, "debug").mockImplementation(() => {});
		vi.spyOn(console, "info").mockImplementation(() => {});
		vi.spyOn(console, "warn").mockImplementation(() => {});
		vi.spyOn(console, "error").mockImplementation(() => {});
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("logger has info/debug/warn/error methods", () => {
		const logger = new OMCLogger();
		expect(typeof logger.info).toBe("function");
		expect(typeof logger.debug).toBe("function");
		expect(typeof logger.warn).toBe("function");
		expect(typeof logger.error).toBe("function");
	});

	it("logger.bind returns new instance", () => {
		const logger = new OMCLogger();
		const context: LogContext = { run_id: "run-1", agent: "planner" };
		const child = logger.bind(context);

		expect(child).not.toBe(logger);
		expect(child).toBeInstanceOf(OMCLogger);

		const grandchild = child.bind({ step: 4 });
		expect(grandchild).not.toBe(child);
		expect(grandchild).not.toBe(logger);
	});

	it("logger.info calls console.info in dev", () => {
		const logger = new OMCLogger({ level: "debug" });
		logger.info("hello world");
		expect(console.info).toHaveBeenCalledTimes(1);
		expect(console.info).toHaveBeenCalledWith(
			expect.stringContaining("hello world"),
		);
	});

	it("logger.error includes context", () => {
		const logger = new OMCLogger().bind({
			run_id: "run-42",
			teacher_id: "t-007",
			agent: "content_creator",
		});
		logger.error("something failed", { code: 500 });

		expect(console.error).toHaveBeenCalledTimes(1);
		const output = (console.error as ReturnType<typeof vi.fn>).mock
			.calls[0][0] as string;
		const parsed = JSON.parse(output);

		expect(parsed.level).toBe("error");
		expect(parsed.message).toBe("something failed");
		expect(parsed.run_id).toBe("run-42");
		expect(parsed.teacher_id).toBe("t-007");
		expect(parsed.agent).toBe("content_creator");
		expect(parsed.code).toBe(500);
		expect(parsed.timestamp).toEqual(expect.any(String));
	});

	it("OMCLogger respects min level", () => {
		const logger = new OMCLogger({ level: "warn" as LogLevel });

		logger.debug("debug msg");
		logger.info("info msg");
		logger.warn("warn msg");
		logger.error("error msg");

		expect(console.debug).not.toHaveBeenCalled();
		expect(console.info).not.toHaveBeenCalled();
		expect(console.warn).toHaveBeenCalledTimes(1);
		expect(console.error).toHaveBeenCalledTimes(1);
	});
});
