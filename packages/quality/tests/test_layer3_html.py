"""Tests for layer3_html — HTML presentation validation and responsive check."""

import pytest

from packages.quality.layer3_html.html_validator import HTMLValidationResult, HTMLValidator
from packages.quality.layer3_html.responsive_check import ResponsiveCheckResult, check_responsive

VALID_HTML = """<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body>oh-my-class content here</body>
</html>"""


class TestHTMLValidator:
    def setup_method(self):
        self.validator = HTMLValidator()

    # ── validate() integration ──────────────────────────────────────────────

    def test_valid_html_passes(self):
        result = self.validator.validate(VALID_HTML)
        assert result.passed is True
        assert len(result.hard_block_violations) == 0

    def test_returns_html_validation_result(self):
        result = self.validator.validate(VALID_HTML)
        assert isinstance(result, HTMLValidationResult)

    def test_missing_doctype_fails(self):
        html = "<html><body>oh-my-class</body></html>"
        result = self.validator.validate(html)
        assert result.passed is False
        assert "missing_doctype" in result.hard_block_violations

    def test_cdn_link_external_asset_fails(self):
        html = """<!DOCTYPE html>
<html><head>
<link href="https://cdn.tailwindcss.com/styles.css">
<meta name="viewport" content="width=device-width">
</head>
<body>oh-my-class</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "external_assets" in result.hard_block_violations

    def test_external_image_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width"></head>
<body><img src="https://example.com/img.png">oh-my-class</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "external_assets" in result.hard_block_violations

    def test_missing_viewport_is_warning_not_block(self):
        html = """<!DOCTYPE html>
