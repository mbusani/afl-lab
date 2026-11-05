"""Checks on the raw files, with no browser: rules every public page must meet even with scripts off."""
import pathlib, re, subprocess, pytest

ROOT = pathlib.Path(__file__).parents[1]
PAGES = ["index.html", "models/deserved-to-win/index.html", "tasks/index.html", "credits/index.html",
         "repos/index.html", "library/index.html", "training/index.html", "404.html"]


def tokens(block):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_internal_notes_are_ignored():
    result = subprocess.run(["git", "check-ignore", ".internal/specs/x.md"], cwd=ROOT, capture_output=True)
    assert result.returncode == 0


def test_licence_excludes_photos_and_data():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text and "assets/img/" in text and "Squiggle" in text


def test_contrast_meets_aa_in_both_modes():
    css = (ROOT / "assets/site.css").read_text(encoding="utf-8")
    light = tokens(re.search(r":root\s*\{(.*?)\}", css, re.S).group(1))
    dark = {**light, **tokens(re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S).group(1))}
    for mode in (light, dark):
        for fg, bg in (("fg", "bg"), ("muted", "bg"), ("muted", "surface"), ("muted", "panel"), ("accent", "bg"), ("accent", "surface"),
                       ("chalk", "night"), ("chalk-dim", "night"), ("lamp", "night")):
            assert contrast(mode[fg], mode[bg]) >= 4.5, (fg, bg)


def test_no_ball_brand_name():
    files = [ROOT / "assets/site.css", ROOT / "assets/site.js"] + [ROOT / p for p in PAGES if (ROOT / p).exists()]
    for f in files:
        assert "sherrin" not in f.read_text(encoding="utf-8").lower(), f


@pytest.mark.parametrize("path", [p for p in PAGES if (ROOT / p).exists()])
def test_page_rules(path):
    html = (ROOT / path).read_text(encoding="utf-8")
    footer = re.search(r"<footer.*?</footer>", html, re.S).group(0)
    assert "Not affiliated with the AFL or any club" in footer
    assert "afl-lab/issues" in footer
    assert "<noscript>" in html
    for tag in ('property="og:title"', 'property="og:description"', 'property="og:image"', 'name="twitter:card"', "favicon.svg"):
        assert tag in html, tag
