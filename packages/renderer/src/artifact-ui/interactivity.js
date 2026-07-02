/*
  ARTIFACT UI — INTERACTIVITY LAYER
  Issue 006

  Vanilla JS only. No eval, no remote requests, no dependencies, no
  module system (this file is inlined verbatim into a <script> tag by
  render.js's `script` option — see that option's own doc comment:
  "vanilla only, no eval, no remote src"). Safe to open from file://.

  This script is intentionally generic: it knows about the *reveal /
  toggle / jump* CONTRACT expressed via data-* and aria-* attributes,
  not about "checkpoints" or "exam questions" by name. That's what lets
  one script back both Issue 004's stateful primitives
  (generalization-checkpoint, exception reveal, metaphor-log) and the
  pre-existing Issue 003 wiring debt (.art-reveal-btn, .art-mode-toggle,
  .art-jumpbox) without knowing which page it's running on.

  ---------------------------------------------------------------------
  Contract 1 — generic reveal/toggle
  ---------------------------------------------------------------------
  <button data-toggle-reveal aria-controls="TARGET_ID" aria-expanded="false"
          [data-collapsed-label="..."] [data-expanded-label="..."]
          [data-hide-after-reveal] [data-toggle-group="GROUP_NAME"]>
    label
  </button>
  <div id="TARGET_ID" class="art-reveal-target" hidden>...</div>

  - Click flips `hidden` on the target and `aria-expanded` on the button.
  - If both data-collapsed-label/data-expanded-label are present, the
    button's visible text swaps to match the new state.
  - `data-hide-after-reveal` marks a ONE-WAY reveal (e.g. the
    generalization-checkpoint verdict): once shown, the button itself is
    hidden rather than left as a re-hide toggle, because the verdict is
    authored content revealed on interaction, not something to grade or
    re-quiz. Focus moves to the revealed content so keyboard/
    screen-reader users don't lose their place when the button
    disappears.
  - `data-toggle-group` opts a reveal button into a named group a
    mode-toggle (contract 2) can bulk-operate on.

  ---------------------------------------------------------------------
  Contract 2 — mode toggle (bulk reveal/hide within a group)
  ---------------------------------------------------------------------
  <button data-mode-toggle data-toggles-group="GROUP_NAME"
          role="switch" aria-checked="false">
    <span class="art-switch"></span> label
  </button>

  - Click reveals every [data-toggle-reveal][data-toggle-group=GROUP_NAME]
    button's target if any are currently collapsed, or hides all of them
    if every one is already expanded (a plain expand-all/collapse-all
    bulk actor, not a per-item override).
  - `aria-checked` and the `.art-on` class on the inner `.art-switch`
    stay in sync with "are all members of this group currently
    expanded" — including when a member is toggled individually, not
    just via this button — so the switch never lies about its state.

  ---------------------------------------------------------------------
  Contract 3 — jump-to-target navigation
  ---------------------------------------------------------------------
  <input data-jump-input-el id="INPUT_ID" data-jump-status="STATUS_ID">
  <button data-jump-go data-jump-input="INPUT_ID">→</button>
  <span id="STATUS_ID" aria-live="polite"></span>
  ...
  <button data-jump-to="3">3</button>   (e.g. a question-grid shortcut)
  ...
  <div id="q3" class="art-jump-target">...</div>

  - Enter on the input, or a click on its paired [data-jump-go] button,
    parses an integer N from the input and jumps to `#q{N}`.
  - A [data-jump-to="N"] element jumps straight to `#q{N}` on click —
    same landing logic, no typed input involved.
  - Landing on a target always: scrolls it into view, moves keyboard
    focus to it (tabindex="-1" added if it isn't already focusable),
    and adds `.art-jump-highlight` (a plain, non-animated outline) for
    ~1.8s. If the visitor has NOT asked for reduced motion, `.art-flash`
    (existing keyframe, families/paper-dossier.css) is layered on top
    for ~1.15s.
  - The highlight/focus/scroll are the load-bearing feedback and fire
    unconditionally; `.art-flash` is decorative on top of them. This is
    the split DESIGN.md §6 asks for: "reduced-motion users must still
    receive all content and state changes without relying on
    animation."

  ---------------------------------------------------------------------
  Non-goals (see issue-006-interactivity-layer.md)
  ---------------------------------------------------------------------
  - No localStorage/IndexedDB — nothing here persists across reloads.
  - No client-side grading — verdicts, why-it-breaks text, and which
    metaphor "landed" are authored content this script only shows or
    hides, never computes.
  - No wiring for .art-mastery-marker — see primitives.css's own
    comment on why that primitive stays a static chip.
*/

