from __future__ import annotations

from packages.quality.layer3_html.html_validator import HTMLValidator


def test_valid_accessible_html_passes_layer3() -> None:
    result = HTMLValidator().validate(_html("""
<main>
  <h1>Accessible lesson</h1>
  <img src="data:image/svg+xml;base64,abc" alt="Fraction bar showing one half">
  <svg role="img" aria-label="Fraction diagram" data-long-description="Shows a rectangle split into two equal parts"></svg>
  <label for="answer">Answer</label><input id="answer" type="text">
  <p style="color: #111111; background-color: #ffffff">oh-my-class content</p>
</main>
"""))

    assert result.passed is True
    assert result.details["accessibility"] == []


def test_missing_lang_is_hard_block() -> None:
    result = HTMLValidator().validate("<!DOCTYPE html><html><body>oh-my-class</body></html>")

    assert result.passed is False
    assert "missing_lang" in result.hard_block_violations


def test_missing_image_alt_is_hard_block() -> None:
    result = HTMLValidator().validate(_html('<main><h1>Lesson</h1><img src="data:image/png;base64,abc">oh-my-class</main>'))

    assert "missing_alt_text" in result.hard_block_violations


def test_svg_without_long_description_is_hard_block() -> None:
    result = HTMLValidator().validate(_html('<main><h1>Lesson</h1><svg role="img" aria-label="Chart"></svg>oh-my-class</main>'))

    assert "missing_long_description" in result.hard_block_violations


def test_broken_heading_order_is_hard_block() -> None:
    result = HTMLValidator().validate(_html("<main><h1>Title</h1><h3>Skipped</h3>oh-my-class</main>"))

    assert "broken_heading_order" in result.hard_block_violations


def test_missing_form_label_is_hard_block() -> None:
    result = HTMLValidator().validate(_html('<main><h1>Lesson</h1><input id="answer" type="text">oh-my-class</main>'))

    assert "missing_form_label" in result.hard_block_violations


def test_low_contrast_is_hard_block() -> None:
    result = HTMLValidator().validate(_html('<main><h1>Lesson</h1><p style="color: #777777; background-color: #777777">oh-my-class</p></main>'))

    assert "contrast_below_aa" in result.hard_block_violations


def _html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body>{body}</body>
</html>"""
