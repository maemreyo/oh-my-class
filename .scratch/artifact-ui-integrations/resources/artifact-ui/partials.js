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
      (r) =>
        `<div class="art-diagnostics-row"><span class="art-dk">${r.k}</span><span class="art-dv">${r.v}</span></div>`,
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

// ============================================================
// Issue 004 — root-cause / Socratic teaching primitives
// ============================================================
// Same discipline as the helpers above: pages pass typed JS objects in,
// these return the HTML string. Issue 001's own AC ("primitives render
// from typed inputs, not pasted template HTML") applies here too.
//
// A handful of these (checkpoint, metaphor-log) also need a unique DOM
// id to wire aria-controls for Issue 006's reveal/collapse script —
// pass `{ id: '...' }` as a second argument when a page has more than
// one instance of the same primitive (core-primitives.html demos one of
// each; root-cause-session.html has two anchor-timelines and needs
// distinct ids for its checkpoint/metaphor-log instances too).

let _uidCounter = 0;
function _uid(prefix) {
  _uidCounter += 1;
  return `${prefix}-${_uidCounter}`;
}

// ---------- 1. Anchor timeline ----------
// { axisLabel, anchor: { label }, events: { label, position: 'before'|'at'|'after', state? }[] }
function _wrapLines(text, maxChars) {
  maxChars = maxChars || 20;
  const words = String(text).split(" ");
  const lines = [];
  let cur = "";
  words.forEach((w) => {
    const next = (cur + " " + w).trim();
    if (next.length > maxChars && cur) {
      lines.push(cur);
      cur = w;
    } else {
      cur = next;
    }
  });
  if (cur) lines.push(cur);
  return lines;
}
function _tspans(text, x, startDy, extraAttrs) {
  return _wrapLines(text)
    .map(
      (line, i) =>
        `<tspan x="${x}" dy="${i === 0 ? startDy : 13}"${extraAttrs || ""}>${line}</tspan>`,
    )
    .join("");
}

function renderAnchorTimeline(data, opts) {
  opts = opts || {};
  const id = opts.id || _uid("aat");
  const { axisLabel, anchor, events } = data;
  const width = 640;
  const height = 190;
  const marginX = 46;
  const axisY = 108;
  const anchorX = Math.round(width * 0.68);

  const before = events.filter((e) => e.position === "before");
  const at = events.filter((e) => e.position === "at");
  const after = events.filter((e) => e.position === "after");

  function place(list, xStart, xEnd) {
    const n = list.length;
    if (n === 0) return [];
    const span = xEnd - xStart;
    return list.map((e, i) => ({ ...e, x: Math.round(xStart + (span * (i + 0.5)) / n) }));
  }
  const beforePlaced = place(before, marginX, anchorX - 44).map((e) => ({ ...e, dotY: axisY }));
  const afterPlaced = place(after, anchorX + 44, width - marginX).map((e) => ({
    ...e,
    dotY: axisY,
  }));
  const atPlaced = at.map((e, i) => ({ ...e, x: anchorX, dotY: axisY + 30 + i * 54 }));

  function eventSvg(e, cls) {
    const stem =
      e.dotY !== axisY
        ? `<line class="aat-axis" x1="${e.x}" y1="${axisY}" x2="${e.x}" y2="${e.dotY - 6}" />`
        : "";
    const stateLine = e.state
      ? `<text class="aat-event-label" x="${e.x}" y="${e.dotY + 22 + _wrapLines(e.label).length * 13}" font-style="italic" opacity="0.75">(${e.state})</text>`
      : "";
    return `
      <g class="aat-event aat-event--${cls}">
        <line class="aat-axis" x1="${e.x}" y1="${axisY - 6}" x2="${e.x}" y2="${axisY + 6}" />
        ${stem}
        <circle class="aat-event-dot" cx="${e.x}" cy="${e.dotY}" r="6" />
        <text class="aat-event-label" x="${e.x}" y="${e.dotY + 22}">${_tspans(e.label, e.x, 0)}</text>
        ${stateLine}
      </g>`;
  }

  const glanceArc = before.length
    ? `<path class="aat-glance-arc" marker-end="url(#${id}-arrow)"
        d="M ${anchorX} ${axisY - 16} C ${anchorX - 90} ${axisY - 50}, ${marginX + 90} ${axisY - 50}, ${marginX + 14} ${axisY - 18}" />`
    : "";

  const svg = `
<svg class="art-anchor-timeline-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${axisLabel}">
  <defs>
    <marker id="${id}-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse">
      <path d="M0,0 L8,4 L0,8 Z" class="aat-anchor-dot" />
    </marker>
  </defs>
  <line class="aat-axis" x1="${marginX}" y1="${axisY}" x2="${width - marginX}" y2="${axisY}" />
  ${glanceArc}
  ${beforePlaced.map((e) => eventSvg(e, "before")).join("")}
  ${afterPlaced.map((e) => eventSvg(e, "after")).join("")}
  ${atPlaced.map((e) => eventSvg(e, "at")).join("")}
  <g class="aat-event aat-event--anchor">
    <circle class="aat-anchor-dot" cx="${anchorX}" cy="${axisY}" r="9" />
    <text class="aat-anchor-label" x="${anchorX}" y="${axisY - 20}">${_tspans(anchor.label, anchorX, 0)}</text>
  </g>
</svg>`;

  const legendItems = [];
  if (before.length)
    legendItems.push(
      `<li><span class="aat-legend-dot aat-legend-dot--before"></span>Trước mốc</li>`,
    );
  legendItems.push(
    `<li><span class="aat-legend-dot aat-legend-dot--at" style="background:var(--art-accent)"></span>Đúng tại mốc (neo)</li>`,
  );
  if (at.length)
    legendItems.push(
      `<li><span class="aat-legend-dot aat-legend-dot--at"></span>Diễn ra tại mốc</li>`,
    );
  if (after.length)
    legendItems.push(`<li><span class="aat-legend-dot aat-legend-dot--after"></span>Sau mốc</li>`);

  return `
<div class="art-anchor-timeline art-avoid-break">
  <div class="art-anchor-timeline-head">
    <span class="art-anchor-timeline-label">${axisLabel}</span>
  </div>
  ${svg}
  <ul class="art-anchor-timeline-legend">${legendItems.join("")}</ul>
</div>`;
}