(function () {
  "use strict";

  if (!document.addEventListener || !window.matchMedia) {
    // No modern DOM APIs (e.g. a very old/embedded viewer opening the
    // file directly) — fail quiet rather than throw. Content stays in
    // its authored default state.
    return;
  }

  var reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  function prefersReducedMotion() {
    return reducedMotionQuery.matches;
  }

  function closest(el, selector) {
    // Element.closest is available in every browser this artifact
    // targets, but guarded the same way the rest of this function
    // relies on feature checks rather than assumptions.
    while (el && el.nodeType === 1) {
      if (el.matches(selector)) return el;
      el = el.parentElement;
    }
    return null;
  }

  // ============================================================
  // Contract 1 — generic reveal / toggle
  // ============================================================
  function revealTargetOf(btn) {
    var id = btn.getAttribute("aria-controls");
    return id ? document.getElementById(id) : null;
  }

  function setButtonExpanded(btn, expanded) {
    btn.setAttribute("aria-expanded", expanded ? "true" : "false");
    var collapsedLabel = btn.getAttribute("data-collapsed-label");
    var expandedLabel = btn.getAttribute("data-expanded-label");
    if (collapsedLabel && expandedLabel) {
      btn.textContent = expanded ? expandedLabel : collapsedLabel;
    }
  }

  function handleToggleReveal(btn) {
    var target = revealTargetOf(btn);
    if (!target) return;

    var willExpand = target.hasAttribute("hidden");
    if (willExpand) {
      target.removeAttribute("hidden");
    } else {
      target.setAttribute("hidden", "");
    }
    setButtonExpanded(btn, willExpand);

    if (willExpand && btn.hasAttribute("data-hide-after-reveal")) {
      btn.setAttribute("hidden", "");
      if (!target.hasAttribute("tabindex")) {
        target.setAttribute("tabindex", "-1");
      }
      target.focus();
    }

    syncModeToggles();
  }

  // ============================================================
  // Contract 2 — mode toggle
  // ============================================================
  function groupMembers(group) {
    if (!group) return [];
    var nodeList = document.querySelectorAll(
      '[data-toggle-reveal][data-toggle-group="' + cssEscape(group) + '"]'
    );
    return Array.prototype.slice.call(nodeList);
  }

  function cssEscape(value) {
    // Minimal escape for the one place this file builds a selector
    // from a data-* value (group names are page-authored constants,
    // never user input, but escape anyway rather than assume).
    return String(value).replace(/["\\]/g, "\\$&");
  }

  function groupAllExpanded(group) {
    var members = groupMembers(group);
    if (!members.length) return false;
    return members.every(function (b) {
      return b.getAttribute("aria-expanded") === "true";
    });
  }

  function setModeToggleVisual(mt, on) {
    mt.setAttribute("aria-checked", on ? "true" : "false");
    var sw = mt.querySelector(".art-switch");
    if (sw) sw.classList.toggle("art-on", on);
  }

  function syncModeToggles() {
    var toggles = document.querySelectorAll("[data-mode-toggle]");
    for (var i = 0; i < toggles.length; i++) {
      var mt = toggles[i];
      var group = mt.getAttribute("data-toggles-group");
      setModeToggleVisual(mt, groupAllExpanded(group));
    }
  }

  function handleModeToggle(mt) {
    var group = mt.getAttribute("data-toggles-group");
    var members = groupMembers(group);
    if (!members.length) return;
    var turnOn = !groupAllExpanded(group);
    members.forEach(function (b) {
      var target = revealTargetOf(b);
      if (!target) return;
      if (turnOn) {
        target.removeAttribute("hidden");
      } else {
        target.setAttribute("hidden", "");
      }
      setButtonExpanded(b, turnOn);
    });
    setModeToggleVisual(mt, turnOn);
  }

  // ============================================================
  // Contract 3 — jump-to-target
  // ============================================================
  function jumpToId(targetId, statusEl) {
    var target = document.getElementById(targetId);
    if (!target) {
      if (statusEl) statusEl.textContent = "Không tìm thấy mục “" + targetId + "”.";
      return;
    }
    target.scrollIntoView({ block: "center" });
    if (!target.hasAttribute("tabindex")) {
      target.setAttribute("tabindex", "-1");
    }
    target.focus();

    target.classList.add("art-jump-highlight");
    window.setTimeout(function () {
      target.classList.remove("art-jump-highlight");
    }, 1800);

    if (!prefersReducedMotion()) {
      target.classList.add("art-flash");
      window.setTimeout(function () {
        target.classList.remove("art-flash");
      }, 1150);
    }

    if (statusEl) {
      statusEl.textContent = "Đã chuyển tới " + targetId + ".";
    }
  }

  function jumpFromInput(input) {
    var raw = (input.value || "").trim();
    var statusEl = input.getAttribute("data-jump-status")
      ? document.getElementById(input.getAttribute("data-jump-status"))
      : null;
    var n = parseInt(raw, 10);
    if (!raw || isNaN(n)) {
      if (statusEl) statusEl.textContent = "Nhập số câu hỏi rồi thử lại.";
      return;
    }
    jumpToId("q" + n, statusEl);
  }

  // ============================================================
  // Event wiring — delegated, one listener per event type
  // ============================================================
  document.addEventListener("click", function (evt) {
    var revealBtn = closest(evt.target, "[data-toggle-reveal]");
    if (revealBtn) {
      handleToggleReveal(revealBtn);
      return;
    }

    var modeBtn = closest(evt.target, "[data-mode-toggle]");
    if (modeBtn) {
      handleModeToggle(modeBtn);
      return;
    }

    var jumpGoBtn = closest(evt.target, "[data-jump-go]");
    if (jumpGoBtn) {
      var inputId = jumpGoBtn.getAttribute("data-jump-input");
      var input = inputId ? document.getElementById(inputId) : null;
      if (input) jumpFromInput(input);
      return;
    }

    var jumpToBtn = closest(evt.target, "[data-jump-to]");
    if (jumpToBtn) {
      jumpToId("q" + jumpToBtn.getAttribute("data-jump-to"), null);
      return;
    }
  });

  document.addEventListener("keydown", function (evt) {
    if (evt.key !== "Enter") return;
    var input = closest(evt.target, "[data-jump-input-el]");
    if (input) {
      evt.preventDefault();
      jumpFromInput(input);
    }
  });

  // Initial paint: make sure every mode-toggle reflects the real
  // (authored) default state of its group rather than whatever the
  // static markup happened to say, in case the two ever drift.
  syncModeToggles();
})();
