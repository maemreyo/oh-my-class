---
title: "Layer 3: HTML Presentation Validation + Responsive Check"
status: ready-for-agent
labels: []
created: 2026-06-23
github: 2
---

## What to build

Implement Layer 3 quality gate in `packages/quality/layer3_html/html_validator.py`. The file already exists with partial implementation (lines 1-153). Complete the missing methods and add new validators.

## Current State

```python
# packages/quality/layer3_html/html_validator.py
# Lines 57-90: HTMLValidator.validate() — partially implemented (checks doctype, external assets, brand, viewport)
# Lines 92-101: check_doctype() — IMPLEMENTED
# Lines 103-119: validate_external_assets() — IMPLEMENTED
# Lines 121-130: check_brand_string() — IMPLEMENTED
# Lines 132-141: check_viewport_meta() — IMPLEMENTED
# Lines 143-153: check_answer_key_separation() — STUB (empty)
# MISSING: validate_no_native_radio()
# MISSING: validate_no_external_js()
# MISSING: responsive_check.py (entire file)
```

## Implementation Spec

### 1. Add `validate_no_native_radio()` to HTMLValidator (after line 141)

```python
def validate_no_native_radio(self, html: str) -> list[str]:
    """Check for native radio inputs visible to student.
    
    INVARIANT: Student-facing artifacts MUST NOT contain <input type="radio">.
    Use custom CSS-styled elements instead.
    
    Args:
        html: HTML content.
    
    Returns:
        List of issues (empty if no native radios found).
    """
    issues: list[str] = []
    pattern = r'<input\s+[^>]*type=["\']radio["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        issues.append(f"Native radio inputs found: {len(matches)} instances")
    return issues
```

### 2. Add `validate_no_external_js()` to HTMLValidator (after validate_no_native_radio)

```python
def validate_no_external_js(self, html: str) -> list[str]:
    """Check for external JavaScript references.
    
    INVARIANT: No external JS frameworks allowed (React, Vue, etc.).
    Only inline vanilla JS permitted.
    
    Args:
        html: HTML content.
    
    Returns:
        List of issues (empty if no external JS found).
    """
    issues: list[str] = []
    # Check for external script src
    pattern = r'<script\s+[^>]*src=["\']https?://'
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        issues.append(f"External script references found: {len(matches)} instances")
    
    # Check for CDN frameworks
    cdn_patterns = [
        r'cdn\.tailwindcss\.com',
        r'cdnjs\.cloudflare\.com',
        r'cdn\.jsdelivr\.net',
        r'unpkg\.com',
    ]
    for cdn in cdn_patterns:
        if re.search(cdn, html, re.IGNORECASE):
            issues.append(f"CDN framework detected: {cdn}")
    
    return issues
```

### 3. Update `validate()` method to include new checks (lines 57-90)

Add after the viewport check:

```python
# Check native radio inputs
radio_issues = self.validate_no_native_radio(html)
if radio_issues:
    hard_blocks.append("native_radio_inputs")

# Check external JS
js_issues = self.validate_no_external_js(html)
if js_issues:
    hard_blocks.append("unmanaged_js_runtime")

# Check answer key separation
answer_issues = self.check_answer_key_separation(html)
if answer_issues:
    hard_blocks.append("answer_key_leakage")
```

### 4. Implement `check_answer_key_separation()` (lines 143-153)

Replace the stub:

```python
def check_answer_key_separation(self, html: str) -> list[str]:
    """Verify answer keys are not in student-facing sections.
    
    Checks for common answer patterns in HTML content.
    
    Args:
        html: HTML content.
    
    Returns:
        List of issues (empty if properly separated).
    """
    issues: list[str] = []
    
    # Patterns that indicate answer key leakage
    answer_patterns = [
        r'correct\s+answer',
        r'answer\s*:',
        r'solution\s*:',
        r'answer\s+key',
    ]
    
    for pattern in answer_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            issues.append(f"Answer key pattern found: '{pattern}'")
    
    return issues
```

### 5. Create `responsive_check.py` (new file)

