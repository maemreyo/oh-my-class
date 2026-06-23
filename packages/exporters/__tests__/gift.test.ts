import { describe, it, expect } from "vitest";
import { exportByFormat } from "../src/index.js";

describe("exportByFormat", () => {
  it("throws for unknown format", async () => {
    await expect(
      exportByFormat("unknown" as never, []),
    ).rejects.toThrow("Unknown export format");
  });

  it("gift format throws not-implemented", async () => {
    await expect(exportByFormat("gift", [])).rejects.toThrow(
      "Not yet implemented",
    );
  });
});
