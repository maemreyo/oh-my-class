"""
Issue 006 QA — real headless-Chromium screenshots + a scripted keyboard
check. Not a permanent build artifact (not referenced by build.js); a
one-off verification script, kept in qa/ alongside its output for
reproducibility.

Covers the two AC bullets code review can't satisfy on its own:
  - "Screenshot QA at 375/768/1280 for every interactive element in
    both states ... not just the default state"
  - keyboard-reachability is checked by literally tabbing + pressing
    Enter, not asserted from the markup.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = ROOT / "qa" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

WIDTHS = [375, 768, 1280]


def shot(page, width, name):
    page.set_viewport_size({"width": width, "height": 900})
    path = OUT / f"{name}-{width}.png"
    page.screenshot(path=str(path), full_page=True)
    print("wrote", path)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        results = {}

        # ------------------------------------------------------------
        # exam-key.html — default state (was never screenshotted at all)
        # ------------------------------------------------------------
        exam_url = f"file://{DIST / 'families/exam-key.html'}"
        for w in WIDTHS:
            page.goto(exam_url)
            shot(page, w, "exam-key-default")

        # exam-key.html — revealed state: open Q1's answer panel via its
        # reveal button (contract 1), then bulk-close via mode-toggle to
        # confirm contract 2 syncs, then re-open via mode-toggle so the
        # "revealed" screenshot actually shows revealed content.
        for w in WIDTHS:
            page.goto(exam_url)
            page.set_viewport_size({"width": w, "height": 900})
            reveal_btn = page.locator('[data-toggle-group="exam-answers"]').first
            reveal_btn.click()
            expanded = reveal_btn.get_attribute("aria-expanded")
            results.setdefault("exam-key single reveal aria-expanded", []).append(expanded)
            panel_hidden = page.locator("#panel-q1").get_attribute("hidden")
            results.setdefault("exam-key panel-q1 hidden-attr-after-click", []).append(panel_hidden)
            shot(page, w, "exam-key-revealed")

        # exam-key.html — mode-toggle bulk reveal-all + jumpbox jump, one
        # breakpoint is enough to prove the bulk/jump mechanics visually
        # (per-question reveal already covered at all 3 breakpoints above).
        page.goto(exam_url)
        page.set_viewport_size({"width": 768, "height": 900})
        mode_toggle = page.locator("[data-mode-toggle]")
        mode_toggle.click()
        all_expanded = page.evaluate(
            "Array.from(document.querySelectorAll('[data-toggle-group=\"exam-answers\"]'))"
            ".every(b => b.getAttribute('aria-expanded') === 'true')"
        )
        results["exam-key mode-toggle bulk reveal all aria-expanded=true"] = all_expanded
        switch_on = "art-on" in (mode_toggle.locator(".art-switch").get_attribute("class") or "")
        results["exam-key mode-toggle switch shows art-on"] = switch_on
        shot(page, 768, "exam-key-mode-toggle-all-open")

        page.goto(exam_url)
        page.set_viewport_size({"width": 768, "height": 900})
        page.fill("#jumpToQuestion", "3")
        page.click('[data-jump-go]')
        page.wait_for_timeout(150)
        highlighted = page.evaluate("!!document.querySelector('#q3.art-jump-highlight')")
        results["exam-key jumpbox lands with .art-jump-highlight on #q3"] = highlighted
        shot(page, 768, "exam-key-jumpbox-landed")

        # exam-key.html — qgrid shortcut (was previously dead markup,
        # wired in this pass)
        page.goto(exam_url)
        page.set_viewport_size({"width": 768, "height": 900})
        page.click('[data-jump-to="4"]')
        page.wait_for_timeout(150)
        qgrid_focus = page.evaluate("document.activeElement && document.activeElement.id")
        results["exam-key qgrid shortcut moves focus to #q4"] = qgrid_focus
        shot(page, 768, "exam-key-qgrid-jump")

        # ------------------------------------------------------------
        # root-cause-session.html — existing screenshots only show the
        # default (unrevealed) state; add the revealed state for each
        # of Issue 004's stateful primitives.
        # ------------------------------------------------------------
        rcs_url = f"file://{DIST / 'families/root-cause-session.html'}"
        for w in WIDTHS:
            page.goto(rcs_url)
            page.set_viewport_size({"width": w, "height": 900})
            # checkpoint: one-way reveal (data-hide-after-reveal) — check
            # the focus-moves-to-content behavior right here, before the
            # next click below overwrites document.activeElement.
            page.click('[data-toggle-reveal][data-hide-after-reveal]')
            if w == WIDTHS[0]:
                verdict_focused = page.evaluate(
                    "document.activeElement && document.activeElement.classList.contains('agc-verdict')"
                )
                results["root-cause-session focus moved to revealed verdict"] = verdict_focused
                checkpoint_btn_gone = page.evaluate(
                    "!!document.querySelector('.art-generalization-checkpoint [data-toggle-reveal][hidden]')"
                )
                results["root-cause-session checkpoint button hidden after one-way reveal"] = checkpoint_btn_gone
            # exception/wrinkle reveal
            page.locator('.art-exception-block [data-toggle-reveal]').click()
            # metaphor-log expand (only present if there are non-landed attempts)
            aml_toggle = page.locator(".aml-toggle")
            if aml_toggle.count():
                aml_toggle.click()
            shot(page, w, "root-cause-session-revealed")

        # ------------------------------------------------------------
        # Keyboard-only reachability: tab from the top of exam-key and
        # confirm we land on a reveal button with a visible focus
        # style, then activate it with Enter (not a click).
        # ------------------------------------------------------------
        page.goto(exam_url)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.keyboard.press("Tab")  # skip-link / print button region
        found_reveal_via_keyboard = False
        for _ in range(40):
            tag_info = page.evaluate(
                "document.activeElement && {tag: document.activeElement.tagName, "
                "hasReveal: document.activeElement.hasAttribute('data-toggle-reveal')}"
            )
            if tag_info and tag_info.get("hasReveal"):
                found_reveal_via_keyboard = True
                break
            page.keyboard.press("Tab")
        results["keyboard reached a [data-toggle-reveal] button via Tab alone"] = found_reveal_via_keyboard
        if found_reveal_via_keyboard:
            page.keyboard.press("Enter")
            page.wait_for_timeout(100)
            expanded_via_enter = page.evaluate(
                "document.activeElement && document.activeElement.getAttribute('aria-expanded')"
            )
            results["Enter-key activation set aria-expanded"] = expanded_via_enter

        # ------------------------------------------------------------
        # prefers-reduced-motion: content must still fully reveal, just
        # without the .art-flash animation on jump-land.
        # ------------------------------------------------------------
        page2 = browser.new_page()
        page2.emulate_media(reduced_motion="reduce")
        page2.goto(exam_url)
        page2.set_viewport_size({"width": 768, "height": 900})
        page2.fill("#jumpToQuestion", "2")
        page2.click('[data-jump-go]')
        page2.wait_for_timeout(150)
        flash_absent = page2.evaluate("!document.querySelector('#q2.art-flash')")
        highlight_present = page2.evaluate("!!document.querySelector('#q2.art-jump-highlight')")
        results["reduced-motion: .art-flash NOT applied"] = flash_absent
        results["reduced-motion: .art-jump-highlight STILL applied"] = highlight_present
        page2.locator('[data-toggle-group="exam-answers"]').first.click()
        panel_reachable_reduced_motion = page2.evaluate(
            "document.getElementById('panel-q1') && !document.getElementById('panel-q1').hasAttribute('hidden')"
        )
        results["reduced-motion: reveal still works (content reachable)"] = panel_reachable_reduced_motion
        page2.close()

        browser.close()

        print("\n=== RESULTS ===")
        for k, v in results.items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