// ---------- 2. Controlled comparison ----------
// { constant: { label, value }, axis, variants: { label, value, note? }[] }
function renderControlledComparison({ constant, axis, variants }) {
  const variantsHtml = variants
    .map(
      (v) => `
    <div class="acc-variant">
      <b>${v.label}</b>
      <span class="acc-value">${v.value}</span>
      ${v.note ? `<span class="acc-note">${v.note}</span>` : ""}
    </div>`,
    )
    .join("\n");
  return `
<div class="art-controlled-comparison art-avoid-break">
  <div class="art-controlled-comparison-constant">
    <span class="acc-constant-label">${constant.label}</span>
    <span class="acc-constant-value">${constant.value}</span>
  </div>
  <div class="art-controlled-comparison-axis">${axis}</div>
  <div class="art-controlled-comparison-grid">${variantsHtml}</div>
</div>`;
}

// ---------- 3. Scenario anchor ----------
// { scenario } — no title/rule field on purpose (Hard Rule #1).
function renderScenarioAnchor({ scenario }) {
  return `
<div class="art-scenario-anchor art-avoid-break">
  <span class="asa-eyebrow">Tình huống</span>
  <p class="asa-scenario">${scenario}</p>
</div>`;
}

// ---------- 4. Generalization checkpoint ----------
// { learnerClaim, verdict: 'confirmed'|'corrected', correction?, explanation }
// The verdict variant is authored content picked at render time — see
// primitives.css comment. Issue 006 only wires the reveal, not grading.
function renderGeneralizationCheckpoint({ learnerClaim, verdict, correction, explanation }, opts) {
  opts = opts || {};
  const id = opts.id || _uid("agc");
  const verdictLabel = verdict === "confirmed" ? "Xác nhận đúng" : "Cần chỉnh lại";
  return `
<div class="art-generalization-checkpoint art-avoid-break">
  <span class="agc-label">Học sinh tự chốt — chờ xác nhận</span>
  <p class="agc-claim">“${learnerClaim}”</p>
  <button type="button" class="art-reveal-btn art-no-print" data-toggle-reveal data-hide-after-reveal
    aria-controls="${id}" aria-expanded="false">Xem xác nhận</button>
  <div class="agc-verdict agc-verdict--${verdict} art-reveal-target" id="${id}" hidden>
    <span class="agc-verdict-label">${verdictLabel}</span>
    ${verdict === "corrected" && correction ? `<p class="agc-correction">${correction}</p>` : ""}
    <p class="agc-explanation">${explanation}</p>
  </div>
</div>`;
}