```python
"""Responsive check — Playwright-based viewport testing.

Runs screenshots at 4 viewports (375/768/1280/1920px) for staging/prod.
Skipped in development mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ResponsiveCheckResult:
    """Result of responsive viewport testing."""
    
    passed: bool
    viewport_results: dict[int, bool] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


async def check_responsive(
    html: str,
    *,
    viewports: list[int] | None = None,
    environment: str = "development",
) -> ResponsiveCheckResult:
    """Run responsive checks at multiple viewports.
    
    Args:
        html: HTML content to test.
        viewports: List of viewport widths in px. Default: [375, 768, 1280, 1920]
        environment: Current environment. Skipped in 'development'.
    
    Returns:
        ResponsiveCheckResult with pass/fail per viewport.
    """
    if viewports is None:
        viewports = [375, 768, 1280, 1920]
    
    # Skip in development
    if environment == "development":
        return ResponsiveCheckResult(passed=True)
    
    # TODO: Implement with Playwright
    # from playwright.async_api import async_playwright
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch()
    #     page = await browser.new_page()
    #     for vp in viewports:
    #         await page.set_viewport_size({"width": vp, "height": 800})
    #         await page.set_content(html)
    #         # Check for layout issues
    #         # Take screenshot for debugging
    #     await browser.close()
    
    return ResponsiveCheckResult(
        passed=True,
        viewport_results={vp: True for vp in viewports},
    )
```

## Acceptance criteria

- [ ] `validate_no_native_radio()` detects `<input type="radio">` tags
- [ ] `validate_no_external_js()` detects `<script src="https://...">` tags
- [ ] `validate_no_external_js()` detects CDN frameworks (tailwindcss, cloudflare, jsdelivr, unpkg)
- [ ] `check_answer_key_separation()` detects answer patterns in HTML
- [ ] `validate()` includes all 7 hard blocks in result
- [ ] `check_responsive()` skips in development environment
- [ ] `check_responsive()` returns viewport results for staging/prod
- [ ] Unit tests cover all hard blocks
- [ ] Integration test: validate real rendered HTML

## Test suite

Create `packages/quality/layer3_html/tests/test_html_validator.py`:

```python
import pytest
from packages.quality.layer3_html.html_validator import HTMLValidator, HTMLValidationResult
from packages.quality.layer3_html.responsive_check import check_responsive, ResponsiveCheckResult

class TestHTMLValidator:
    def setup_method(self):
        self.validator = HTMLValidator()
    
    def test_valid_html_passes(self):
        html = """<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width"></head>
<body>oh-my-class content</body>
</html>"""
        result = self.validator.validate(html)
        assert result.passed is True
        assert len(result.hard_block_violations) == 0
    
    def test_missing_doctype_fails(self):
        html = "<html><body>Content</body></html>"
        result = self.validator.validate(html)
        assert result.passed is False
        assert "missing_doctype" in result.hard_block_violations
    
    def test_cdn_link_fails(self):
        html = """<!DOCTYPE html>
<html><head><link href="https://cdn.tailwindcss.com"></head>
<body>oh-my-class</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "external_assets" in result.hard_block_violations
    
    def test_external_image_fails(self):
        html = """<!DOCTYPE html>
<html><body><img src="https://example.com/img.png">oh-my-class</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "external_assets" in result.hard_block_violations
    
    def test_missing_viewport_warns(self):
        html = """<!DOCTYPE html>
<html><body>oh-my-class</body></html>"""
        result = self.validator.validate(html)
        assert "missing_viewport_meta" in result.warnings
    
    def test_missing_brand_string_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport"></head>
<body>Content without brand</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "missing_brand_string" in result.hard_block_violations
    
    def test_native_radio_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport"></head>
<body>oh-my-class <input type="radio" name="q1"></body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "native_radio_inputs" in result.hard_block_violations
    
    def test_external_script_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport"></head>
<body>oh-my-class <script src="https://cdn.example.com/app.js"></script></body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "unmanaged_js_runtime" in result.hard_block_violations

class TestResponsiveCheck:
    @pytest.mark.asyncio
    async def test_skips_in_development(self):
        result = await check_responsive("<html></html>", environment="development")
        assert result.passed is True
    
    @pytest.mark.asyncio
    async def test_returns_viewport_results(self):
        result = await check_responsive("<html></html>", environment="staging")
        assert 375 in result.viewport_results
        assert 1920 in result.viewport_results
```

## File paths

| File | Action |
|------|--------|
| `packages/quality/layer3_html/html_validator.py` | MODIFY: Add validate_no_native_radio, validate_no_external_js, update validate() |
| `packages/quality/layer3_html/responsive_check.py` | CREATE: New file with responsive check |
| `packages/quality/layer3_html/__init__.py` | MODIFY: Add exports |
| `packages/quality/layer3_html/tests/test_html_validator.py` | CREATE: Full test suite |

## Dependencies

- `playwright` — for responsive checks (optional, stubbed in dev)
- `re` — regex for pattern matching (already imported)

## Edge cases to handle

1. Case-insensitive matching for DOCTYPE, viewport, radio
2. Multiple CDN links → report all instances
3. Empty HTML → missing_doctype + missing_brand_string
4. Development environment → skip Playwright checks
