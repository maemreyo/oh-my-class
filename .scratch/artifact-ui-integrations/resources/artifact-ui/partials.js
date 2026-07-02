// Reusable HTML fragment generators shared across every showcase page.
// Kept as plain string-building functions (no templating engine) so this
// runs with zero dependencies in the sandbox.

function footer(signoff, note) {
  return `
<footer class="art-footer">
  ${note ? `<p>${note}</p>` : ""}
  <span class="art-signoff art-mono">oh-my-class · Artifact UI Layer${signoff ? " · " + signoff : ""}</span>
</footer>`;
}

function diagnosticsPanel({ status, title, rows }) {
  const label = { passed: "Đạt", needs_review: "Cần rà soát", failed: "Thất bại" }[status];
  const rowsHtml = rows
    .map(
      (r) => `<div class="art-diagnostics-row"><span class="art-dk">${r.k}</span><span class="art-dv">${r.v}</span></div>`
    )
    .join("\n");
  return `
<div class="art-diagnostics art-diagnostics--${status} art-avoid-break">
  <div class="art-diagnostics-head">
    <span class="art-diagnostics-status">${label}</span>
    <span class="art-diagnostics-title">${title}</span>
  </div>
  ${rowsHtml}
</div>`;
}

function projectionFlag(text) {
  return `<div class="art-projection-flag"><span class="art-dot"></span>${text}</div>`;
}

function teacherBlock(label, html) {
  return `
<div class="art-teacher-block art-avoid-break">
  <span class="art-teacher-block-label">${label}</span>
  ${html}
</div>`;
}

module.exports = { footer, diagnosticsPanel, projectionFlag, teacherBlock };