// ---------- 5. Stress test ----------
// { learnerAttempt, breaksBecause, tiesBackTo? } — static, no client grading.
function renderStressTest({ learnerAttempt, breaksBecause, tiesBackTo }) {
  return `
<div class="art-stress-test art-avoid-break">
  <span class="ast-label">Học sinh tự bẻ luật để test</span>
  <p class="ast-attempt">${learnerAttempt}</p>
  <div class="ast-why">
    <span class="ast-why-label">Vì sao câu này gãy</span>
    <p class="ast-why-text">${breaksBecause}</p>
    ${tiesBackTo ? `<p class="ast-ties">↳ ${tiesBackTo}</p>` : ""}
  </div>
</div>`;
}

// ---------- 6. Metaphor log ----------
// { attempts: { device, text, landed: boolean }[] }
function renderMetaphorLog({ attempts }, opts) {
  opts = opts || {};
  const id = opts.id || _uid("aml");
  const landed = attempts.find((a) => a.landed);
  const earlier = attempts.filter((a) => !a.landed);
  const earlierHtml = earlier
    .map((a) => `<li class="aml-attempt"><b>${a.device}</b><p>${a.text}</p></li>`)
    .join("\n");
  const toggle = earlier.length
    ? `
  <button type="button" class="aml-toggle art-no-print" data-toggle-reveal aria-controls="${id}" aria-expanded="false"
    data-collapsed-label="Xem ${earlier.length} lần thử trước đó" data-expanded-label="Ẩn các lần thử trước đó">Xem ${earlier.length} lần thử trước đó</button>
  <ul class="aml-attempts art-reveal-target" id="${id}" hidden>${earlierHtml}</ul>`
    : "";
  return `
<div class="art-metaphor-log art-avoid-break">
  <span class="aml-label">Nhật ký ẩn dụ</span>
  ${
    landed
      ? `
  <div class="aml-landed">
    <span class="aml-landed-tag">Ẩn dụ trúng</span>
    <b class="aml-device">${landed.device}</b>
    <p class="aml-text">${landed.text}</p>
  </div>`
      : ""
  }
  ${toggle}
</div>`;
}

// ---------- 7. Mastery marker ----------
// { concept, state: 'open'|'clicked' } — static chip, see primitives.css.
function renderMasteryMarker({ concept, state }) {
  const stateLabel = state === "clicked" ? "Đã hiểu" : "Còn mở";
  return `<span class="art-mastery-marker art-mastery-marker--${state}"><span class="amm-dot"></span><span class="amm-concept">${concept}</span><span class="amm-state">${stateLabel}</span></span>`;
}

// ---------- Exception / wrinkle reveal ----------
// Not a new primitive (Issue 006 is explicitly JS-wiring-only, no new
// primitives) — this composes two pre-existing primitives (.art-callout
// from Issue 001, .art-reveal-btn) instead of adding an 8th class. Same
// generic reveal contract as everything else in interactivity.js.
// { prompt, text }
function renderExceptionReveal({ prompt, text }, opts) {
  opts = opts || {};
  const id = opts.id || _uid("exc");
  return `
<div class="art-exception-block" style="margin:var(--art-space-3) 0;">
  <button type="button" class="art-reveal-btn art-no-print" data-toggle-reveal aria-controls="${id}" aria-expanded="false"
    data-collapsed-label="${prompt}" data-expanded-label="Ẩn trường hợp ngoại lệ">${prompt}</button>
  <div class="art-callout art-callout--dashed art-reveal-target" id="${id}" hidden style="margin-top:var(--art-space-3);">
    <span class="art-glyph art-mono">!</span>
    <span>${text}</span>
  </div>
</div>`;
}

module.exports = {
  footer,
  diagnosticsPanel,
  projectionFlag,
  teacherBlock,
  renderAnchorTimeline,
  renderControlledComparison,
  renderScenarioAnchor,
  renderGeneralizationCheckpoint,
  renderStressTest,
  renderMetaphorLog,
  renderMasteryMarker,
  renderExceptionReveal,
};
