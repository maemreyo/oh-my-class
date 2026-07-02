// Artifact UI — render harness
//
// Simulates, in plain Node, what the real Eta-based renderer
// (packages/renderer) does at build time: concatenate the token
// contract + family tokens + core primitives + family components into
// one inlined <style> block, per artifact HTML file, and never emit a
// <link>, remote <script src>, or http(s):// reference anywhere.
//
// This is deliberately dependency-free (no Eta installed in this
// sandbox) so every showcase page here is fully inspectable and
// testable without a build step.

const fs = require("fs");
const path = require("path");

const ROOT = __dirname;

function read(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), "utf8");
}

const CONTRACT_CSS = read("tokens/contract.css");
const PRIMITIVES_CSS = read("primitives.css");

// Issue 006 — shared vanilla-JS interactivity layer. Read once here
// (same pattern as the CSS constants above) so every page that needs
// it just passes `script: INTERACTIVITY_JS` to renderPage() instead of
// each page file re-reading the file itself.
const INTERACTIVITY_JS = read("interactivity.js");

const FAMILY_TOKENS = {
  "navy-ticket": read("tokens/navy-ticket.css"),
  "paper-dossier": read("tokens/paper-dossier.css"),
  "transit-route": read("tokens/transit-route.css"),
  "investigation-folder": read("tokens/investigation-folder.css"),
};

const FAMILY_COMPONENTS = {
  "navy-ticket": read("families/navy-ticket.css"),
  "paper-dossier": read("families/paper-dossier.css"),
  "transit-route": read("families/transit-route.css"),
  "investigation-folder": read("families/investigation-folder.css"),
};

/**
 * @param {Object} opts
 * @param {string} opts.family one of the 4 data-artifact-theme values
 * @param {string} opts.title document <title>
 * @param {string} opts.lang html lang attribute, default "vi"
 * @param {string} opts.bodyClass extra classes on the .art-root wrapper
 * @param {string} opts.body inner HTML (already includes .art-root wrapper content)
 * @param {string} [opts.extraCss] page-specific CSS appended last (rare; prefer family files)
 * @param {string} [opts.script] inline <script> body (vanilla only, no eval, no remote src)
 * @param {boolean} [opts.printButton] show the floating print button
 */
function renderPage(opts) {
  const {
    family,
    title,
    lang = "vi",
    bodyClass = "",
    body,
    extraCss = "",
    script = "",
    printButton = true,
  } = opts;

  if (!FAMILY_TOKENS[family]) {
    throw new Error(`Unknown artifact family: ${family}`);
  }

  const css = [
    CONTRACT_CSS,
    FAMILY_TOKENS[family],
    PRIMITIVES_CSS,
    FAMILY_COMPONENTS[family] || "",
    extraCss,
  ].join("\n\n");

  return `<!DOCTYPE html>
<html lang="${lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<style>
${css}
</style>
</head>
<body>
<div class="art-root ${bodyClass}" data-artifact-theme="${family}">
${printButton ? '<button class="art-print-btn art-no-print" onclick="window.print()">🖨 In tài liệu</button>' : ""}
${body}
</div>
${script ? `<script>\n${script}\n</script>` : ""}
</body>
</html>
`;
}

/**
 * Variant used only by the core-primitives showcase, which needs a live
 * data-artifact-theme switcher across all four families in one document.
 * Every family's token + component CSS is inlined; only ONE is active at
 * a time via the attribute selector already baked into every rule.
 */
function renderMultiThemePage(opts) {
  const {
    title,
    lang = "vi",
    defaultFamily = "navy-ticket",
    body,
    extraCss = "",
    script = "",
  } = opts;

  const css = [
    CONTRACT_CSS,
    ...Object.values(FAMILY_TOKENS),
    PRIMITIVES_CSS,
    ...Object.values(FAMILY_COMPONENTS),
    extraCss,
  ].join("\n\n");

  const families = Object.keys(FAMILY_TOKENS);
  const switcherButtons = families
    .map(
      (f) =>
        `<button type="button" class="art-theme-switch-btn${f === defaultFamily ? " art-active" : ""}" data-theme="${f}">${f}</button>`,
    )
    .join("\n");

  return `<!DOCTYPE html>
<html lang="${lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<style>
${css}

.art-theme-switch {
  position: sticky; top: 0; z-index: 40;
  display: flex; gap: 6px; flex-wrap: wrap;
  padding: 10px 14px; background: rgba(20,20,20,.92); backdrop-filter: blur(6px);
  font-family: ui-monospace, monospace;
}
.art-theme-switch-btn {
  font-family: inherit; font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
  border: 1px solid rgba(255,255,255,.25); background: transparent; color: rgba(255,255,255,.7);
  padding: 7px 12px; border-radius: 999px; cursor: pointer;
}
.art-theme-switch-btn.art-active { background: #fff; color: #111; border-color: #fff; font-weight: 700; }
@media print { .art-theme-switch { display: none; } }
</style>
</head>
<body style="margin:0;">
<nav class="art-theme-switch art-no-print" aria-label="Chuyển đổi visual family">
${switcherButtons}
</nav>
<div class="art-root" id="artRoot" data-artifact-theme="${defaultFamily}">
${body}
</div>
<script>
function applyOnlyTheme(theme){
  document.querySelectorAll('[data-only-theme]').forEach(function(el){
    el.style.display = (el.getAttribute('data-only-theme') === theme) ? '' : 'none';
  });
}
document.querySelectorAll('.art-theme-switch-btn').forEach(function(btn){
  btn.addEventListener('click', function(){
    document.getElementById('artRoot').setAttribute('data-artifact-theme', btn.dataset.theme);
    document.querySelectorAll('.art-theme-switch-btn').forEach(function(b){ b.classList.remove('art-active'); });
    btn.classList.add('art-active');
    applyOnlyTheme(btn.dataset.theme);
  });
});
applyOnlyTheme('${defaultFamily}');
${script}
</script>
</body>
</html>
`;
}

function writeFile(relOutPath, html) {
  const outPath = path.join(ROOT, "dist", relOutPath);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, html, "utf8");
  return outPath;
}

module.exports = { renderPage, renderMultiThemePage, writeFile, ROOT, INTERACTIVITY_JS };
