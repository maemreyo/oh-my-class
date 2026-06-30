import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const checkedRoots = ["src/components", "src/app"];
const allowedFiles = new Set(["src/app/globals.css"]);

function productionUiFiles(root: string): string[] {
	const files: string[] = [];
	for (const entry of readdirSync(root)) {
		const path = join(root, entry);
		const stat = statSync(path);
		if (stat.isDirectory()) {
			files.push(...productionUiFiles(path));
			continue;
		}
		if (/\.(ts|tsx|css)$/.test(path) && !allowedFiles.has(path)) {
			files.push(path);
		}
	}
	return files;
}

describe("methodology UI token guard", () => {
	it("does not introduce raw hex colors in production UI components", () => {
		const checkedFiles = checkedRoots.flatMap(productionUiFiles);

		for (const file of checkedFiles) {
			const source = readFileSync(join(process.cwd(), file), "utf8");
			expect(source, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
		}
	});
});
