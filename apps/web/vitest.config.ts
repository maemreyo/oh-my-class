import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
	test: {
		environment: "node",
		globals: true,
		setupFiles: [],
		include: ["src/**/*.test.{ts,tsx}", "tests/**/*.test.{ts,tsx}"],
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
			"@oh-my-class/schemas": path.resolve(
				__dirname,
				"../../common/schemas/src",
			),
		},
	},
});