<html><body>oh-my-class</body></html>"""
        result = self.validator.validate(html)
        assert "missing_viewport_meta" in result.warnings
        # Viewport is a warning, not a hard block
        assert "missing_viewport_meta" not in result.hard_block_violations

    def test_missing_brand_string_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width"></head>
<body>Content without brand</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "missing_brand_string" in result.hard_block_violations

    def test_native_radio_input_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width"></head>
<body>oh-my-class <input type="radio" name="q1"></body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "native_radio_inputs" in result.hard_block_violations

    def test_external_script_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width"></head>
<body>oh-my-class <script src="https://cdn.example.com/app.js"></script></body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "unmanaged_js_runtime" in result.hard_block_violations

    def test_answer_key_in_html_fails(self):
        html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width"></head>
<body>oh-my-class Answer: 42</body></html>"""
        result = self.validator.validate(html)
        assert result.passed is False
        assert "answer_key_leakage" in result.hard_block_violations

    def test_multiple_violations_collected(self):
        html = "<body>no doctype, no brand</body>"
        result = self.validator.validate(html)
        assert "missing_doctype" in result.hard_block_violations
        assert "missing_brand_string" in result.hard_block_violations

    # ── check_doctype ───────────────────────────────────────────────────────

    def test_check_doctype_present(self):
        assert self.validator.check_doctype("<!DOCTYPE html><html></html>") is True

    def test_check_doctype_case_insensitive(self):
        assert self.validator.check_doctype("<!doctype html><html></html>") is True

    def test_check_doctype_missing(self):
        assert self.validator.check_doctype("<html></html>") is False

    def test_check_doctype_empty(self):
        assert self.validator.check_doctype("") is False

    # ── validate_external_assets ────────────────────────────────────────────

    def test_external_href_detected(self):
        issues = self.validator.validate_external_assets('<link href="https://example.com">')
        assert len(issues) > 0

    def test_external_src_detected(self):
        issues = self.validator.validate_external_assets('<img src="https://example.com/a.png">')
        assert len(issues) > 0

    def test_external_import_detected(self):
        issues = self.validator.validate_external_assets('@import url("https://fonts.googleapis.com")')
        assert len(issues) > 0

    def test_no_external_assets_clean(self):
        issues = self.validator.validate_external_assets('<img src="data:image/png;base64,abc">')
        assert len(issues) == 0

    # ── check_brand_string ──────────────────────────────────────────────────

    def test_brand_present(self):
        assert self.validator.check_brand_string("<body>oh-my-class</body>") is True

    def test_brand_case_insensitive(self):
        assert self.validator.check_brand_string("<body>OH-MY-CLASS</body>") is True

    def test_brand_missing(self):
        assert self.validator.check_brand_string("<body>unrelated content</body>") is False

    # ── check_viewport_meta ─────────────────────────────────────────────────

    def test_viewport_present(self):
        assert self.validator.check_viewport_meta('<meta name="viewport" content="width=device-width">') is True

    def test_viewport_missing(self):
        assert self.validator.check_viewport_meta("<html></html>") is False

    # ── validate_no_native_radio ────────────────────────────────────────────

    def test_radio_input_detected(self):
        issues = self.validator.validate_no_native_radio('<input type="radio" name="q">')
        assert len(issues) == 1
        assert "Native radio" in issues[0]

    def test_radio_single_quotes_detected(self):
        issues = self.validator.validate_no_native_radio("<input type='radio' name='q'>")
        assert len(issues) == 1

    def test_radio_multiple_detected(self):
        html = '<input type="radio" name="a"><input type="radio" name="b">'
        issues = self.validator.validate_no_native_radio(html)
        assert len(issues) == 1
        assert "2 instances" in issues[0]

    def test_no_radio_clean(self):
        html = '<input type="checkbox" name="q">'
        issues = self.validator.validate_no_native_radio(html)
        assert len(issues) == 0

    def test_radio_case_insensitive(self):
        issues = self.validator.validate_no_native_radio('<INPUT TYPE="RADIO" NAME="q">')
        assert len(issues) == 1

    # ── validate_no_external_js ─────────────────────────────────────────────

    def test_external_script_src_detected(self):
        issues = self.validator.validate_no_external_js('<script src="https://example.com/app.js"></script>')
        assert len(issues) >= 1
        assert any("External script" in i for i in issues)

    def test_tailwind_cdn_detected(self):
        issues = self.validator.validate_no_external_js('<script src="https://cdn.tailwindcss.com/3.0.js"></script>')
        assert any("cdn.tailwindcss.com" in i for i in issues)

    def test_cloudflare_cdn_detected(self):
        issues = self.validator.validate_no_external_js('<script src="https://cdnjs.cloudflare.com/libs/app.js"></script>')
        assert any("cdnjs.cloudflare.com" in i for i in issues)

    def test_jsdelivr_detected(self):
        issues = self.validator.validate_no_external_js('<script src="https://cdn.jsdelivr.net/npm/vue@3"></script>')
        assert any("cdn.jsdelivr.net" in i for i in issues)

    def test_unpkg_detected(self):
        issues = self.validator.validate_no_external_js('<script src="https://unpkg.com/react@18"></script>')
        assert any("unpkg.com" in i for i in issues)

    def test_inline_script_clean(self):
        issues = self.validator.validate_no_external_js("<script>console.log('hi')</script>")
        assert len(issues) == 0

    def test_no_script_clean(self):
        issues = self.validator.validate_no_external_js("<p>just text</p>")
        assert len(issues) == 0

    # ── check_answer_key_separation ─────────────────────────────────────────

    def test_answer_colon_detected(self):
        issues = self.validator.check_answer_key_separation("<p>Answer: 42</p>")
        assert len(issues) >= 1

    def test_correct_answer_detected(self):
        issues = self.validator.check_answer_key_separation("<p>The correct answer is B</p>")
        assert len(issues) >= 1

    def test_solution_colon_detected(self):
        issues = self.validator.check_answer_key_separation("<p>Solution: x = 5</p>")
        assert len(issues) >= 1

    def test_answer_key_phrase_detected(self):
        issues = self.validator.check_answer_key_separation("<p>Answer Key</p>")
        assert len(issues) >= 1

    def test_clean_html_passes(self):
        issues = self.validator.check_answer_key_separation("<p>What is photosynthesis?</p>")
        assert len(issues) == 0

    def test_case_insensitive_answer(self):
        issues = self.validator.check_answer_key_separation("<p>ANSWER: 4</p>")
        assert len(issues) >= 1


class TestResponsiveCheck:
    @pytest.mark.asyncio
    async def test_skips_in_development(self):
        result = await check_responsive("<html></html>", environment="development")
        assert result.passed is True
        assert isinstance(result, ResponsiveCheckResult)

    @pytest.mark.asyncio
    async def test_dev_returns_empty_viewport_results(self):
        result = await check_responsive("<html></html>", environment="development")
        # In dev, skipped — no viewport results populated
        assert result.viewport_results == {}

    @pytest.mark.asyncio
    async def test_staging_returns_viewport_results(self):
        result = await check_responsive("<html></html>", environment="staging")
        assert 375 in result.viewport_results
        assert 768 in result.viewport_results
        assert 1280 in result.viewport_results
        assert 1920 in result.viewport_results

    @pytest.mark.asyncio
    async def test_staging_passes_all_viewports(self):
        result = await check_responsive("<html></html>", environment="staging")
        assert result.passed is True
        assert all(result.viewport_results.values())

    @pytest.mark.asyncio
    async def test_custom_viewports(self):
        result = await check_responsive("<html></html>", viewports=[480, 1024], environment="staging")
        assert 480 in result.viewport_results
        assert 1024 in result.viewport_results
        assert 375 not in result.viewport_results

    @pytest.mark.asyncio
    async def test_prod_environment_runs(self):
        result = await check_responsive("<html></html>", environment="production")
        assert result.passed is True
        assert 375 in result.viewport_results
