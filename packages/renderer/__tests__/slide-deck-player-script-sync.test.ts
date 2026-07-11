import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

// pages/slide_deck.html embeds its presentation/print-mode player script
// inline (via base.html's `<% if (it.pageJS) %>` branch, since Eta template
// literals can't `require`/readFileSync their own template directory
// reliably across dev vs. built execution contexts). slide-deck-player.js is
// a byte-for-byte extracted copy of that same script, kept only so
// slideDeckPlugin.managedScripts (core/asset-policy.ts's inline-only policy
// check) has a real file to hash against. This test is the guard the
// project's own printModeClass precedent recommends: "one test instead of
// two divergent copies" -- if either file changes without the other, this
// fails loudly instead of silently breaking every slide-deck render through
// the registry-based render() API.
describe("slide-deck-player.js stays in sync with pages/slide_deck.html", () => {
  it("the extracted player script is byte-identical to the template's embedded copy", () => {
    const template = readFileSync("templates/pages/slide_deck.html", "utf8");
    const extracted = readFileSync("templates/pages/slide-deck-player.js", "utf8");

    const startMarker = "const pageJS = isPrint ? '' : `";
    const startIdx = template.indexOf(startMarker) + startMarker.length;
    expect(startIdx).toBeGreaterThan(startMarker.length - 1);
    const endIdx = template.indexOf("`;\n  const pageCSS", startIdx);
    expect(endIdx).toBeGreaterThan(startIdx);

    const embedded = template.slice(startIdx, endIdx);
    expect(extracted).toBe(embedded);
  });
});
